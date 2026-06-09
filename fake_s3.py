"""
Module de simulation d'un client S3 synchrone.
Représente ce que fait boto3 : du blocage I/O qui ne rend jamais la main à l'event loop.

NE PAS MODIFIER CE FICHIER.
"""
import time
import random


def download_file(bucket: str, key: str) -> bytes:
    """
    Simule un téléchargement S3 : bloque le thread courant pendant 2 à 4 secondes.

    C'est exactement le comportement de boto3.s3.download_file : un appel sync
    qui ne connaît rien à asyncio et qui ne rend jamais la main pendant l'I/O.
    """
    duration = random.uniform(2.0, 4.0)
    print(f"  ⬇️  START  {key} (durée prévue: {duration:.1f}s)")
    time.sleep(duration)  # ← Blocage volontaire, simule l'I/O réseau
    print(f"  ✅ END    {key}")
    return b"file content for " + key.encode()
