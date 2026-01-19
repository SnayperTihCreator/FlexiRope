import asyncio
import pytest
import inspect
from flexirope import SmartRope, support_ropes, SyncPlugin, AsyncPlugin, rope_factory


# --- 1. Моки плагинов для тестов ---

class SyncCounterPlugin:
    """Простой синхронный плагин для подсчета вызовов."""
    
    def __init__(self): self.count = 0
    
    def before(self, wire, args, kwargs):
        self.count += 1
        return args, kwargs


class AsyncTracePlugin:
    """Асинхронный плагин для проверки await логики."""
    
    async def before(self, wire, args, kwargs):
        await asyncio.sleep(0.001)
        if not hasattr(wire, 'trace'): wire.trace = []
        wire.trace.append("async_before")
        return args, kwargs


class EarlyReturnPlugin:
    """Плагин для проверки прерывания выполнения (кэш-эффект)."""
    
    def before(self, wire, args, kwargs):
        if args and args[0] == "shortcut":
            wire._early_response = "fast_track"
        return args, kwargs


# --- 2. Тесты универсальности вызова (Standalone, Methods, Static, Class) ---

def test_standalone_function():
    plugin = SyncCounterPlugin()
    
    @SmartRope(plugins=[plugin])
    def add(a, b): return a + b
    
    assert add(2, 3) == 5
    assert plugin.count == 1


@support_ropes
class MultiService:
    __slots__ = ("__weakref__", "factor")
    
    def __init__(self, factor): self.factor = factor
    
    @SmartRope(plugins=[SyncCounterPlugin()])
    def instance_method(self, x): return x * self.factor
    
    @classmethod
    @SmartRope(plugins=[SyncCounterPlugin()])
    def class_method(cls, x): return f"cls_{x}"
    
    @staticmethod
    @SmartRope(plugins=[SyncCounterPlugin()])
    def static_method(x): return x + 1


def test_all_method_types():
    obj = MultiService(10)
    assert obj.instance_method(2) == 20
    assert MultiService.class_method("test") == "cls_test"
    assert MultiService.static_method(5) == 6


# --- 3. Тесты асинхронности и смешанных плагинов ---

@pytest.mark.asyncio
async def test_async_wire_mixed_plugins():
    plugin_sync = SyncCounterPlugin()
    plugin_async = AsyncTracePlugin()
    
    class AsyncApp:
        @SmartRope(plugins=[plugin_sync, plugin_async])
        async def run(self): return "done"
    
    app = AsyncApp()
    result = await app.run()
    
    assert result == "done"
    assert plugin_sync.count == 1
    assert app.run.trace == ["async_before"]


# --- 4. Тест защиты BaseWire от асинхронных плагинов ---

def test_sync_wire_safety():
    class AsyncOnlyPlugin:
        async def before(self, wire, args, kwargs): return args, kwargs
    
    @SmartRope(plugins=[AsyncOnlyPlugin()])
    def sync_func(): return "no"
    
    with pytest.raises(TypeError, match="is async, but wire sync_func is sync"):
        sync_func()


# --- 5. Тест слияния декораторов (Stacking) ---

def test_decorator_flattening():
    p1 = SyncCounterPlugin()
    p2 = SyncCounterPlugin()
    
    @SmartRope(plugins=[p1])
    @SmartRope(plugins=[p2])
    def double_wrapped(): return "ok"
    
    # Должен быть ОДИН SmartRope в итоге
    assert isinstance(double_wrapped, SmartRope)
    assert len(double_wrapped.plugins) == 2
    assert double_wrapped() == "ok"
    assert p1.count == 1
    assert p2.count == 1


# --- 6. Тест Early Return (Кэширование) ---

@pytest.mark.asyncio
async def test_early_return():
    plugin = EarlyReturnPlugin()
    
    @SmartRope(plugins=[plugin])
    async def data_fetcher(mode):
        await asyncio.sleep(1)  # Должно пропуститься
        return "real_data"
    
    assert await data_fetcher("shortcut") == "fast_track"
    assert await data_fetcher("normal") == "real_data"


# --- 7. Тест .register() проксирования ---

class OverloadMock:
    def __init__(self): self.reg = {}
    
    def register(self, types, func): self.reg[types] = func


def test_register_proxy():
    plugin = OverloadMock()
    
    @SmartRope(plugins=[plugin])
    def base(): pass
    
    @base.register(int)
    def overloaded_int(x): return x
    
    assert (int,) in plugin.reg
    assert plugin.reg[(int,)] == overloaded_int