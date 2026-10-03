from fastapi import APIRouter

from app.core.config import reglages
from app.models.schemas import ReponseSante

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ReponseSante)
def verifier_sante():
    """Vérifie que le service répond."""
    return ReponseSante(status="ok", service=reglages.nom_service)
