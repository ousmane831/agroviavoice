from fastapi import APIRouter, File, Form, UploadFile

from app.core.languages import verifier_langue_asr, verifier_langue_tts
from app.models.schemas import ReponseQuestion
from app.services.agriculture_service import trouver_conseil
from app.services.audio_service import preparer_audio_pour_asr, sauvegarder_audio_reponse
from app.services.model_loader import synthetiser_texte, transcrire_audio
import json
router = APIRouter(tags=["Agriculture"])

@router.post("/agriculture/transcribe")
def transcrire_question(
    audio: UploadFile = File(...),
    language: str = Form(...),
):
    """Audio -> texte uniquement avec KIRIKU ASR."""
    langue = verifier_langue_asr(language)

    echantillons = preparer_audio_pour_asr(
        audio.filename,
        audio.file.read(),
    )

    question = transcrire_audio(
        echantillons,
        langue,
    )

    return {
        "question": question,
        "language": langue,
    }


@router.post("/agriculture/respond", response_model=ReponseQuestion)
def repondre_question(
    question: str = Form(...),
    language: str = Form(...),
    agricultural_context: str = Form(None),
):
    """Texte + contexte agricole -> conseil -> réponse vocale."""

    # 1. Vérifier la langue pour le TTS
    langue = verifier_langue_asr(language)
    verifier_langue_tts(langue)

    # 2. Lire le contexte agricole
    contexte = None

    if agricultural_context:
        try:
            contexte = json.loads(agricultural_context)
        except json.JSONDecodeError:
            contexte = None

    # 3. Générer le conseil agricole
    reponse = trouver_conseil(
        question,
        langue,
        contexte,
    )

    # 4. Transformer la réponse en audio avec KIRIKU TTS
    audio_reponse, frequence = synthetiser_texte(
        reponse,
        langue,
    )

    nom_fichier = sauvegarder_audio_reponse(
        audio_reponse,
        frequence,
    )

    return ReponseQuestion(
        question=question,
        answer=reponse,
        audio_url=f"/audio/{nom_fichier}",
    )

# Les noms "audio" et "language" sont ceux envoyés par Django : ne pas les changer.
@router.post("/agriculture/ask", response_model=ReponseQuestion)
def poser_question(
    audio: UploadFile = File(...),
    language: str = Form(...),
    agricultural_context: str = Form(None),
):
    """Question vocale -> texte -> conseil agricole -> réponse vocale."""
    # 1. Vérifier que la langue a un modèle ASR et un modèle TTS
    langue = verifier_langue_asr(language)
    verifier_langue_tts(langue)

    # 2. Préparer l'audio reçu (conversion en WAV 16 kHz)
    echantillons = preparer_audio_pour_asr(audio.filename, audio.file.read())

    # 3. Audio -> texte
    question = transcrire_audio(echantillons, langue)

    # 4. Texte -> conseil agricole
    contexte = None

    if agricultural_context:
        try:
            contexte = json.loads(agricultural_context)
        except json.JSONDecodeError:
            contexte = None

    reponse = trouver_conseil(
        question,
        langue,
        contexte
    )

    # 5. Conseil -> audio
    audio_reponse, frequence = synthetiser_texte(reponse, langue)
    nom_fichier = sauvegarder_audio_reponse(audio_reponse, frequence)

    return ReponseQuestion(question=question, answer=reponse, audio_url=f"/audio/{nom_fichier}")


@router.post("/agriculture/synthesize")
def synthetiser_reponse(
    text: str = Form(...),
    language: str = Form(...),
):
    """Texte déjà formulé -> réponse vocale avec KIRIKU TTS."""

    # 1. Vérifier que la langue possède un modèle TTS
    langue = verifier_langue_asr(language)
    verifier_langue_tts(langue)

    # 2. Vérifier que le texte n'est pas vide
    if not text.strip():
        return {
            "error": "Le texte à synthétiser est vide."
        }

    # 3. Texte -> audio avec KIRIKU TTS
    audio_reponse, frequence = synthetiser_texte(
        text,
        langue,
    )

    # 4. Sauvegarder le fichier audio
    nom_fichier = sauvegarder_audio_reponse(
        audio_reponse,
        frequence,
    )

    return {
        "text": text,
        "language": langue,
        "audio_url": f"/audio/{nom_fichier}",
    }