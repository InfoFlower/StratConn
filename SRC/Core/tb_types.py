from enum import Enum, auto

class Side(Enum):
    LONG = auto()
    SHORT = auto()

class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()

class OrderStatus(Enum):
    REQUESTED = auto()
    PENDING = auto()
    EXECUTED = auto()
    CANCELLED = auto()

class PositionStatus(Enum):
    OPENED = auto()
    CLOSED = auto()

class EventType(Enum):

    PRICE_UPDATE = auto()
    ORDER_PLACED = auto()
    ORDER_EXECUTED = auto()
    ORDER_CANCELLED = auto()
    POSITION_OPENED = auto()
    POSITION_CLOSED = auto()
    TP_TRIGGERED = auto()
    SL_TRIGGERED = auto()

class Asset(Enum):

    BTC = auto()
    ETH = auto()
    SOL = auto()
    EUR = auto()
    USD = auto()

    