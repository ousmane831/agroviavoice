from fastapi import APIRouter

from app.core.config import reglages
from app.models.schemas import EtatModeles, ReponseSante
from app.services.model_loader import etat_modeles

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ReponseSante)
def verifier_sante():
    """Vérifie que le service répond."""
    return ReponseSante(status="ok", service=reglages.nom_service)


@router.get("/health/models", response_model=EtatModeles)
def verifier_modeles():
    """Indique quels modèles IA sont chargés en mémoire."""
    modeles = etat_modeles()
    return EtatModeles(status="ok" if all(modeles.values()) else "degraded", models=modeles)
