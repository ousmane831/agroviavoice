import json
import logging

from fastapi import APIRouter, File, Form, UploadFile

from app.core.languages import verifier_langue_asr, verifier_langue_tts
from app.models.schemas import ReponseQuestion, ReponseSynthese, ReponseTranscription
from app.services.agriculture_service import trouver_conseil
from app.services.audio_service import preparer_audio_pour_asr, sauvegarder_audio_reponse
from app.services.model_loader import synthetiser_texte, transcrire_audio

journal = logging.getLogger(__name__)

router = APIRouter(tags=["Agriculture"])

# Les noms des champs ("audio", "language", "question", "agricultural_context"...)
# sont ceux envoyés par Django : ne pas les changer.


def lire_contexte(agricultural_context: str | None) -> dict | None:
    """Décode le contexte agricole JSON envoyé par Django (None s'il est absent ou invalide)."""
    if not agricultural_context:
        return None
    try:
        contexte = json.loads(agricultural_context)
    except json.JSONDecodeError:
        journal.warning("agricultural_context ignoré : JSON invalide.")
        return None
    if not isinstance(contexte, dict):
        journal.warning("agricultural_context ignoré : un objet JSON est attendu.")
        return None
    return contexte


def repondre_en_audio(question: str, langue: str, contexte: dict | None) -> ReponseQuestion:
    """Texte -> conseil agricole -> réponse vocale."""
    reponse = trouver_conseil(question, langue, contexte)
    audio_reponse, frequence = synthetiser_texte(reponse, langue)
    nom_fichier = sauvegarder_audio_reponse(audio_reponse, frequence)
    return ReponseQuestion(question=question, answer=reponse, audio_url=f"/audio/{nom_fichier}")


@router.post("/agriculture/transcribe", response_model=ReponseTranscription)
def transcrire_question(
    audio: UploadFile = File(...),
    language: str = Form(...),
):
    """Audio -> texte uniquement."""
    langue = verifier_langue_asr(language)
    echantillons = preparer_audio_pour_asr(audio.filename, audio.file.read())
    question = transcrire_audio(echantillons, langue)
    return ReponseTranscription(question=question, language=langue)


@router.post("/agriculture/respond", response_model=ReponseQuestion)
def repondre_question(
    question: str = Form(...),
    language: str = Form(...),
    agricultural_context: str = Form(None),
):
    """Question écrite + contexte agricole -> conseil -> réponse vocale."""
    langue = verifier_langue_tts(language)
    return repondre_en_audio(question, langue, lire_contexte(agricultural_context))


@router.post("/agriculture/ask", response_model=ReponseQuestion)
def poser_question(
    audio: UploadFile = File(...),
    language: str = Form(...),
    agricultural_context: str = Form(None),
):
    """Question vocale -> texte -> conseil agricole -> réponse vocale."""
    # 1. La langue doit avoir un modèle ASR ET un modèle TTS
    langue = verifier_langue_asr(language)
    verifier_langue_tts(langue)

    # 2. Audio -> texte
    echantillons = preparer_audio_pour_asr(audio.filename, audio.file.read())
    question = transcrire_audio(echantillons, langue)

    # 3. Texte -> conseil -> audio
    return repondre_en_audio(question, langue, lire_contexte(agricultural_context))


@router.post("/agriculture/synthesize", response_model=ReponseSynthese)
def synthetiser_reponse(
    text: str = Form(...),
    language: str = Form(...),
):
    """Texte déjà formulé -> réponse vocale."""
    langue = verifier_langue_tts(language)
    # synthetiser_texte refuse un texte vide ou trop long (format d'erreur standard).
    audio_reponse, frequence = synthetiser_texte(text, langue)
    nom_fichier = sauvegarder_audio_reponse(audio_reponse, frequence)
    return ReponseSynthese(text=text, language=langue, audio_url=f"/audio/{nom_fichier}")
