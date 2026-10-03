"""
Chargement des modèles IA (ASR et TTS).

Grâce à @lru_cache, chaque modèle n'est chargé qu'UNE SEULE FOIS en mémoire
(Singleton) : le premier appel charge le modèle, les appels suivants
réutilisent directement le modèle déjà en mémoire.
"""

from functools import lru_cache
from pathlib import Path

from huggingface_hub import snapshot_download
from transformers import pipeline
from TTS.api import TTS

from app.core.config import MODELES_ASR, MODELES_TTS, reglages
from app.core.languages import verifier_langue_asr, verifier_langue_tts


@lru_cache()
def charger_modele_asr(nom_modele: str):
    """
    Charge un modèle Whisper Kiriku (audio -> texte) une seule fois.
    Pulaar et Sérère utilisent le même modèle (M-Kiriku-ASR) :
    il n'est donc chargé qu'une fois pour les deux langues.
    """
    transcripteur = pipeline(
        "automatic-speech-recognition",
        model=nom_modele,
        token=reglages.hf_token,
        model_kwargs={"cache_dir": reglages.dossier_modeles},
    )
    return transcripteur


@lru_cache()
def charger_modele_tts(nom_modele: str):
    """Charge un modèle VITS Kiriku (texte -> audio) une seule fois."""
    # Télécharge les fichiers du modèle dans le dossier models/
    dossier_modele = Path(
        snapshot_download(nom_modele, cache_dir=reglages.dossier_modeles, token=reglages.hf_token)
    )
    chemin_modele = next(dossier_modele.glob("*.pth"))
    chemin_config = dossier_modele / "config.json"

    synthetiseur = TTS(model_path=str(chemin_modele), config_path=str(chemin_config))
    return synthetiseur


def obtenir_modele_asr(langue: str):
    """Retourne le modèle ASR de la langue demandée (wolof, pulaar...)."""
    code_langue = verifier_langue_asr(langue)
    nom_modele = MODELES_ASR[code_langue]["nom_modele"]
    return charger_modele_asr(nom_modele)


def obtenir_modele_tts(langue: str):
    """Retourne le modèle TTS de la langue demandée (wolof, pulaar)."""
    code_langue = verifier_langue_tts(langue)
    nom_modele = MODELES_TTS[code_langue]
    return charger_modele_tts(nom_modele)


def transcrire_audio(echantillons, langue: str) -> str:
    """Transforme l'audio (16 kHz) en texte."""
    transcripteur = obtenir_modele_asr(langue)

    # M-Kiriku-ASR a besoin du token de la langue (ex. "<|pu|>")
    options = {"task": "transcribe"}
    token_langue = MODELES_ASR[langue]["token_langue"]
    if token_langue:
        options["language"] = token_langue

    resultat = transcripteur(
        {"raw": echantillons, "sampling_rate": 16000},
        generate_kwargs=options,
    )
    return resultat["text"].strip()


def synthetiser_texte(texte: str, langue: str):
    """Transforme le texte en audio. Retourne (echantillons, frequence)."""
    synthetiseur = obtenir_modele_tts(langue)
    echantillons = synthetiseur.tts(texte)
    frequence = synthetiseur.synthesizer.output_sample_rate
    return echantillons, frequence
