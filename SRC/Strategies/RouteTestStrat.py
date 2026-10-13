"""
Stratégie de test des routes du broker (Sisimulation/src/interface/HTTP/translator.py).
Un scénario fixe, une étape par tick, puis STILL :
  0. DO NOTHING -> DO NOTHING
  1. GET_PRICE                  -> status 'success' et prix non nul
  2. SUBMIT_ORDER MARKET LONG   -> status 'SUCCESS' (ouvre une position)
  3. SUBMIT_ORDER LIMIT LONG    -> status 'SUCCESS' (level très bas : reste PENDING)
  4. CANCEL_ORDER (ordre LIMIT) -> 'SUCCESS', data.status 'CANCELLED' (P12)
  5. CANCEL_ORDER (même ordre)  -> 'FAILED' avec data.reason : déjà annulé (P12)
  6. CANCEL_ORDER (id inconnu)  -> 'FAILED' avec data.reason (P6)
  7. CLOSE_POSITION (position)  -> 'SUCCESS', data.status 'CLOSED', close_justif 'TERM' (P12)
  8. CLOSE_POSITION (même pos.) -> 'FAILED' avec data.reason : déjà fermée (P12)
  9. CLOSE_POSITION (id inconnu)-> 'FAILED' avec data.reason (P6)
    SUBMIT_ORDER hors marge    -> status 'ERROR'/'FAILED' avec data.reason
Un récapitulatif PASS/FAIL est affiché dès la réponse de la dernière étape.
START_SIMULATION est déjà exercé par TEST/main.py.

Pour l'utiliser : strategie_path = 'SRC.Strategies.RouteTestStrat' dans SRC/main.py
"""

from Core.request import REQUEST
from Core.order import Order
from Core.tb_types import Asset, OrderStatus, OrderType, Side, EventType


