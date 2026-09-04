from dataclasses import dataclass, asdict
from zoneinfo import ZoneInfo 
from typing import Any, Dict, List, Callable
import datetime
from functools import wraps
from event import Event
from tb_types import EventType

class EventDispatcher:
    def __init__(self) -> None:
        self._listeners : Dict[EventType, List[Callable]] = {e: [] for e in EventType}

        #self._setup_event_logging()

    def add_listeners(self, event_type : EventType, callback : Callable) -> None:
        self._listeners[event_type].append(callback)
        
    def dispatch(self, event : Event) -> None:
        for callback in self._listeners[event.event_type]:
            callback(event)

    # Décorateur pour envoyer un événement après l'exécution d'une méthode
def dispatch_event(event_type: EventType, event_dispatcher_attr: str = "event_dispatcher", cur_timestamp: int=1716800000):
    """
    Décorateur pour envoyer un événement après l'exécution d'une méthode.

    Args:
        event_type: Le type d'événement à envoyer.
        event_dispatcher_attr: Le nom de l'attribut de la classe qui contient l'EventDispatcher.
                              Par défaut, on suppose que l'objet a un attribut `event_dispatcher`.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Exécute la méthode originale
            result = func(self, *args, **kwargs)

            # Récupère l'EventDispatcher depuis l'objet
            event_dispatcher = getattr(self, event_dispatcher_attr)

            # Envoie l'événement
            event_dispatcher.dispatch(Event(
                event_type=event_type,
                timestamp= datetime.datetime.fromtimestamp(cur_timestamp/1000, tz=datetime.timezone.utc),
                data=result,
            ))

            return result
        return wrapper
    return decorator
