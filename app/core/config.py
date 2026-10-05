
"""
Configuration centrale du service.

Les réglages viennent du fichier `.env`.
Les modèles Kiriku sont utilisés via l'API distante du concours.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


# Dossier racine du projet
DOSSIER_PROJET = Path(__file__).resolve().parents[2]


class Reglages(BaseSettings):
    nom_application: str = "Sama Agri Voice"
    nom_service: str = "sama-agri-ai"
    environnement: str = "development"
    hote: str = "0.0.0.0"
    port: int = 8001

    # -----------------------------------------------------------------------
    # API Kiriku distante
    # -----------------------------------------------------------------------

    kiriku_api_url: str = (
        "https://14hyb7tjwzuh9q-8000.proxy.runpod.net/v1"
    )
    kiriku_api_key: str | None = None

    # -----------------------------------------------------------------------
    # Dossiers audio
    # -----------------------------------------------------------------------

    dossier_audio_entree: Path = DOSSIER_PROJET / "audio" / "input"
    dossier_audio_sortie: Path = DOSSIER_PROJET / "audio" / "output"

    # -----------------------------------------------------------------------
    # Limites
    # -----------------------------------------------------------------------

    taille_max_audio_mo: int = 10

    # L'API Kiriku accepte jusqu'à 60 secondes par transcription.
    duree_max_audio_secondes: int = 60

    # L'API Kiriku accepte jusqu'à 512 caractères par synthèse TTS.
    longueur_max_texte: int = 512

    # -----------------------------------------------------------------------
    # Configuration .env
    # -----------------------------------------------------------------------

    model_config = {
        "env_file": DOSSIER_PROJET / ".env",
        "extra": "ignore",
    }


reglages = Reglages()


# ===========================================================================
# LANGUES
# ===========================================================================

# Toutes les langues connues du projet.
NOMS_LANGUES = {
    "wolof": "Wolof",
    "pulaar": "Pulaar",
    "serere": "Sérère",
}


# ===========================================================================
# MODÈLES API KIRIKU
# ===========================================================================

# ASR : audio -> texte.
#
# L'API distante utilise le même modèle pour les trois langues.
MODELES_ASR = {
    "wolof": {
        "nom_modele": "m-kiriku-asr",
    },
    "pulaar": {
        "nom_modele": "m-kiriku-asr",
    },
    "serere": {
        "nom_modele": "m-kiriku-asr",
    },
}


# TTS : texte -> audio.
#
# L'API Kiriku fournit actuellement Wolof et Pulaar.
# Il n'y a pas de voix Sérère.
MODELES_TTS = {
    "wolof": "kiriku-tts",
    "pulaar": "kiriku-tts",
}
