from enum import Enum, auto

class REQUEST(Enum):
    SUBMIT_ORDER = auto()
    STILL = auto()
    CANCEL_ORDER = auto()
    CLOSE_POSITION = auto()
    GET_PRICE = auto()
    # Routes de lecture (docs/04-utils-strategie.md) : pas encore routées par ConnStrat ni par le broker
    GET_ORDERS = auto()
    GET_POSITIONS = auto()
    GET_WALLET = auto()