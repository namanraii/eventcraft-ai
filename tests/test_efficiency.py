"""Cache behavior: stable keys, TTL expiry, and least-recently-used eviction."""

from __future__ import annotations

from src.core.cache import ResponseCache, plan_cache_key


def test_cache_key_ignores_dict_order() -> None:
    first = plan_cache_key({"b": 1, "a": {"d": 2, "c": 3}})
    second = plan_cache_key({"a": {"c": 3, "d": 2}, "b": 1})
    assert first == second
    assert first != plan_cache_key({"a": {"c": 4, "d": 2}, "b": 1})


def test_ttl_expiry(monkeypatch) -> None:
    clock = {"now": 1_000.0}
    monkeypatch.setattr("src.core.cache.time.monotonic", lambda: clock["now"])
    cache = ResponseCache(max_entries=4, ttl_seconds=10)
    cache.set("plan", {"ok": True})
    assert cache.get("plan") == {"ok": True}
    clock["now"] = 1_011.0
    assert cache.get("plan") is None
    assert cache.misses == 1


def test_lru_eviction(monkeypatch) -> None:
    monkeypatch.setattr("src.core.cache.time.monotonic", lambda: 50.0)
    cache = ResponseCache(max_entries=2, ttl_seconds=100)
    cache.set("a", {"n": 1})
    cache.set("b", {"n": 2})
    assert cache.get("a") == {"n": 1}
    cache.set("c", {"n": 3})
    assert cache.get("b") is None
    assert cache.get("a") == {"n": 1}
    assert cache.get("c") == {"n": 3}
