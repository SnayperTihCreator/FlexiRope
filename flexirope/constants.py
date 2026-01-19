from typing import TypeVar, ParamSpec, Callable, Any, Type, Protocol

P = ParamSpec("P")
R = TypeVar("R")


class WireProtocol(Protocol[P, R]):
    _func: Callable
    _instance: Any
    _owner: Type
    _name: str
    
    def _invoke_flexible(self, func: Callable, *args: Any, **kwargs: Any) -> Any: ...
