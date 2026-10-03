import sys
from unittest.mock import MagicMock

import numpy as np
import pytest
import soundfile as sf

# Les gros paquets IA (transformers, TTS...) ne sont pas nécessaires pour les tests :
# s'ils ne sont pas installés, on les remplace par des faux.
for nom_paquet in ["transformers", "TTS", "TTS.api", "huggingface_hub"]:
    try:
        __import__(nom_paquet)
    except ImportError:
        sys.modules[nom_paquet] = MagicMock()

from app.core.config import reglages


@pytest.fixture(autouse=True)
def dossiers_audio_temporaires(tmp_path, monkeypatch):
    """Chaque test écrit ses fichiers audio dans un dossier temporaire."""
    monkeypatch.setattr(reglages, "dossier_audio_entree", tmp_path / "input")
    monkeypatch.setattr(reglages, "dossier_audio_sortie", tmp_path / "output")


def creer_wav(tmp_path, secondes=1.0, frequence=44100, volume=0.5) -> bytes:
    """Crée un petit WAV (un son "la" à 440 Hz) et retourne son contenu."""
    temps = np.linspace(0, secondes, int(frequence * secondes), endpoint=False)
    chemin = tmp_path / "exemple.wav"
    sf.write(chemin, volume * np.sin(2 * np.pi * 440 * temps), frequence)
    return chemin.read_bytes()
