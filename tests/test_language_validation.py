import pytest

from app.core.errors import ErreurApp
from app.core.languages import normaliser_langue, verifier_langue_asr, verifier_langue_tts


def test_langue_normalisee():
    assert normaliser_langue("  Wolof ") == "wolof"


def test_langue_inconnue_refusee():
    with pytest.raises(ErreurApp) as erreur:
        normaliser_langue("anglais")
    assert erreur.value.code == "LANGUAGE_NOT_SUPPORTED"


def test_serere_disponible_en_asr():
    # M-Kiriku-ASR transcrit aussi le sérère.
    assert verifier_langue_asr("serere") == "serere"


def test_serere_pas_disponible_en_tts():
    with pytest.raises(ErreurApp) as erreur:
        verifier_langue_tts("serere")
    assert erreur.value.code == "LANGUAGE_NOT_AVAILABLE"
    assert erreur.value.message == "La langue Sérère n'est pas encore disponible."


@pytest.mark.parametrize("langue", ["wolof", "pulaar"])
def test_wolof_et_pulaar_disponibles(langue):
    assert verifier_langue_asr(langue) == langue
    assert verifier_langue_tts(langue) == langue
