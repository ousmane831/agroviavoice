"""
Configuration centrale du service.

Les réglages viennent du fichier `.env` (sinon, les valeurs par défaut ci-dessous).
Les noms des modèles Hugging Face sont définis UNIQUEMENT ici.
"""

from pathlib import Path

from pydantic_settings import BaseSettings

# Dossier racine du projet (ai-service/)
DOSSIER_PROJET = Path(__file__).resolve().parents[2]


class Reglages(BaseSettings):
    nom_application: str = "Sama Agri Voice"
    nom_service: str = "sama-agri-ai"
    environnement: str = "development"
    hote: str = "0.0.0.0"
    port: int = 8001

    # Jeton Hugging Face : nécessaire car les modèles Kiriku sont "gated".
    hf_token: str | None = None

    # Dossiers où sont rangés les modèles et les fichiers audio
    dossier_modeles: Path = DOSSIER_PROJET / "models"
    dossier_audio_entree: Path = DOSSIER_PROJET / "audio" / "input"
    dossier_audio_sortie: Path = DOSSIER_PROJET / "audio" / "output"

    # Limites
    taille_max_audio_mo: int = 10
    # Whisper traite au maximum 30 secondes d'audio en une fois.
    duree_max_audio_secondes: int = 30
    longueur_max_texte: int = 500

    # Lit les valeurs du fichier .env
    model_config = {"env_file": DOSSIER_PROJET / ".env", "extra": "ignore"}


reglages = Reglages()


# ---------------------------------------------------------------------------
# Langues et modèles
# ---------------------------------------------------------------------------

# Toutes les langues connues du projet (même celles pas encore disponibles).
NOMS_LANGUES = {
    "wolof": "Wolof",
    "pulaar": "Pulaar",
    "serere": "Sérère",
}

# ASR : audio -> texte.
# `token_langue` : M-Kiriku-ASR est multilingue et doit recevoir le token
# de la langue (voir sa model card). Kiriku-Wolof-ASR n'en utilise pas.
MODELES_ASR = {
    "wolof": {"nom_modele": "AIHubSN/Kiriku-Wolof-ASR", "token_langue": None},
    "pulaar": {"nom_modele": "AIHubSN/M-Kiriku-ASR", "token_langue": "<|pu|>"},
    # M-Kiriku-ASR sait aussi transcrire le Sérère. Pour l'activer :
    # "serere": {"nom_modele": "AIHubSN/M-Kiriku-ASR", "token_langue": "<|se|>"},
}

# TTS : texte -> audio. Aucun modèle Sérère n'existe pour l'instant.
MODELES_TTS = {
    "wolof": "AIHubSN/Kiriku-Wolof-TTS",
    "pulaar": "AIHubSN/Kiriku-Pulaar-TTS",
}
