"""
Worker qui doit télécharger 5 fichiers depuis un stockage distant.

PROBLÈME EN PROD :
1. Les downloads s'enchaînent en série au lieu d'être concurrents (5x plus lent que prévu)
2. L'event loop est gelée pendant les downloads → les heartbeats sautent
3. L'orchestrateur considère le worker mort et le redémarre → boucle infinie

VOTRE MISSION : corriger les 3 TODO ci-dessous dans worker().
"""

import asyncio
import time
from fake_s3 import download_file

# Liste des fichiers à télécharger (simule des messages d'une queue)
MESSAGES = ["file_a.zip", "file_b.zip", "file_c.zip", "file_d.zip", "file_e.zip"]

# Configuration du heartbeat
HEARTBEAT_INTERVAL = 1.0  # On envoie un heartbeat toutes les 1s
HEARTBEAT_TIMEOUT = 2.0  # Si delta > 2s, le worker est considéré mort


async def heartbeat() -> None:
    """
    Tourne en parallèle du worker.
    Affiche un battement toutes les secondes — si la loop est gelée,
    le delta entre deux battements explose et on voit le worker "mourir".
    """
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


def process_message(key: str) -> None:
    """Traite un message : télécharge le fichier correspondant."""
    content = download_file("my-bucket", key)
    # Ici on ferait quelque chose du contenu (le pousser dans une DB, etc.)


async def worker() -> None:
    """
    Le worker à corriger.

    TODO 1 : Traiter les 5 messages EN CONCURRENCE.
             Au choix :
               - asyncio.TaskGroup (3.11+) :
                   async with asyncio.TaskGroup() as tg: tg.create_task(...)
               - asyncio.gather (3.7+) :
                   await asyncio.gather(*[coro(key) for key in MESSAGES])

             ⚠️ Faites tourner après cette étape SEULE. Que constatez-vous ?
             Les downloads se chevauchent-ils vraiment ? Les heartbeats reviennent-ils ?

    TODO 2 : process_message contient un appel BLOQUANT (download_file).
             Faites-le tourner dans un thread pour qu'il ne gèle pas la loop.
             (Indice : asyncio.to_thread(func, *args))

    TODO 3 (bonus) : Limiter à 2 downloads simultanés maximum.
             (Indice : asyncio.Semaphore(2))
    """
    for key in MESSAGES:
        process_message(key)


async def main() -> None:
    # Lance le heartbeat en arrière-plan
    hb_task = asyncio.create_task(heartbeat())

    # Petite pause pour laisser le heartbeat démarrer et afficher son premier battement
    # (sinon worker() bloque la loop avant même que heartbeat n'ait tourné une fois)
    await asyncio.sleep(0.1)

    start = time.monotonic()
    await worker()
    duration = time.monotonic() - start

    print(f"\n⏱️  Durée totale du worker : {duration:.1f}s")
    print("   Théoriquement, en vraie concurrence : ~3-4s")
    print("   En série bloquante : ~15s")

    # Laisse le heartbeat reprendre ses esprits pour voir le retour à la normale
    await asyncio.sleep(2)

    # On arrête le heartbeat proprement
    _ = hb_task.cancel()
    try:
        await hb_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
