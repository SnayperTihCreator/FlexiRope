import weakref
import functools
import inspect

from .wire import BaseWire, AsyncWire


def support_ropes(cls):
    if not hasattr(cls, "__slots__"): return cls
    if "__weakref__" in cls.__slots__: return cls
    new_slots = tuple(cls.__slots__) + ("__weakref__",)
    namespace = {k: v for k, v in cls.__dict__.items()
                 if k not in ("__slots__", "__weakref__") and k not in cls.__slots__}
    return type(cls.__name__, cls.__bases__, {"__slots__": new_slots, **namespace})


class SmartRope:
    def __init__(self, wrapper_class=None, plugins: list = None):
        self.wire_class = wrapper_class
        self.plugins = plugins or []
        self.raw_func = None
        self.name = None
        self._wires = weakref.WeakKeyDictionary()
        self._global_wire = None
    
    def register(self, *types):
        def wrapper(func):
            target = next((p for p in self.plugins if hasattr(p, "register")), None)
            if not target:
                raise AttributeError("No plugin in this SmartRope supports .register()")
            target.register(types, func)
            return func
        
        return wrapper
    
    def __call__(self, *args, **kwargs):
        if self.raw_func is None:
            func = args[0]
            if isinstance(func, SmartRope):
                self.plugins = func.plugins + self.plugins
                if self.wire_class is None: self.wire_class = func.wire_class
                self.raw_func = func.raw_func
            else:
                self.raw_func = func
            if self.raw_func:
                functools.update_wrapper(self, self.raw_func)
            return self
        
        if self._global_wire is None:
            self._global_wire = self._get_wire(None, None)
        return self._global_wire(*args, **kwargs)
    
    def _get_wire(self, instance, owner):
        if instance is None and owner is None:
            if self._global_wire is None:
                self._global_wire = self._create_wire(None, None)
            return self._global_wire
        
        key = instance if instance is not None else owner
        if key not in self._wires:
            self._wires[key] = self._create_wire(instance, owner)
        return self._wires[key]
    
    def _create_wire(self, instance, owner):
        """Вынес логику создания в отдельный метод для чистоты."""
        obj = self.raw_func
        kind, func = 'method', obj
        if isinstance(obj, staticmethod):
            kind, func = 'static', obj.__func__
        elif isinstance(obj, classmethod):
            kind, func = 'class', obj.__func__
        elif isinstance(obj, property):
            kind, func = 'property', obj.fget
        
        actual_func = func
        actual_instance = instance
        if kind == 'class':
            actual_func = func.__get__(None, owner)
            actual_instance = None
        elif kind == 'static':
            actual_instance = None
        
        w_cls = self.wire_class or (AsyncWire if inspect.iscoroutinefunction(func) else BaseWire)
        
        return w_cls(
            func=actual_func, instance=actual_instance,
            owner=owner, name=self.name or getattr(func, "__name__", "unknown"),
            plugins=self.plugins
        )
    
    def __get__(self, instance, owner):
        if instance is None and not isinstance(self.raw_func, (classmethod, staticmethod)):
            return self
        return self._get_wire(instance, owner)
    
    def __set_name__(self, owner, name):
        self.name = name