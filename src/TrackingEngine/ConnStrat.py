from Core.request import REQUEST
from GatewayCommand.StratCommand import GateComm


class ConnStrat :
    def __init__(self, stratpath, BROKER_ADR, BROKER_PORT):
        self.CurStrat = self.load_strategy(stratpath)
        self.GateComm = GateComm(BROKER_ADR, BROKER_PORT)
        self.Current_Orders = []
        return None

    def load_strategy(self, stratpath):
        import importlib
        strategie_mod = importlib.import_module(stratpath)
        return strategie_mod.strategie()

    def UpdatePrice(self, data):
        """
        ProcessPrice retourne une requête (dict), une liste de requêtes, ou None (= STILL).
        Les requêtes sont envoyées dans l'ordre ; ProcessResponse est appelé après chacune,
        avant l'envoi de la suivante. Une requête inconnue est sautée, les autres partent quand même.
        """
        Price, Timestamp = self._convert_prices(data), int(data['timestamp'])
        Requests = self.CurStrat.ProcessPrice(Price, Timestamp)
        if Requests is None:
            Requests = []
        elif isinstance(Requests, dict):
            Requests = [Requests]

        Status, Actions = 'success', []
        for Request in Requests:
            Action = self.SendRequest(Request)
            if Action['action'] == 'unknown':
                Status = 'FAILED'
            Actions.append(Action)
        if not Actions:
            Actions.append({'action':'still'})
        return {'status':Status,
                'data':{'actions':Actions}}
    
    def _convert_prices(self, data):
        for key in ('open', 'high', 'low', 'close', 'volume'):
            if key in data:
                data[key] = float(data[key])
        return data
    
    def SendRequest(self, Request):
        """Envoie une requête de la stratégie au broker ; retourne {'action', 'response'}"""
        if not isinstance(Request, dict):
            Request = {}
        RequestType = Request.get('request')
        Params = Request.get('params') or {}
        if RequestType == REQUEST.STILL :
            return {'action':'still'}
        elif RequestType == REQUEST.SUBMIT_ORDER :
            self.Current_Orders.append(Params)
            response = self.GateComm.submit_order(Params)
            Action = 'submit_order'
        elif RequestType == REQUEST.CANCEL_ORDER :
            response = self.GateComm.cancel_order(Params['OrderId'])
            Action = 'cancel_order'
        elif RequestType == REQUEST.CLOSE_POSITION :
            response = self.GateComm.close_position(Params['PositionId'])
            Action = 'close_position'
        elif RequestType == REQUEST.GET_PRICE :
            response = self.GateComm.get_price()
            Action = 'get_price'
        elif RequestType == REQUEST.GET_ORDERS :
            response = self.GateComm.get_orders(Params.get('status'))
            Action = 'get_orders'
        elif RequestType == REQUEST.GET_POSITIONS :
            response = self.GateComm.get_positions(Params.get('status'))
            Action = 'get_positions'
        elif RequestType == REQUEST.GET_WALLET :
            response = self.GateComm.get_wallet()
            Action = 'get_wallet'
        else :
            print(f'[STRATCONN] Unknown request: {Request}')
            return {'action':'unknown', 'request':str(RequestType)}

        # Retour optionnel de la réponse broker à la stratégie (ex. pour récupérer les ids)
        if hasattr(self.CurStrat, 'ProcessResponse'):
            self.CurStrat.ProcessResponse(RequestType, response)
        return {'action':Action,
                'response':response}


    def SendEvent(self, data):
        TypeEvent,DataEvent = data['EventType'],data['data']
        response = self.CurStrat.ProcessEvent(TypeEvent,DataEvent)
        return response