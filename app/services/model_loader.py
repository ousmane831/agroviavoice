"""
Chargement et utilisation des modèles IA en local (ASR et TTS).

- ASR (audio -> texte) : M-Kiriku-ASR converti pour faster-whisper (CTranslate2).
  Un seul modèle pour wolof, pulaar et sérère. En int8 sur CPU il tient en ~2 Go.
- TTS (texte -> audio) : modèles VITS Kiriku chargés avec coqui-tts.

Chaque modèle n'est chargé qu'UNE SEULE FOIS en mémoire, puis réutilisé.
Les modèles doivent d'abord être installés avec : python scripts/telecharger_modeles.py

Interface utilisée par le reste de l'application :
- transcrire_audio(echantillons, langue) -> str
- synthetiser_texte(texte, langue)       -> (echantillons, frequence)
"""

import logging
import threading

import numpy as np

from app.core.config import LANGUES_ASR, MODELES_TTS, reglages
from app.core.errors import ErreurApp
from app.core.languages import verifier_langue_asr, verifier_langue_tts

journal = logging.getLogger(__name__)

# Modèles déjà chargés : {"asr": ..., "tts:wolof": ...}
_modeles = {}
_verrou_chargement = threading.Lock()
# coqui-tts n'est pas prévu pour être appelé par plusieurs threads en même temps.
_verrou_tts = threading.Lock()


def _obtenir(cle: str, chargeur):
    """Charge un modèle la première fois, puis le réutilise."""
    if cle not in _modeles:
        with _verrou_chargement:
            if cle not in _modeles:
                _modeles[cle] = chargeur()
    return _modeles[cle]


def _modele_absent(nom: str) -> ErreurApp:
    return ErreurApp(
        "MODEL_NOT_AVAILABLE",
        f"Le modèle {nom} n'est pas installé sur le serveur.",
        code_http=503,
    )


# ===========================================================================
# ASR
# ===========================================================================

def _autoriser_codes_kiriku() -> None:
    """
    faster-whisper refuse les codes de langue absents de la liste officielle
    de Whisper. M-Kiriku-ASR a ajouté ses propres jetons (ex. <|pu|>) :
    on ajoute donc nos codes à la liste acceptée.
    """
    import faster_whisper.tokenizer as tokenizer_fw

    manquants = sorted(set(LANGUES_ASR.values()) - set(tokenizer_fw._LANGUAGE_CODES))
    if manquants:
        tokenizer_fw._LANGUAGE_CODES = tuple(tokenizer_fw._LANGUAGE_CODES) + tuple(manquants)


def _charger_asr():
    dossier = reglages.dossier_asr
    if not (dossier / "model.bin").is_file():
        raise _modele_absent("ASR")

    from faster_whisper import WhisperModel

    _autoriser_codes_kiriku()
    journal.info("Chargement du modèle ASR depuis %s ...", dossier)
    modele = WhisperModel(
        str(dossier),
        device=reglages.appareil,
        compute_type=reglages.asr_type_calcul,
        cpu_threads=reglages.nombre_threads,
        local_files_only=True,
    )

    for langue, code in LANGUES_ASR.items():
        if modele.hf_tokenizer.token_to_id(f"<|{code}|>") is None:
            journal.warning("Le jeton <|%s|> (%s) est absent du tokenizer ASR.", code, langue)
    return modele


def transcrire_audio(echantillons, langue: str) -> str:
    """Transforme l'audio (mono, 16 kHz) en texte."""
    code_langue = verifier_langue_asr(langue)
    modele = _obtenir("asr", _charger_asr)

    code_whisper = LANGUES_ASR[code_langue]
    if modele.hf_tokenizer.token_to_id(f"<|{code_whisper}|>") is None:
        raise ErreurApp(
            "LANGUAGE_NOT_AVAILABLE",
            f"Le modèle ASR ne reconnaît pas le code de langue '{code_whisper}'.",
        )

    try:
        segments, _ = modele.transcribe(
            np.asarray(echantillons, dtype=np.float32),
            language=code_whisper,
            task="transcribe",
            beam_size=reglages.asr_beam_size,
            condition_on_previous_text=False,
        )
        # `segments` est un générateur : la transcription a lieu ici.
        texte = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception:
        journal.exception("Échec de la transcription (%s)", code_langue)
        raise ErreurApp("ASR_FAILED", "La transcription de l'audio a échoué.", code_http=500)

    if not texte:
        raise ErreurApp("SPEECH_NOT_RECOGNIZED", "Aucune parole n'a été reconnue dans l'audio.")
    return texte


# ===========================================================================
# TTS
# ===========================================================================

def _charger_tts(langue: str):
    dossier = reglages.dossier_tts(langue)
    chemin_config = dossier / "config.json"
    chemins_modele = sorted(dossier.glob("*.pth"))
    if not chemin_config.is_file() or not chemins_modele:
        raise _modele_absent(f"TTS {langue}")

    import torch
    from TTS.api import TTS

    if reglages.nombre_threads > 0:
        torch.set_num_threads(reglages.nombre_threads)

    journal.info("Chargement du modèle TTS %s depuis %s ...", langue, dossier)
    synthetiseur = TTS(
        model_path=str(chemins_modele[0]),
        config_path=str(chemin_config),
        progress_bar=False,
    )
    return synthetiseur.to(reglages.appareil)


def synthetiser_texte(texte: str, langue: str):
    """Transforme le texte en audio. Retourne (echantillons, frequence)."""
    code_langue = verifier_langue_tts(langue)

    texte = (texte or "").strip()
    if not texte:
        raise ErreurApp("EMPTY_TEXT", "Le texte à synthétiser est vide.")
    if len(texte) > reglages.longueur_max_texte:
        raise ErreurApp(
            "TEXT_TOO_LONG",
            f"Le texte dépasse la longueur maximale de {reglages.longueur_max_texte} caractères.",
        )

    synthetiseur = _obtenir(f"tts:{code_langue}", lambda: _charger_tts(code_langue))

    try:
        with _verrou_tts:
            # split_sentences : les textes longs sont lus phrase par phrase.
            echantillons = synthetiseur.tts(texte, split_sentences=True)
        frequence = synthetiseur.synthesizer.output_sample_rate
    except Exception:
        journal.exception("Échec de la synthèse vocale (%s)", code_langue)
        raise ErreurApp("TTS_FAILED", "La synthèse vocale a échoué.", code_http=500)

    return np.asarray(echantillons, dtype=np.float32), frequence


# ===========================================================================
# Démarrage / état
# ===========================================================================

def precharger_modeles() -> None:
    """
    Charge tous les modèles au démarrage, pour que la première requête
    ne soit pas lente. Un modèle absent n'empêche pas le service de démarrer :
    les requêtes qui en ont besoin recevront MODEL_NOT_AVAILABLE (503).
    """
    a_charger = [("asr", _charger_asr)] + [
        (f"tts:{langue}", lambda langue=langue: _charger_tts(langue)) for langue in MODELES_TTS
    ]
    for cle, chargeur in a_charger:
        try:
            _obtenir(cle, chargeur)
        except ErreurApp as erreur:
            journal.error("Modèle %s non chargé : %s", cle, erreur.message)
        except Exception:
            # Erreur inattendue (dépendance manquante...) : trace complète dans les logs.
            journal.exception("Modèle %s non chargé", cle)


def etat_modeles() -> dict:
    """Indique quels modèles sont chargés en mémoire."""
    cles = ["asr"] + [f"tts:{langue}" for langue in MODELES_TTS]
    return {cle: cle in _modeles for cle in cles}
