from .receptionist_core import Receptionist as CoreReceptionist
from infrastructure.container import container

class Receptionist(CoreReceptionist):
    def __init__(self, critic=None, assimilator=None):
        super().__init__(container=container, critic=critic, assimilator=assimilator)

__all__ = ["Receptionist"]
