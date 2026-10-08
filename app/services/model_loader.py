"""
Communication avec l'API Kiriku distante.

Les modèles ASR et TTS ne sont plus téléchargés localement.
Ils tournent sur le GPU RTX 4090 du concours.

Interface conservée pour le reste de l'application :
- transcrire_audio(echantillons, langue)
- synthetiser_texte(texte, langue)
"""

import io
import wave

import numpy as np
from openai import OpenAI

from app.core.config import reglages
from app.core.languages import verifier_langue_asr, verifier_langue_tts


def obtenir_client_kiriku() -> OpenAI:
    """Crée le client OpenAI configuré pour l'API Kiriku."""
    if not reglages.kiriku_api_key:
        raise RuntimeError(
            "KIRIKU_API_KEY n'est pas configurée dans le fichier .env."
        )

    return OpenAI(
        api_key=reglages.kiriku_api_key,
        base_url=reglages.kiriku_api_url,
        timeout=120.0,
    )


def convertir_echantillons_en_wav(echantillons, frequence: int = 16000) -> bytes:
    """
    Convertit les échantillons audio numpy en fichier WAV en mémoire.

    L'API Kiriku ASR accepte les fichiers audio.
    """
    echantillons = np.asarray(echantillons, dtype=np.float32)

    # Limiter les valeurs dans l'intervalle audio standard.
    echantillons = np.clip(echantillons, -1.0, 1.0)

    # Conversion float32 -> PCM 16 bits.
    pcm = (echantillons * 32767).astype(np.int16)

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as fichier_wav:
        fichier_wav.setnchannels(1)
        fichier_wav.setsampwidth(2)
        fichier_wav.setframerate(frequence)
        fichier_wav.writeframes(pcm.tobytes())

    buffer.seek(0)
    return buffer.read()


def transcrire_audio(echantillons, langue: str) -> str:
    """
    Transforme l'audio en texte avec l'API Kiriku distante.

    Langues ASR :
    - wolof
    - pulaar
    - serer
    """
    code_langue = verifier_langue_asr(langue)

    audio_wav = convertir_echantillons_en_wav(
        echantillons,
        frequence=16000,
    )

    client = obtenir_client_kiriku()

    fichier_audio = io.BytesIO(audio_wav)
    fichier_audio.name = "audio.wav"

    resultat = client.audio.transcriptions.create(
        model="m-kiriku-asr",
        file=fichier_audio,
        language=code_langue,
        response_format="json",
    )

    return resultat.text.strip()


def synthetiser_texte(texte: str, langue: str):
    """
    Transforme le texte en audio WAV avec l'API Kiriku.

    L'API limite chaque requête TTS à 512 caractères.
    Si le texte est plus long, il est découpé en plusieurs morceaux,
    puis les audios sont concaténés.

    Langues TTS :
    - wolof
    - pulaar

    Retourne :
        (echantillons, frequence)
    """
    code_langue = verifier_langue_tts(langue)

    if not texte or not texte.strip():
        raise ValueError("Le texte à synthétiser est vide.")

    client = obtenir_client_kiriku()

    # Découpage en morceaux de maximum 512 caractères.
    morceaux = []

    texte_restant = texte.strip()

    while len(texte_restant) > 512:
        position = texte_restant.rfind(" ", 0, 512)

        if position <= 0:
            position = 512

        morceaux.append(texte_restant[:position].strip())
        texte_restant = texte_restant[position:].strip()

    if texte_restant:
        morceaux.append(texte_restant)

    tous_les_echantillons = []
    frequence = None

    for morceau in morceaux:
        resultat = client.audio.speech.create(
            model="kiriku-tts",
            voice=code_langue,
            input=morceau,
        )

        audio_wav = resultat.read()

        with wave.open(io.BytesIO(audio_wav), "rb") as fichier_wav:
            frequence_morceau = fichier_wav.getframerate()
            nombre_canaux = fichier_wav.getnchannels()
            largeur_echantillon = fichier_wav.getsampwidth()
            frames = fichier_wav.readframes(fichier_wav.getnframes())

        if largeur_echantillon == 2:
            echantillons = (
                np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            )
            echantillons /= 32768.0

        elif largeur_echantillon == 1:
            echantillons = (
                np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
            )
            echantillons = (echantillons - 128) / 128.0

        else:
            raise ValueError(
                f"Format WAV TTS non supporté : "
                f"{largeur_echantillon} octets par échantillon."
            )

        if nombre_canaux > 1:
            echantillons = echantillons.reshape(
                -1,
                nombre_canaux,
            ).mean(axis=1)

        if frequence is None:
            frequence = frequence_morceau
        elif frequence != frequence_morceau:
            raise ValueError(
                "Les morceaux audio ont des fréquences différentes."
            )

        tous_les_echantillons.append(echantillons)

    echantillons_finaux = np.concatenate(tous_les_echantillons)

    return echantillons_finaux, frequence