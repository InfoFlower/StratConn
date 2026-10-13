import datetime

from Core.request import REQUEST
from Core.tb_types import EventType
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
        Price, Timestamp = float(data['close']), int(data['timestamp'])
        Request = self.CurStrat.ProcessPrice(Price, Timestamp)
        if Request['request'] == REQUEST.STILL :
            return {'status':'success',
                    'data':{'action':'still'}}
        elif Request['request'] == REQUEST.SUBMIT_ORDER :
            Order = Request['params']
            self.Current_Orders.append(Order)
            response = self.GateComm.submit_order(Order)
            Action = 'submit_order'
        elif Request['request'] == REQUEST.CANCEL_ORDER :
            response = self.GateComm.cancel_order(Request['params']['OrderId'])
            Action = 'cancel_order'
        elif Request['request'] == REQUEST.CLOSE_POSITION :
            response = self.GateComm.close_position(Request['params']['PositionId'])
            Action = 'close_position'
        elif Request['request'] == REQUEST.GET_PRICE :
            response = self.GateComm.get_price()
            Action = 'get_price'
        else :
            return {'status':'FAILED',
                    'data':{'action':'unknown', 'request':str(Request['request'])}}

        # Retour optionnel de la réponse broker à la stratégie (ex. pour récupérer les ids)
        if hasattr(self.CurStrat, 'ProcessResponse'):
            self.CurStrat.ProcessResponse(Request['request'], response)
        return {'status':'success',
                'data':{'action':Action,
                        'response':response}}


    def SendEvent(self, data):
        TypeEvent,DataEvent = data['EventType'],data['data']
        response = self.CurStrat.ProcessEvent(TypeEvent,DataEvent)
        return response