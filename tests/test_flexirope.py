import inspect

import pytest
from flexirope import SmartRope, support_ropes, SyncPlugin, AsyncPlugin


class MockPlugin(SyncPlugin):
    def before(self, wire, args, kwargs):
        wire.called_before = True
        return args, kwargs


# Тест обычной функции
@SmartRope(plugins=[MockPlugin()])
def standalone_func(x):
    return x + 1


def test_standalone_function():
    assert standalone_func(10) == 11
    assert standalone_func._global_wire.called_before is True


@support_ropes
class Service:
    __slots__ = ('name',)
    
    def __init__(self, name): self.name = name
    
    @SmartRope(plugins=[MockPlugin()])
    def process(self):
        return f"ok {self.name}"


def test_class_method_with_slots():
    srv = Service("test")
    assert srv.process() == "ok test"


# Тест асинхронности и invoke_flexible
class AsyncOverloadPlugin(AsyncPlugin):
    
    async def before(self, wire, args, kwargs):
        if args and isinstance(args[0], int):
            async def alt_func(instance, val): return val * 100
            
            res = wire._invoke_flexible(alt_func, *args, **kwargs)
            wire._early_response = await res if inspect.isawaitable(res) else res
        
        return args, kwargs


@pytest.mark.asyncio
async def test_async_invoke_flexible():
    class AsyncApp:
        @SmartRope(plugins=[AsyncOverloadPlugin()])
        async def run(self, data): return data
    
    app = AsyncApp()
    assert await app.run("string") == "string"  # Обычный вызов
    assert await app.run(5) == 500  # Перегруженный вызов через invoke_flexible


# Тест слияния декораторов
def test_decorator_merging():
    @SmartRope(plugins=[MockPlugin()])
    @SmartRope(plugins=[MockPlugin()])
    def merged(): return "merged"
    
    # Должен быть один SmartRope с двумя плагинами
    assert isinstance(merged, SmartRope)
    assert len(merged.plugins) == 2
