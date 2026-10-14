"""
Template de stratégie : copier ce fichier, le renommer, puis écrire la décision dans ProcessPrice.
Pour le charger : strategie_path = 'Strategies.<NomDuFichier>' dans StratConn/src/main.py
Routes et formats de réponse : Strategies/utils/doc/routes.md
"""

from Core.request import REQUEST
from Core.order import Order
from Core.tb_types import Asset, OrderStatus, OrderType, Side
from Strategies.utils.state import BrokerState


class strategie:                       # le nom de la classe est imposé

    def __init__(self):
        self.State = BrokerState()     # ordres, positions et wallet connus
        self.Tick = 0
        print('[STRATEGY] Initialized')

    def ProcessPrice(self, candle, ts):
        """
        Appelée à chaque tick. Retourne une requête, une liste de requêtes, ou None (ne rien faire).
        candle : dict {'timestamp', 'timeframe', 'open', 'high', 'low', 'close', 'volume'} (prix en float)
        ts     : int, epoch en ms
        """
        self.State.OnPrice(candle, ts)
        self.Tick += 1
        if self.Tick == 1:
            return None                # le broker n'a encore reçu aucune bougie au premier tick

        close = candle['close']

        # --- Votre décision ici. Exemple : acheter 0.01 BTC au marché ---
        # order = Order(asset=Asset.BTC, asset_qty=0.01, base=Asset.USD, side=Side.LONG,
        #               status=OrderStatus.REQUESTED, type=OrderType.MARKET,
        #               tp_price=close * 1.03, sl_price=close * 0.98)
        # return {'request': REQUEST.SUBMIT_ORDER, 'params': order}

        return None

    def ProcessResponse(self, request, response):
        """Réponse du broker à chaque requête envoyée"""
        self.State.OnResponse(request, response)

    def ProcessEvent(self, type, data):
        """Événements du broker (ordre exécuté, position fermée...). Ne jamais appeler le broker ici"""
        self.State.OnEvent(type, data)
        return {'status': 'SUCCESS'}