class strategie:

    def __init__(self):
        self.last_price = 0
        self.tick = 0
        self.step = 0
        self.awaiting = None        # nom de l'étape envoyée, en attente de ProcessResponse
        self.results = []           # (étape, PASS/FAIL, détail)
        self.done = False

        # Ids : ceux de la réponse broker si disponibles, sinon ceux attendus
        # sur un broker neuf (Executor démarre ordres et positions à 0).
        self.market_order_id = None
        self.limit_order_id = None
        self.position_id = None
        self.submits_sent = 0
        self.unknown_id = 999       # id absent du broker

        self.default_params = {
            'asset': Asset.BTC,
            'asset_qty': 0.01,
            'base': Asset.USD,
            'status': OrderStatus.REQUESTED,
        }
        self.steps = [
            ('PASS FIRST TICK',None),
            ('GET_PRICE', self._get_price),
            ('SUBMIT_MARKET', self._submit_market),
            ('SUBMIT_LIMIT', self._submit_limit),
            ('CANCEL_ORDER', self._cancel_order),
            ('CANCEL_AGAIN', self._cancel_order),
            ('CANCEL_UNKNOWN', self._cancel_unknown),
            ('CLOSE_POSITION', self._close_position),
            ('CLOSE_AGAIN', self._close_position),
            ('CLOSE_UNKNOWN', self._close_unknown),
            ('SUBMIT_NO_MARGIN', self._submit_no_margin),
        ]
        print("[RouteTest] Initialized")
        return None

    def ProcessPrice(self, price, timestamp):
        self.last_price = price
        self.tick += 1

        # Étape précédente sans réponse : exception côté StratConn (voir log INVALID_TICK)
        if self.awaiting is not None:
            self._record(self.awaiting, False, 'pas de réponse (exception dans StratConn)')

        if self.step >= len(self.steps):
            if not self.done:
                self._summary()
            return {'request': REQUEST.STILL}

        name, build = self.steps[self.step]
        self.step += 1
        
        print(f"[RouteTest] Tick {self.tick} : étape {name} (prix {price})")
        if build is None :
            return {'request': REQUEST.STILL}
        self.awaiting = name    
        return build(price)

    # --- Construction des requêtes ---

    def _get_price(self, price):
        return {'request': REQUEST.GET_PRICE}

    def _submit_market(self, price):
        # TP/SL éloignés : la position ne doit pas se fermer seule avant CLOSE_POSITION
        order = Order(**self.default_params, side=Side.LONG, type=OrderType.MARKET,
                      tp_price=price * 1.5, sl_price=price * 0.5)
        return self._submit(order)

    def _submit_limit(self, price):
        order = Order(**self.default_params, side=Side.LONG, type=OrderType.LIMIT,
                      level=price * 0.5, tp_price=price * 1.5, sl_price=price * 0.25)
        return self._submit(order)

    def _cancel_order(self, price):
        OrderId = self.limit_order_id if self.limit_order_id is not None else 1
        return {'request': REQUEST.CANCEL_ORDER, 'params': {'OrderId': OrderId}}

    def _close_position(self, price):
        PositionId = self.position_id if self.position_id is not None else 0
        return {'request': REQUEST.CLOSE_POSITION, 'params': {'PositionId': PositionId}}

    def _cancel_unknown(self, price):
        return {'request': REQUEST.CANCEL_ORDER, 'params': {'OrderId': self.unknown_id}}

    def _close_unknown(self, price):
        return {'request': REQUEST.CLOSE_POSITION, 'params': {'PositionId': self.unknown_id}}

    def _submit_no_margin(self, price):
        params = dict(self.default_params, asset_qty=1e9)
        order = Order(**params, side=Side.LONG, type=OrderType.MARKET,
                      tp_price=price * 1.5, sl_price=price * 0.5)
        return self._submit(order)

    def _submit(self, order):
        self.submits_sent += 1
        return {'request': REQUEST.SUBMIT_ORDER, 'params': order}

    # --- Vérification des réponses ---

    def ProcessResponse(self, request, response):
        name, self.awaiting = self.awaiting, None
        print(f"[RouteTest] Réponse {name} : {response}")
        response = response if isinstance(response, dict) else {}
        status = response.get('status')
        data = response.get('data') if isinstance(response.get('data'), dict) else {}

        if name == 'GET_PRICE':
            ok = status == 'success' and data.get('price') is not None
            self._record(name, ok, f"status={status}, price={data.get('price')}")

        elif name in ('SUBMIT_MARKET', 'SUBMIT_LIMIT'):
            # Id attendu = rang du submit : l'ordre est placé même si la réponse HTTP échoue
            order_id = data.get('id', self.submits_sent - 1)
            if name == 'SUBMIT_MARKET':
                self.market_order_id = order_id
            else:
                self.limit_order_id = order_id
            self._record(name, status == 'SUCCESS', f"status={status}, id={order_id}, {self._err(response)}")

        elif name == 'CANCEL_ORDER':
            ok = status == 'SUCCESS' and data.get('status') == 'CANCELLED' and data.get('id') == self.limit_order_id
            self._record(name, ok, f"status={status}, id={data.get('id')}, order.status={data.get('status')}, {self._err(response)}")

        elif name == 'CLOSE_POSITION':
            ok = status == 'SUCCESS' and data.get('status') == 'CLOSED' and data.get('close_justif') == 'TERM'
            self._record(name, ok, f"status={status}, id={data.get('id')}, position.status={data.get('status')}, "
                                   f"close_price={data.get('close_price')}, justif={data.get('close_justif')}, {self._err(response)}")

        elif name in ('CANCEL_AGAIN', 'CANCEL_UNKNOWN', 'CLOSE_AGAIN', 'CLOSE_UNKNOWN', 'SUBMIT_NO_MARGIN'):
            # Refus attendu : 'reason' distingue un refus du broker d'un échec réseau/crash (error)
            ok = status in ('ERROR', 'FAILED') and 'reason' in data
            self._record(name, ok, f"status={status}, data={data}, {self._err(response)}")

        if self.step >= len(self.steps) and not self.done:
            self._summary()

    def ProcessEvent(self, event_type: EventType, data=None):
        print(f"[RouteTest] Event received: {event_type}, Data: {data}")
        # Si les events arrivent, ils priment sur l'id supposé
        if event_type == 'POSITION_OPENED' and isinstance(data, dict) and self.position_id is None:
            self.position_id = data.get('id')
        return {'status': 'processed', 'event': str(event_type)}

    # --- Outils ---

    def _err(self, response):
        return f"error={response['error']}" if 'error' in response else ''

    def _record(self, name, ok, detail):
        self.results.append((name, 'PASS' if ok else 'FAIL', detail))
        print(f"[RouteTest] {name} : {'PASS' if ok else 'FAIL'} ({detail})")
        if name == self.awaiting:
            self.awaiting = None

    def _summary(self):
        self.done = True
        passed = sum(1 for _, r, _ in self.results if r == 'PASS')
        print(f"[RouteTest] ===== Récapitulatif : {passed}/{len(self.results)} PASS =====")
        for name, res, detail in self.results:
            print(f"[RouteTest] {res:4} {name:17} {detail}")
