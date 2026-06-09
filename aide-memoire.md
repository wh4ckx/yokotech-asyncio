# Aide-mémoire asyncio — les outils de l'exo

Une syntaxe par bloc. À garder ouvert pendant que vous codez.

---

## `async` / `await` — les briques de base

```python
async def download(key):        # définit une COROUTINE (pas exécutée à l'appel)
    data = await fetch(key)      # await = "je rends la main, réveille-moi quand c'est prêt"
    return data

asyncio.run(download("a.zip"))   # le point d'entrée : crée la loop, exécute, ferme
```

- `async def` fabrique un **objet coroutine**. L'appeler ne l'exécute pas — il faut un `await` ou la loop.
- `await` n'est PAS un blocage : c'est une **suspension**. La loop part faire autre chose pendant l'attente I/O.
- ⚠️ `await` ne marche que dans une `async def`.

---

## `create_task` — lancer en arrière-plan

```python
task = asyncio.create_task(download("a.zip"))   # démarre TOUT DE SUITE, en fond
...                                              # je fais autre chose pendant ce temps
result = await task                              # je récupère le résultat quand j'en ai besoin
```

- Sans `create_task`, `await coro()` est **séquentiel** (j'attends avant de continuer).
- ⚠️ **Gardez une référence** à la task (`task = ...`). Une task non référencée peut être garbage-collectée et son exception passe à la trappe.

---

## `TaskGroup` / `gather` — lancer N choses en concurrence

```python
# TaskGroup (Python 3.11+) — le défaut moderne
async with asyncio.TaskGroup() as tg:
    for key in keys:
        tg.create_task(download(key))
# à la sortie du bloc : tout est terminé

# gather (Python 3.7+) — équivalent, marche partout
results = await asyncio.gather(*[download(key) for key in keys])
```

| | `TaskGroup` | `gather` |
|---|---|---|
| Version | 3.11+ | 3.7+ |
| Si une tâche échoue | annule les autres proprement | les autres continuent |
| Renvoie les résultats | non (à récupérer via les tasks) | oui, une liste |

⚠️ **Ne crée PAS de concurrence par magie.** Il orchestre des coroutines qui *rendent la main*. Si une coroutine ne fait aucun `await` (code 100% bloquant), elle s'exécute en bloc → fausse concurrence.

---

## `to_thread` — faire tourner du code BLOQUANT sans geler la loop

```python
await asyncio.to_thread(download_file, "my-bucket", key)
#                       └─ fonction sync ─┘ └─ ses arguments ─┘
```

- Le **pont** entre une lib sync I/O (`boto3`, `requests`, `psycopg2`...) et l'event loop.
- Pendant que le thread bloque, **la loop continue de tourner** (heartbeats, autres coroutines).
- Se combine naturellement avec `TaskGroup`/`gather` :
  ```python
  async with asyncio.TaskGroup() as tg:
      for key in keys:
          tg.create_task(asyncio.to_thread(download_file, "my-bucket", key))
  ```
- 💡 Réflexe : **lib sync qui fait de l'I/O → `to_thread`**.

---

## `Semaphore` — borner la concurrence

```python
sem = asyncio.Semaphore(2)          # 2 en parallèle MAX

async def bounded(key):
    async with sem:                 # attend si 2 sont déjà en cours
        await asyncio.to_thread(download_file, "my-bucket", key)
```

- Évite de saturer bande passante / DB / thread pool quand vous lancez beaucoup de tâches.
- ⚠️ Créez UN sémaphore partagé, passez-le aux coroutines (pas un par appel).

---

## Quel outil, quand ?

| Situation | Outil |
|---|---|
| Lib **async native** (httpx, aiohttp, asyncpg) | `await` + `TaskGroup` / `gather` |
| Lib **sync** incontournable qui fait de l'**I/O** (boto3, requests…) | `to_thread` |
| Trop de tâches en parallèle, ressources saturées | `Semaphore(N)` |
| **Calcul CPU lourd** (parsing, ML, crunching) | ni l'un ni l'autre → sortez d'asyncio (`multiprocessing`) |

> **Asyncio ne rend pas le code plus rapide. Il évite d'attendre bêtement pendant les I/O.**
