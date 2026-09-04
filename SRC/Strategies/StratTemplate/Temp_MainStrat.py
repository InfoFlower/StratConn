from Core.request import REQUEST
from Core.order import Order
from Core.tb_types import Asset, OrderStatus, OrderType, Side, EventType
from Strategies.Utils import GetOrderById
from random import randint

class strategie:
    def __init__(self):
        self.Last_Price = 0
        self.default_params = {'asset':Asset.BTC, 
                          'asset_qty':1, 
                          'base':Asset.EUR, 
                          'status': OrderStatus.REQUESTED, 
                          'type':OrderType.MARKET, 
                          'side':Side.SHORT}
        return None
    
    def ProcessPrice(self, Price, timestamp):
        Request = {'request': REQUEST.STILL}
        self.cur_price = Price
        self.cur_time = timestamp
        CONDITION = randint(0,100)
        if CONDITION<50 :
            Request = {'request':REQUEST.SUBMIT_ORDER,
                    'params':Order(**self.default_params)}
        elif CONDITION>90 :
            OrderId = GetOrderById()            
            Request = {'request':REQUEST.CANCEL_ORDER,
                    'params':OrderId}
        elif CONDITION>80 :
                OrderId = GetOrderById()            
                Request = {'request':REQUEST.CANCEL_ORDER,
                        'params':OrderId}
        return Request

    def ProcessEvent(self, Event:EventType, Data=None):
        if Event==EventType.PRICE_UPDATE:
            pass
        if Event==EventType.ORDER_PLACED:
            pass
        if Event==EventType.ORDER_EXECUTED:
            pass
        if Event==EventType.ORDER_CANCELLED:
            pass
        if Event==EventType.POSITION_OPENED:
            pass
        if Event==EventType.POSITION_CLOSED:
            pass
        if Event==EventType.TP_TRIGGERED:
            pass
        if Event==EventType.SL_TRIGGERED:
            pass