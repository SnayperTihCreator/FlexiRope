from .rope import SmartRope


def rope_factory(plugin_cls, wrapper_class=None, **default_plugin_kwargs):
    def decorator(func=None, **call_kwargs):
        final_params = {**default_plugin_kwargs, **call_kwargs}
        
        def wrapper(f):
            p = plugin_cls(**final_params)
            return SmartRope(wrapper_class, plugins=[p])(f)
        
        return wrapper(func) if (func is not None and callable(func)) else wrapper
    
    return decorator
