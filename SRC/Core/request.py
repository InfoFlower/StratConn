from enum import Enum, auto

class REQUEST(Enum):
    SUBMIT_ORDER = auto()
    STILL = auto()
    CANCEL_ORDER = auto()
    CLOSE_POSITION = auto()