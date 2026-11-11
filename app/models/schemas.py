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


class EtatModeles(BaseModel):
    """Réponse de GET /health/models."""

    status: str           # "ok" si tous les modèles sont chargés, sinon "degraded"
    models: dict[str, bool]


class ReponseTranscription(BaseModel):
    """Réponse de POST /agriculture/transcribe."""

    question: str
    language: str


class ReponseQuestion(BaseModel):
    """Réponse de POST /agriculture/ask et /agriculture/respond."""

    question: str   # texte de la question (transcrit ou envoyé)
    answer: str     # conseil agricole dans la langue de l'agriculteur
    audio_url: str  # lien vers la réponse vocale, ex. /audio/reponse_xxx.wav


class ReponseSynthese(BaseModel):
    """Réponse de POST /agriculture/synthesize."""

    text: str
    language: str
    audio_url: str
