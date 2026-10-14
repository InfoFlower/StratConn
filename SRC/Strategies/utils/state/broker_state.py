"""
Miroir local de l'état du broker : ordres, positions, wallet.
Spécification : docs/04-utils-strategie.md §3.

Alimentation :
  ProcessPrice    -> OnPrice(candle, ts), puis retourner SyncRequests() si une resynchronisation est en cours
  ProcessEvent    -> OnEvent(type, data)          (jamais d'appel réseau ici : interblocage, routes.md §7.5)
  ProcessResponse -> OnResponse(request, response)

Règle : upsert par id, sans jamais faire régresser un statut.
Le wallet n'est jamais recalculé : il vient des instantanés du broker (événements, GET_WALLET).
"""

import threading
from dataclasses import fields
from enum import Enum

from Core.order import Order
from Core.position import Position
from Core.request import REQUEST
from Core.tb_types import Asset, OrderStatus, OrderType, PositionStatus, Side


# Rang des statuts : un objet reçu avec un rang inférieur au rang connu est ignoré
ORDER_RANK = {OrderStatus.REQUESTED: 0, OrderStatus.PENDING: 1,
              OrderStatus.EXECUTED: 2, OrderStatus.CANCELLED: 2}
POSITION_RANK = {PositionStatus.OPENED: 0, PositionStatus.CLOSED: 1}

ORDER_ENUMS = {'asset': Asset, 'base': Asset, 'side': Side, 'status': OrderStatus, 'type': OrderType}
POSITION_ENUMS = {'asset': Asset, 'base': Asset, 'side': Side, 'status': PositionStatus}

SYNC_ORDER = (REQUEST.GET_ORDERS, REQUEST.GET_POSITIONS, REQUEST.GET_WALLET)


