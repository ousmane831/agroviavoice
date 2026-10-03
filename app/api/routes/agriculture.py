from fastapi import APIRouter, File, Form, UploadFile

from app.core.languages import verifier_langue_asr, verifier_langue_tts
from app.models.schemas import ReponseQuestion
from app.services.agriculture_service import trouver_conseil
from app.services.audio_service import preparer_audio_pour_asr, sauvegarder_audio_reponse
from app.services.model_loader import synthetiser_texte, transcrire_audio

router = APIRouter(tags=["Agriculture"])


# Les noms "audio" et "language" sont ceux envoyés par Django : ne pas les changer.
@router.post("/agriculture/ask", response_model=ReponseQuestion)
def poser_question(audio: UploadFile = File(...), language: str = Form(...)):
    """Question vocale -> texte -> conseil agricole -> réponse vocale."""
    # 1. Vérifier que la langue a un modèle ASR et un modèle TTS
    langue = verifier_langue_asr(language)
    verifier_langue_tts(langue)

    # 2. Préparer l'audio reçu (conversion en WAV 16 kHz)
    echantillons = preparer_audio_pour_asr(audio.filename, audio.file.read())

    # 3. Audio -> texte
    question = transcrire_audio(echantillons, langue)

    # 4. Texte -> conseil agricole
    reponse = trouver_conseil(question, langue)

    # 5. Conseil -> audio
    audio_reponse, frequence = synthetiser_texte(reponse, langue)
    nom_fichier = sauvegarder_audio_reponse(audio_reponse, frequence)

    return ReponseQuestion(question=question, answer=reponse, audio_url=f"/audio/{nom_fichier}")
