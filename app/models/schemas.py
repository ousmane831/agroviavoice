"""
Schémas des réponses renvoyées par l'API.

Les noms des champs (status, question, answer, audio_url...) sont lus
par Django : ne pas les traduire.
"""

from pydantic import BaseModel


class ReponseSante(BaseModel):
    """Réponse de GET /health."""

    status: str
    service: str


class ReponseQuestion(BaseModel):
    """Réponse de POST /agriculture/ask."""

    question: str   # texte transcrit de la question vocale
    answer: str     # conseil agricole dans la langue de l'agriculteur
    audio_url: str  # lien vers la réponse vocale, ex. /audio/reponse_xxx.wav
