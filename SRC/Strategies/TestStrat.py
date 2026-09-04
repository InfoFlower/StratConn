"""
Test Strategy for validating the trading system.
Simple strategy that submits orders based on price conditions.
"""

from SRC.Core.request import REQUEST
from SRC.Core.order import Order
from SRC.Core.tb_types import Asset, OrderStatus, OrderType, Side, EventType
from SRC.Strategies.Utils import GetOrderById


class strategie:
    """Test strategy with simple trading logic for validation."""
    
    def __init__(self):
        self.last_price = 0
        self.positions = []
        self.orders = []
        self.trade_count = 0
        self.max_trades = 5  # Limit trades for testing
        self.prices = []  # Track price history for technical analysis
        
        self.default_params = {
            'asset': Asset.BTC,
            'asset_qty': 0.5,
            'base': Asset.USD,
            'status': OrderStatus.REQUESTED,
            'type': OrderType.MARKET,
            'side': Side.LONG
        }
        print("[TestStrat] Initialized")
        return None

    def ProcessPrice(self, price, timestamp):
        """
        Process price updates and generate trading requests.
        Simple logic: buy on dips, sell on peaks.
        """
        self.last_price = price
        self.cur_time = timestamp
        self.prices.append(price)  # Track price history
        
        request = {'request': REQUEST.STILL}
        # Stop trading after max trades reached
        if self.trade_count >= self.max_trades:
            return request
        
        # Buy on significant dips (price drops 2% or more)
        if len(self.prices) >= 2:
            price_change = ((price - self.prices[-2]) / self.prices[-2]) * 100
            
            # BUY signal: 2% price drop
            if price_change < -2 and len(self.positions) < 2:
                request = {
                    'request': REQUEST.SUBMIT_ORDER,
                    'params': Order(**self.default_params, side=Side.LONG)
                }
                self.trade_count += 1
                print(f"[TestStrat] BUY signal at {price} (change: {price_change:.2f}%)")
            
            # SELL signal: 3% price increase
            elif price_change > 3 and len(self.positions) > 0:
                params = self.default_params.copy()
                params['side'] = Side.SHORT
                request = {
                    'request': REQUEST.SUBMIT_ORDER,
                    'params': Order(**params)
                }
                self.trade_count += 1
                print(f"[TestStrat] SELL signal at {price} (change: {price_change:.2f}%)")
        
        return request

    def ProcessEvent(self, event_type: EventType, data=None):
        """
        Process trading events.
        """
        if event_type == 'PRICE_UPDATE':
            print(f"[Event] Price update: {data}")
        
        elif event_type == 'ORDER_PLACED':
            print(f"[Event] Order placed: {data}")
            self.orders.append(data)
        
        elif event_type == 'ORDER_EXECUTED':
            print(f"[Event] Order executed: {data}")
        
        elif event_type == 'ORDER_CANCELLED':
            print(f"[Event] Order cancelled: {data}")
        
        elif event_type == 'POSITION_OPENED':
            print(f"[Event] Position opened: {data}")
            self.positions.append(data)
        
        elif event_type == 'POSITION_CLOSED':
            print(f"[Event] Position closed: {data}")
        
        elif event_type == 'TP_TRIGGERED':
            print(f"[Event] Take Profit triggered: {data}")
        
        elif event_type == 'SL_TRIGGERED':
            print(f"[Event] Stop Loss triggered: {data}")
        
        return {'status': 'processed', 'event': str(event_type)}