class BrokerState:

    def __init__(self) -> None:
        self._lock = threading.Lock()   # ProcessEvent (thread HTTP) et ProcessPrice (thread TCP) l'utilisent tous deux
        self.Orders = {}                # dict[int, Order]
        self.Positions = {}             # dict[int, Position]
        self.Wallet = {}                # dict[Asset, {'portfolio', 'locked', 'available'}]
        self.LastCandle = None          # dernier tick complet (dict)
        self.LastPrice = None           # close du dernier tick
        self.LastTs = None
        self.LastEventTs = None
        self.LastError = None
        self.Desync = False
        self._ClosedIds = []            # ids des positions fermées, dans l'ordre de fermeture
        self._SyncPending = set()       # requêtes GET_* restant à recevoir

    # ------------------------------------------------------------------ alimentation

    def OnPrice(self, candle, ts) -> None:
        """
        À appeler dans ProcessPrice. candle : le tick reçu par ConnStrat
        ({'timestamp', 'timeframe', 'open', 'high', 'low', 'close', 'volume'}, prix en float).
        LastPrice reste le close, utilisé pour le PnL latent.
        """
        self.LastCandle = dict(candle)
        self.LastPrice, self.LastTs = float(candle['close']), int(ts)

    def OnEvent(self, type, data) -> None:
        """
        À appeler dans ProcessEvent. type : nom de l'EventType (chaîne ou enum).
        data : {'timestamp': ms, 'object': <Order|Position>, 'wallet': {'base', 'portfolio', 'locked', 'available'}}
        Aucun appel réseau ici.
        """
        name = type.name if isinstance(type, Enum) else str(type)
        data = data or {}
        with self._lock:
            obj = data.get('object')
            if name.startswith('ORDER_') and isinstance(obj, dict):
                if name != 'ORDER_PLACED' and obj.get('id') not in self.Orders:
                    self._MarkDesync(f'{name} pour un ordre inconnu ({obj.get("id")})')
                self._UpsertOrder(obj)
            elif name.startswith('POSITION_') and isinstance(obj, dict):
                if name == 'POSITION_CLOSED' and obj.get('id') not in self.Positions:
                    self._MarkDesync(f'{name} pour une position inconnue ({obj.get("id")})')
                self._UpsertPosition(obj)
            elif name != 'PRICE_UPDATE':
                print(f'[STATE] Événement ignoré : {name} {data}')
                return

            wallet = data.get('wallet')
            if isinstance(wallet, dict) and wallet.get('base') in Asset.__members__:
                self.Wallet[Asset[wallet['base']]] = {k: float(wallet[k]) for k in ('portfolio', 'locked', 'available') if k in wallet}
            if data.get('timestamp') is not None:
                self.LastEventTs = int(data['timestamp'])

    def OnResponse(self, request, response) -> None:
        """À appeler dans ProcessResponse, avec la requête envoyée et la réponse brute du broker"""
        with self._lock:
            if not isinstance(response, dict) or not isinstance(response.get('data'), dict):
                # Réseau, P7, requête inconnue : on ne sait pas si le broker a traité la requête
                self.LastError = response
                self._MarkDesync(f'réponse sans data à {request} : {response}')
                return

            data = response['data']
            if str(response.get('status', '')).upper() != 'SUCCESS':
                self.LastError = data.get('reason', data)
                return

            if request in (REQUEST.SUBMIT_ORDER, REQUEST.CANCEL_ORDER):
                self._UpsertOrder(data)
            elif request == REQUEST.CLOSE_POSITION:
                self._UpsertPosition(data)
            elif request == REQUEST.GET_ORDERS:
                self._ReplaceOrders(data.get('orders', []))
                self._SyncDone(request)
            elif request == REQUEST.GET_POSITIONS:
                self._ReplacePositions(data.get('positions', []))
                self._SyncDone(request)
            elif request == REQUEST.GET_WALLET:
                self._ReplaceWallet(data)
                self._SyncDone(request)

    def ForceSync(self) -> None:
        """Demande une relecture complète (au démarrage, ou après une incohérence repérée par la stratégie)"""
        with self._lock:
            self._MarkDesync('ForceSync')

    def SyncRequests(self) -> list:
        """
        Requêtes GET_* encore à envoyer, dans l'ordre. Liste vide si l'état est à jour.
        ProcessPrice peut la retourner telle quelle : ConnStrat envoie toute la liste dans le même tick.
        """
        with self._lock:
            return [{'request': r, 'params': {}} for r in SYNC_ORDER if r in self._SyncPending]

    # ------------------------------------------------------------------ lecture

    def GetOrder(self, id):
        return self.Orders.get(id)

    def GetPosition(self, id):
        return self.Positions.get(id)

    def PendingOrders(self, asset=None) -> list:
        return [o for o in self._Sorted(self.Orders)
                if o.status == OrderStatus.PENDING and (asset is None or o.asset == asset)]

    def OpenPositions(self, asset=None, side=None) -> list:
        return [p for p in self._Sorted(self.Positions)
                if p.status == PositionStatus.OPENED
                and (asset is None or p.asset == asset) and (side is None or p.side == side)]

    def ClosedPositions(self) -> list:
        """Positions fermées, dans l'ordre de fermeture"""
        return [self.Positions[i] for i in self._ClosedIds]

    def PositionOfOrder(self, order_id):
        """Position ouverte par cet ordre, ou None"""
        for p in self.Positions.values():
            if p.order_id == order_id:
                return p
        return None

    def HasOpenPosition(self, asset=None) -> bool:
        return len(self.OpenPositions(asset)) > 0

    def Available(self, base):
        """None tant qu'aucun instantané du wallet n'a été reçu pour cette base"""
        return self.Wallet.get(base, {}).get('available')

    def Locked(self, base):
        return self.Wallet.get(base, {}).get('locked')

    def Balance(self, base):
        """Solde du wallet (portfolio), PnL réalisé compris"""
        return self.Wallet.get(base, {}).get('portfolio')

    def Exposure(self, asset) -> float:
        """Somme signée des asset_qty ouvertes : LONG +, SHORT -"""
        return sum(p.asset_qty if p.side == Side.LONG else -p.asset_qty
                   for p in self.OpenPositions(asset))

    def UnrealizedPnl(self, base, price=None):
        """PnL latent des positions ouvertes sur cette base, au prix donné (défaut : LastPrice). None sans prix"""
        price = self.LastPrice if price is None else price
        positions = [p for p in self.OpenPositions() if p.base == base]
        if not positions:
            return 0.0
        if price is None:
            return None
        return sum(self._Pnl(p, price) for p in positions)

    def Equity(self, base, price=None):
        """Balance + PnL latent. None si l'un des deux est inconnu"""
        balance, unrealized = self.Balance(base), self.UnrealizedPnl(base, price)
        if balance is None or unrealized is None:
            return None
        return balance + unrealized

    def RealizedPnl(self, base) -> float:
        return sum(self._Pnl(p, p.close_price) for p in self.ClosedPositions()
                   if p.base == base and p.close_price is not None)

    # ------------------------------------------------------------------ interne

    @staticmethod
    def _Pnl(position, price) -> float:
        # Même formule que Wallet.pnl du broker ; à remplacer par calc.pnl.pnl quand il existera
        pnl = (price - position.entry) * position.asset_qty
        return -pnl if position.side == Side.SHORT else pnl

    @staticmethod
    def _Sorted(objects) -> list:
        return [objects[i] for i in sorted(objects)]

    @staticmethod
    def _Build(cls, enums, raw):
        """dict JSON (enums par nom) -> dataclass ; ignore les champs que le modèle StratConn ne connaît pas (N9)"""
        known = {f.name for f in fields(cls)}
        params = {}
        for key, value in raw.items():
            if key not in known:
                continue
            if key in enums and isinstance(value, str):
                value = enums[key][value]
            params[key] = value
        return cls(**params)

    def _UpsertOrder(self, raw) -> None:
        try:
            order = self._Build(Order, ORDER_ENUMS, raw)
        except (KeyError, TypeError) as e:
            self._MarkDesync(f'ordre illisible {raw} : {e!r}')
            return
        known = self.Orders.get(order.id)
        if known is not None:
            old, new = ORDER_RANK[known.status], ORDER_RANK[order.status]
            if new < old or (new == old and new == 2 and order.status != known.status):
                return
        self.Orders[order.id] = order

    def _UpsertPosition(self, raw) -> None:
        try:
            position = self._Build(Position, POSITION_ENUMS, raw)
        except (KeyError, TypeError) as e:
            self._MarkDesync(f'position illisible {raw} : {e!r}')
            return
        known = self.Positions.get(position.id)
        if known is not None and POSITION_RANK[position.status] < POSITION_RANK[known.status]:
            return
        self.Positions[position.id] = position
        if position.status == PositionStatus.CLOSED and position.id not in self._ClosedIds:
            self._ClosedIds.append(position.id)

    def _ReplaceOrders(self, raws) -> None:
        self.Orders = {}
        for raw in raws:
            self._UpsertOrder(raw)

    def _ReplacePositions(self, raws) -> None:
        # Le broker ne donne pas l'ordre de fermeture : on garde celui connu, les nouvelles fermées suivent par id
        previous = self._ClosedIds
        self.Positions, self._ClosedIds = {}, []
        for raw in sorted(raws, key=lambda r: r.get('id', 0)):
            self._UpsertPosition(raw)
        closed = set(self._ClosedIds)
        kept = [i for i in previous if i in closed]
        self._ClosedIds = kept + [i for i in self._ClosedIds if i not in kept]

    def _ReplaceWallet(self, data) -> None:
        wallet = {}
        for key in ('portfolio', 'locked', 'available'):
            for base, value in data.get(key, {}).items():
                if base in Asset.__members__:
                    wallet.setdefault(Asset[base], {})[key] = float(value)
        self.Wallet = wallet

    def _MarkDesync(self, reason) -> None:
        print(f'[STATE] Désynchronisé : {reason}')
        self.Desync = True
        self._SyncPending = set(SYNC_ORDER)

    def _SyncDone(self, request) -> None:
        self._SyncPending.discard(request)
        if not self._SyncPending:
            self.Desync = False
