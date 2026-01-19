from typing import Protocol, Any, runtime_checkable
from .constants import P, R
from .wire import BaseWire, AsyncWire


@runtime_checkable
class SyncPlugin(Protocol):
    def before(self, wire: BaseWire[P, R], args: tuple, kwargs: dict) -> tuple[tuple, dict]: return args, kwargs
    
    def after(self, wire: BaseWire[P, R], result: Any) -> Any: return result


@runtime_checkable
class AsyncPlugin(Protocol):
    async def before(self, wire: AsyncWire[P, R], args: tuple, kwargs: dict) -> tuple[tuple, dict]: return args, kwargs
    
    async def after(self, wire: AsyncWire[P, R], result: Any) -> Any: return result
