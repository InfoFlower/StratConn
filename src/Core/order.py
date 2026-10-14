from dataclasses import dataclass, field, asdict
from typing import Optional, Dict
from .tb_types import Side, OrderType, OrderStatus, Asset

@dataclass
class Order:

    asset : Asset
    asset_qty : float
    base : Asset
    side : Side
    status : OrderStatus
    type : OrderType
    leverage : Optional[float] = 1.0
    level : Optional[float] = None
    execution_price : Optional[float] = None
    tp_price: Optional[float] = None
    sl_price : Optional[float] = None
    id : Optional[int] = None

    def set(self, **kwargs):
        """Met à jour les attributs de l'objet avec les paires clé:valeur fournies."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"L'attribut '{key}' n'existe pas dans {self.__class__.__name__}")
    
    def asdict(self):
        return asdict(self)