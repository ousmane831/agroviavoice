import pytest

from app.core.errors import ErreurApp
from app.core.languages import normaliser_langue, verifier_langue_asr, verifier_langue_tts


def test_langue_normalisee():
    assert normaliser_langue("  Wolof ") == "wolof"


def test_langue_inconnue_refusee():
    with pytest.raises(ErreurApp) as erreur:
        normaliser_langue("anglais")
    assert erreur.value.code == "LANGUAGE_NOT_SUPPORTED"


@pytest.mark.parametrize("verifier", [verifier_langue_asr, verifier_langue_tts])
def test_serere_connu_mais_pas_disponible(verifier):
    with pytest.raises(ErreurApp) as erreur:
        verifier("serere")
    assert erreur.value.code == "LANGUAGE_NOT_AVAILABLE"
    assert erreur.value.message == "La langue Sérère n'est pas encore disponible."


@pytest.mark.parametrize("langue", ["wolof", "pulaar"])
def test_wolof_et_pulaar_disponibles(langue):
    assert verifier_langue_asr(langue) == langue
    assert verifier_langue_tts(langue) == langue
