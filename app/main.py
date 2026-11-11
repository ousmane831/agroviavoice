"""
Point d'entrée de l'application FastAPI.

Lancement : python run.py   (ou : uvicorn app.main:app)

IMPORTANT : lancer UN SEUL worker. Chaque worker charge ses propres
modèles en mémoire (~4 Go) : 2 workers = 2 fois plus de RAM.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles

from app.api.routes import agriculture, health
from app.core.config import reglages
from app.core.errors import enregistrer_gestionnaires_erreurs
from app.services.model_loader import precharger_modeles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")

PREFIXE_API = "/api/v1"


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    if reglages.precharger_modeles:
        await run_in_threadpool(precharger_modeles)
    yield


app = FastAPI(
    title=reglages.nom_application,
    description="Service IA vocal pour les agriculteurs (ASR → Agriculture → TTS).",
    version="0.2.0",
    lifespan=cycle_de_vie,
)

enregistrer_gestionnaires_erreurs(app)

app.include_router(health.router, prefix=PREFIXE_API)
app.include_router(agriculture.router, prefix=PREFIXE_API)

# Les fichiers audio générés sont accessibles via /audio/<nom_du_fichier>.wav
reglages.dossier_audio_sortie.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=reglages.dossier_audio_sortie), name="audio")
