"""
ÉTAPE 1 — TaskGroup seul (LE PIÈGE PÉDAGOGIQUE)

On lance les 5 messages « en concurrence » avec un TaskGroup... mais
process_message reste 100% bloquant (aucun await dedans). Résultat : RIEN
ne change par rapport à la version séquentielle. Les downloads s'enchaînent
en série, les heartbeats sautent, durée ~15s.

    uv run etape_1_taskgroup.py

La leçon : TaskGroup orchestre des coroutines COOPÉRATIVES. Si aucune ne rend
la main (pas d'await), il n'y a aucune concurrence. On corrige ça à l'étape 2.

Comparez avec le point de départ :  diff worker_broken.py etape_1_taskgroup.py
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
    """async def, mais 100% bloquant : aucun await → la loop est gelée."""
    download_file("my-bucket", key)


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
