# asyncio-workshop — "Sauve le worker"

Mini-exercice de 5 minutes pour le Yokotech asyncio.

## Contexte

Un worker doit télécharger 5 fichiers depuis un stockage distant. Il a été écrit avec asyncio pour traiter les messages en concurrence. En prod :

1. **Les downloads s'enchaînent en série** (15s au lieu des ~3s attendues)
2. **Les heartbeats sautent** → l'orchestrateur déclare le worker mort et le redémarre → boucle infinie

À vous de réparer ça.

## Prérequis

- **Python 3.11+** pour les fichiers de solution `etape_*.py` (qui utilisent `asyncio.TaskGroup`).
  Pour l'exo, `asyncio.gather` suffit et marche dès Python 3.7+.
- Aucune dépendance externe (stdlib uniquement)

## Setup (30 secondes)

Avec [uv](https://docs.astral.sh/uv/) (recommandé — gère la version de Python tout seul) :

```bash
git clone <ce-repo> asyncio-workshop
cd asyncio-workshop
uv run worker_broken.py   # uv installe Python 3.13 (cf. .python-version) et lance
```

Sans uv (Python système) :

```bash
python3 --version         # doit afficher >= 3.11 pour les fichiers etape_*.py
python3 worker_broken.py
```

Vous devriez voir :
- Des `START` / `END` de downloads qui s'enchaînent **en série** (pas concurrents)
- Des `💀 HEARTBEAT MANQUÉ` qui apparaissent
- Une durée totale d'environ **15 secondes**

Si c'est ce que vous obtenez, **vous êtes prêt pour l'exo**.

## L'exercice

Ouvrez `worker_broken.py` et corrigez les 3 TODO **dans l'ordre** :

### TODO 1 — Concurrence avec TaskGroup ou gather

Faites tourner les 5 `process_message` en concurrence. Deux options selon votre version de Python :

```python
# asyncio.TaskGroup (Python 3.11+) — c'est ce qu'utilisent les fichiers etape_*.py
async with asyncio.TaskGroup() as tg:
    for key in MESSAGES:
        tg.create_task(...)

# asyncio.gather (Python 3.7+) — équivalent ici, marche partout
await asyncio.gather(*[process_message(key) for key in MESSAGES])
```

**Relancez le script. Que constatez-vous ?**

(C'est volontaire. La leçon arrive au TODO 2.)

### TODO 2 — Débloquer la loop avec to_thread

`download_file` est une fonction sync bloquante. Faites-la tourner dans un thread :

```python
await asyncio.to_thread(download_file, "my-bucket", key)
```

Relancez. Cette fois, les `START` doivent se chevaucher, les heartbeats doivent survivre, et la durée totale doit tomber à ~3-4 secondes.

### TODO 3 (bonus) — Limiter la concurrence

En prod, on ne veut pas saturer la bande passante. Limitez à 2 downloads simultanés max avec un sémaphore :

```python
sem = asyncio.Semaphore(2)

async def bounded(key):
    async with sem:
        await asyncio.to_thread(download_file, "my-bucket", key)
```

## Solution

La correction est découpée en 3 fichiers indépendants, à lancer **un par un** dans l'ordre :

```bash
uv run etape_1_taskgroup.py   # le piège : ~15s, heartbeats sautent (RIEN ne change)
uv run etape_2_to_thread.py   # la vraie solution : ~3-4s, heartbeats OK
uv run etape_3_semaphore.py   # bonus : Semaphore(2), ~7-10s, heartbeats OK
```

Chaque fichier mirrore `worker_broken.py` : le `diff` montre exactement ce qui change.

```bash
diff worker_broken.py etape_1_taskgroup.py   # ajouter TaskGroup
diff etape_1_taskgroup.py etape_2_to_thread.py   # +to_thread → toute la leçon en 1 ligne
diff etape_2_to_thread.py etape_3_semaphore.py   # +Semaphore
```

## Ce que vous devriez retenir

1. **`TaskGroup` ne crée pas de concurrence par magie.** Il orchestre des coroutines qui rendent la main. Une coroutine 100% bloquante reste bloquante.
2. **`to_thread` est le pont entre une lib sync I/O et l'event loop.** Réflexe à avoir dès que vous croisez `boto3`, `requests`, `psycopg2` (sync), etc.
3. **`Semaphore` pour borner la concurrence**, sinon vous saturez vos ressources avant l'event loop.
