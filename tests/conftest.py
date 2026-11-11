import numpy as np
import pytest
import soundfile as sf

from app.core.config import reglages

# Les tests ne chargent jamais les vrais modèles (plusieurs Go) :
# ils remplacent transcrire_audio / synthetiser_texte par des faux.
reglages.precharger_modeles = False


@pytest.fixture(autouse=True)
def dossiers_temporaires(tmp_path, monkeypatch):
    """Chaque test écrit ses fichiers audio (et cherche ses modèles) dans un dossier temporaire."""
    monkeypatch.setattr(reglages, "dossier_audio_entree", tmp_path / "input")
    monkeypatch.setattr(reglages, "dossier_audio_sortie", tmp_path / "output")
    monkeypatch.setattr(reglages, "dossier_modeles", tmp_path / "models")
    monkeypatch.setattr(reglages, "chemin_journal_questions", tmp_path / "logs" / "questions.jsonl")


def creer_wav(tmp_path, secondes=1.0, frequence=44100, volume=0.5) -> bytes:
    """Crée un petit WAV (un son "la" à 440 Hz) et retourne son contenu."""
    temps = np.linspace(0, secondes, int(frequence * secondes), endpoint=False)
    chemin = tmp_path / "exemple.wav"
    sf.write(chemin, volume * np.sin(2 * np.pi * 440 * temps), frequence)
    return chemin.read_bytes()
