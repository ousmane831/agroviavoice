import subprocess

import pytest

from app.core.config import reglages
from app.core.errors import ErreurApp
from app.services import audio_service
from tests.conftest import creer_wav


def convertir_avec_ffmpeg(tmp_path, nom_sortie, *options):
    """Crée un fichier audio dans un autre format (mp3, webm...) à partir d'un WAV."""
    chemin_wav = tmp_path / "exemple.wav"
    chemin_wav.write_bytes(creer_wav(tmp_path))
    chemin_sortie = tmp_path / nom_sortie
    commande = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(chemin_wav), *options, str(chemin_sortie)]
    subprocess.run(commande, check=True)
    return chemin_sortie.read_bytes()


def test_wav_converti_en_16khz(tmp_path):
    echantillons = audio_service.preparer_audio_pour_asr("question.wav", creer_wav(tmp_path, secondes=2))
    assert len(echantillons) == 2 * audio_service.FREQUENCE_ASR


def test_mp3_accepte(tmp_path):
    contenu = convertir_avec_ffmpeg(tmp_path, "exemple.mp3")
    echantillons = audio_service.preparer_audio_pour_asr("question.mp3", contenu)
    assert len(echantillons) > 0


def test_webm_du_navigateur_accepte(tmp_path):
    contenu = convertir_avec_ffmpeg(tmp_path, "exemple.webm", "-c:a", "libopus")
    echantillons = audio_service.preparer_audio_pour_asr("question.webm", contenu)
    assert len(echantillons) > 0


def test_fichiers_temporaires_supprimes(tmp_path):
    audio_service.preparer_audio_pour_asr("question.wav", creer_wav(tmp_path))
    assert list(reglages.dossier_audio_entree.iterdir()) == []


@pytest.mark.parametrize(
    "nom_fichier, contenu, code_attendu",
    [
        ("question.txt", b"abc", "INVALID_AUDIO_FILE"),
        ("question.webm", b"pas un vrai webm", "INVALID_AUDIO_FILE"),
        ("question.wav", b"", "EMPTY_AUDIO"),
        ("question.wav", b"ceci n'est pas un audio", "INVALID_AUDIO_FILE"),
    ],
)
def test_fichiers_invalides_refuses(nom_fichier, contenu, code_attendu):
    with pytest.raises(ErreurApp) as erreur:
        audio_service.preparer_audio_pour_asr(nom_fichier, contenu)
    assert erreur.value.code == code_attendu


def test_silence_refuse(tmp_path):
    with pytest.raises(ErreurApp) as erreur:
        audio_service.preparer_audio_pour_asr("question.wav", creer_wav(tmp_path, volume=0))
    assert erreur.value.code == "EMPTY_AUDIO"


def test_audio_trop_long_refuse(tmp_path, monkeypatch):
    monkeypatch.setattr(reglages, "duree_max_audio_secondes", 1)
    with pytest.raises(ErreurApp) as erreur:
        audio_service.preparer_audio_pour_asr("question.wav", creer_wav(tmp_path, secondes=2))
    assert erreur.value.code == "AUDIO_TOO_LONG"


def test_fichier_trop_gros_refuse(monkeypatch):
    monkeypatch.setattr(reglages, "taille_max_audio_mo", 0)
    with pytest.raises(ErreurApp) as erreur:
        audio_service.verifier_fichier_audio("question.wav", b"x")
    assert erreur.value.code == "AUDIO_TOO_LARGE"


def test_audio_reponse_sauvegarde():
    nom_fichier = audio_service.sauvegarder_audio_reponse([0.0, 0.1, -0.1], frequence=22050)
    assert nom_fichier.startswith("reponse_") and nom_fichier.endswith(".wav")
    assert (reglages.dossier_audio_sortie / nom_fichier).exists()
