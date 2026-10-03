"""
Point d'entrée de l'application FastAPI.

Lancement : uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import agriculture, health
from app.core.config import reglages
from app.core.errors import enregistrer_gestionnaires_erreurs

PREFIXE_API = "/api/v1"

app = FastAPI(
    title=reglages.nom_application,
    description="Service IA vocal pour les agriculteurs (ASR → Agriculture → TTS).",
    version="0.1.0",
)

enregistrer_gestionnaires_erreurs(app)

app.include_router(health.router, prefix=PREFIXE_API)
app.include_router(agriculture.router, prefix=PREFIXE_API)

# Les fichiers audio générés sont accessibles via /audio/<nom_du_fichier>.wav
reglages.dossier_audio_sortie.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=reglages.dossier_audio_sortie), name="audio")
