from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="yieldvisor-async")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """
    Запускает coroutine из синхронного Django view.
    Если уже есть running loop (ASGI/async view), выполняет в отдельном потоке.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    future = _executor.submit(asyncio.run, coro)
    return future.result()
