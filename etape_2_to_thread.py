"""
ÉTAPE 2 — TaskGroup + to_thread (LA VRAIE SOLUTION)

Seule différence avec l'étape 1 : process_message délègue l'appel bloquant à
un thread via asyncio.to_thread. La coroutine rend la main pendant le download
→ l'event loop continue de tourner → les heartbeats passent et les 5 downloads
se chevauchent vraiment. Durée ~3-4s.

    uv run etape_2_to_thread.py

Le réflexe à retenir : une lib sync qui fait de l'I/O (boto3, requests,
psycopg2...) → asyncio.to_thread. C'est le pont entre une lib qui ne connaît
pas asyncio et votre event loop.

Le diff qui contient toute la leçon :  diff etape_1_taskgroup.py etape_2_to_thread.py
"""

import asyncio
import time
from fake_s3 import download_file

MESSAGES = ["file_a.zip", "file_b.zip", "file_c.zip", "file_d.zip", "file_e.zip"]

HEARTBEAT_INTERVAL = 1.0
HEARTBEAT_TIMEOUT = 2.0


async def heartbeat() -> None:
    last = time.monotonic()
    while True:
        now = time.monotonic()
        delta = now - last
        if delta > HEARTBEAT_TIMEOUT:
            print(f"💀 HEARTBEAT MANQUÉ (delta={delta:.2f}s) — worker considéré mort")
        else:
            print(f"💓 heartbeat (delta={delta:.2f}s)")
        last = now
        await asyncio.sleep(HEARTBEAT_INTERVAL)


async def process_message(key: str) -> None:
    """to_thread délègue l'appel bloquant à un thread → la coroutine rend la main."""
    await asyncio.to_thread(download_file, "my-bucket", key)


async def worker() -> None:
    async with asyncio.TaskGroup() as tg:
        for key in MESSAGES:
            tg.create_task(process_message(key))


async def main() -> None:
    hb_task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.1)

    start = time.monotonic()
    await worker()
    duration = time.monotonic() - start

    print(f"\n⏱️  Durée totale du worker : {duration:.1f}s")
    print("   Théoriquement, en vraie concurrence : ~3-4s")
    print("   En série bloquante : ~15s")

    await asyncio.sleep(2)

    hb_task.cancel()
    try:
        await hb_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
