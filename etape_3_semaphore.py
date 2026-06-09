"""
ÉTAPE 3 — TaskGroup + to_thread + Semaphore (SOLUTION FINALE, bonus)

Comme l'étape 2, mais on borne à 2 downloads simultanés avec un sémaphore.
En prod, on ne veut pas lancer 1000 downloads d'un coup : on saturerait la
bande passante, la DB ou le thread pool avant l'event loop. Durée ~7-8s,
heartbeats toujours OK.

    uv run etape_3_semaphore.py

Le diff avec l'étape 2 :  diff etape_2_to_thread.py etape_3_semaphore.py
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


async def process_message(key: str, sem: asyncio.Semaphore) -> None:
    """Le sémaphore borne à N le nombre de downloads simultanés."""
    async with sem:
        await asyncio.to_thread(download_file, "my-bucket", key)


async def worker() -> None:
    sem = asyncio.Semaphore(2)  # 2 downloads simultanés max
    async with asyncio.TaskGroup() as tg:
        for key in MESSAGES:
            tg.create_task(process_message(key, sem))


async def main() -> None:
    hb_task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.1)

    start = time.monotonic()
    await worker()
    duration = time.monotonic() - start

    print(f"\n⏱️  Durée totale du worker : {duration:.1f}s")
    print("   Avec Semaphore(2), on étale les downloads : ~7-10s")
    print("   Sans limite (étape 2) : ~3-4s")

    await asyncio.sleep(2)

    hb_task.cancel()
    try:
        await hb_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
