"""
Vérification des langues demandées par l'utilisateur.

Deux cas d'erreur différents :
- langue inconnue du projet                          -> LANGUAGE_NOT_SUPPORTED
- langue connue mais sans modèle (ex. Sérère en TTS) -> LANGUAGE_NOT_AVAILABLE
"""

from app.core.config import MODELES_ASR, MODELES_TTS, NOMS_LANGUES
from app.core.errors import ErreurApp


def normaliser_langue(langue: str) -> str:
    """Met la langue en minuscules et vérifie qu'elle est connue du projet."""
    code_langue = langue.strip().lower()
    if code_langue not in NOMS_LANGUES:
        raise ErreurApp("LANGUAGE_NOT_SUPPORTED", "La langue demandée n'est pas supportée.")
    return code_langue


def verifier_langue_asr(langue: str) -> str:
    """Retourne le code de la langue si un modèle ASR existe pour elle."""
    code_langue = normaliser_langue(langue)
    if code_langue not in MODELES_ASR:
        raise ErreurApp(
            "LANGUAGE_NOT_AVAILABLE",
            f"La langue {NOMS_LANGUES[code_langue]} n'est pas encore disponible.",
        )
    return code_langue


def verifier_langue_tts(langue: str) -> str:
    """Retourne le code de la langue si un modèle TTS existe pour elle."""
    code_langue = normaliser_langue(langue)
    if code_langue not in MODELES_TTS:
        raise ErreurApp(
            "LANGUAGE_NOT_AVAILABLE",
            f"La langue {NOMS_LANGUES[code_langue]} n'est pas encore disponible.",
        )
    return code_langue
