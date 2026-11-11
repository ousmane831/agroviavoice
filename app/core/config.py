"""
Configuration centrale du service.

Les réglages viennent du fichier `.env` (sinon, les valeurs par défaut ci-dessous).
Les modèles Kiriku tournent EN LOCAL sur le serveur : aucune API externe.
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
    # Modèles locaux
    # -----------------------------------------------------------------------

    # Jeton Hugging Face : utile UNIQUEMENT pour télécharger les modèles
    # (scripts/telecharger_modeles.py). Le service lui-même n'en a pas besoin.
    hf_token: str | None = None

    # Dossier où sont rangés les modèles téléchargés / convertis.
    dossier_modeles: Path = DOSSIER_PROJET / "models"

    # "cpu" (VPS sans GPU) ou "cuda" (serveur avec GPU NVIDIA).
    appareil: str = "cpu"

    # Nombre de cœurs CPU utilisés par les modèles (0 = automatique).
    nombre_threads: int = 0

    # ASR (faster-whisper) : "int8" = rapide et léger sur CPU,
    # "float16" conseillé sur GPU.
    asr_type_calcul: str = "int8"

    # 1 = le plus rapide (recommandé sur CPU), 5 = un peu plus précis mais plus lent.
    asr_beam_size: int = 1

    # Charger les modèles au démarrage (sinon : à la première requête, qui sera lente).
    precharger_modeles: bool = True

    # -----------------------------------------------------------------------
    # Outils et dossiers audio
    # -----------------------------------------------------------------------

    # Chemin vers ffmpeg. "ffmpeg" = celui trouvé dans le PATH.
    chemin_ffmpeg: str = "ffmpeg"

    dossier_audio_entree: Path = DOSSIER_PROJET / "audio" / "input"
    dossier_audio_sortie: Path = DOSSIER_PROJET / "audio" / "output"

    # -----------------------------------------------------------------------
    # Limites
    # -----------------------------------------------------------------------

    taille_max_audio_mo: int = 10
    duree_max_audio_secondes: int = 60
    longueur_max_texte: int = 1000

    # Les réponses audio plus vieilles que ce nombre d'heures sont supprimées.
    duree_conservation_audio_heures: int = 24

    # -----------------------------------------------------------------------
    # Conseils agricoles
    # -----------------------------------------------------------------------

    # Base de conseils (modifiable sans toucher au code).
    chemin_conseils: Path = DOSSIER_PROJET / "app" / "data" / "conseils.json"

    # Journal des questions posées (une ligne JSON par question) : sert à
    # repérer les questions restées sans réponse. Ne contient ni nom ni parcelle.
    journaliser_questions: bool = True
    chemin_journal_questions: Path = DOSSIER_PROJET / "logs" / "questions.jsonl"

    model_config = {"env_file": DOSSIER_PROJET / ".env", "extra": "ignore"}

    @property
    def dossier_asr(self) -> Path:
        """Modèle ASR converti au format faster-whisper (CTranslate2)."""
        return self.dossier_modeles / "asr" / "m-kiriku-asr-ct2"

    def dossier_tts(self, langue: str) -> Path:
        return self.dossier_modeles / "tts" / langue


reglages = Reglages()


# ===========================================================================
# LANGUES
# ===========================================================================

# Toutes les langues connues du projet (même celles pas encore disponibles).
NOMS_LANGUES = {
    "wolof": "Wolof",
    "pulaar": "Pulaar",
    "serere": "Sérère",
}


# ===========================================================================
# MODÈLES (noms Hugging Face définis UNIQUEMENT ici)
# ===========================================================================

# ASR : un seul modèle multilingue pour les trois langues.
MODELE_ASR_HF = "AIHubSN/M-Kiriku-ASR"

# Code de langue Whisper attendu par M-Kiriku-ASR (le modèle reçoit le jeton
# "<|code|>"). Le script de téléchargement vérifie que ces jetons existent
# bien dans le tokenizer du modèle et affiche la liste réelle sinon.
LANGUES_ASR = {
    "wolof": "wo",
    "pulaar": "pu",
    "serere": "se",
}

# TTS : texte -> audio (VITS). Aucun modèle Sérère n'existe pour l'instant.
MODELES_TTS = {
    "wolof": "AIHubSN/Kiriku-Wolof-TTS",
    "pulaar": "AIHubSN/Kiriku-Pulaar-TTS",
}
