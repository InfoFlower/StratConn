import datetime

from SRC.Core.request import REQUEST
from SRC.Core.tb_types import EventType

from SRC.GatewayCommand.StratCommand import GateComm


class ConnStrat :
    def __init__(self, stratpath):
        self.CurStrat = self.load_strategy(stratpath)
        self.GateComm = GateComm()
        self.Current_Orders = []
        return None

    def load_strategy(self, stratpath):
        import importlib
        strategie_mod = importlib.import_module(stratpath)
        return strategie_mod.strategie()

    def UpdatePrice(self, data):
        Price, Timestamp = float(data['price']), int(data['timestamp'])
        Request = self.CurStrat.ProcessPrice(Price, Timestamp)
        if Request['request'] == REQUEST.STILL :
            return {'status':'success',
                    'data':{'action':'still'}}
        elif Request['request'] == REQUEST.SUBMIT_ORDER :
            Order = Request['params']
            self.Current_Orders.append(Order)
            response = self.GateComm.submit_order(Order)
            return {'status':'success',
                    'data':{'action':'submit_order',
                            'response':response}}


    def SendEvent(self, data):
        TypeEvent,DataEvent = data['EventType'],data['data']
        response = self.CurStrat.ProcessEvent(TypeEvent,DataEvent)
        return response