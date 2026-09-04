from dataclasses import dataclass, field
from typing import Optional
from .tb_types import Side, PositionStatus, Asset

@dataclass
class Position:

    id : int
    order_id : int 
    asset : Asset
    asset_qty : float
    base : Asset
    side : Side
    leverage : float
    status : PositionStatus
    entry : float
    tp_price : Optional[float] = None
    sl_price : Optional[float] = None
    close_price : Optional[float] = None
    close_justif : Optional[str] = None

    def set(self, **kwargs):
        """Met à jour les attributs de l'objet avec les paires clé:valeur fournies."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"L'attribut '{key}' n'existe pas dans {self.__class__.__name__}")
    
    def asdict(self):
        return asdict(self)