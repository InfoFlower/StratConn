from dataclasses import dataclass
from typing import Any
from datetime import datetime
from .tb_types import EventType

@dataclass
class Event:
    event_type : EventType
    timestamp : datetime
    data : Any
    