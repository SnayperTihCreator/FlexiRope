import inspect
from typing import Any, Callable, Type, Generic, Optional, List
from .constants import P, R


class BaseWire(Generic[P, R]):
    def __init__(self, func: Callable, instance: Any, owner: Type, name: str, plugins: Optional[List] = None):
        self._func = func
        self._instance = instance
        self._owner = owner
        self._name = name
        self.plugins = plugins or []
        self._early_response = None
    
    def _invoke_flexible(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        if self._instance is not None:
            return func(self._instance, *args, **kwargs)
        return func(*args, **kwargs)
    
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._early_response = None
        for p in self.plugins:
            # ПРОВЕРКА: BaseWire не терпит асинхронных плагинов
            if inspect.iscoroutinefunction(getattr(p, 'before', None)):
                raise TypeError(f"Plugin {p.__class__.__name__} is async, but wire {self._name} is sync!")
            
            if hasattr(p, 'before'):
                args, kwargs = p.before(self, args, kwargs)
            
            if self._early_response is not None:
                return self._early_response
        
        result = self._invoke_flexible(self._func, *args, **kwargs)
        
        for p in reversed(self.plugins):
            if inspect.iscoroutinefunction(getattr(p, 'after', None)):
                raise TypeError(f"Plugin {p.__class__.__name__} is async, but wire {self._name} is sync!")
            
            if hasattr(p, 'after'):
                result = p.after(self, result)
        return result


class AsyncWire(BaseWire[P, R]):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._execute_async(*args, **kwargs)
    
    async def _execute_async(self, *args: Any, **kwargs: Any) -> Any:
        self._early_response = None
        for p in self.plugins:
            # AsyncWire работает со всеми: и sync, и async
            before_method = getattr(p, 'before', None)
            if before_method:
                if inspect.iscoroutinefunction(before_method):
                    args, kwargs = await before_method(self, args, kwargs)
                else:
                    args, kwargs = before_method(self, args, kwargs)
            
            if self._early_response is not None:
                return self._early_response
        
        res = self._invoke_flexible(self._func, *args, **kwargs)
        result = await res if inspect.isawaitable(res) else res
        
        for p in reversed(self.plugins):
            after_method = getattr(p, 'after', None)
            if after_method:
                if inspect.iscoroutinefunction(after_method):
                    result = await after_method(self, result)
                else:
                    result = after_method(self, result)
        return result
    
    def __await__(self):
        return self._execute_async().__await__()