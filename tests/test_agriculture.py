from fastapi.testclient import TestClient

from app.api.routes import agriculture
from app.main import app
from app.services.agriculture_service import trouver_conseil
from tests.conftest import creer_wav

client = TestClient(app)


def test_conseil_trouve_par_mot_cle():
    assert "gerte" in trouver_conseil("Kañ laa wara ji gerte?", "wolof")


def test_reponse_par_defaut():
    assert trouver_conseil("bonjour", "pulaar").startswith("A jaaraama")


def test_poser_question(tmp_path, monkeypatch):
    # On remplace les vrais modèles par des faux : pas de téléchargement.
    monkeypatch.setattr(agriculture, "transcrire_audio", lambda echantillons, langue: "ji gerte")
    monkeypatch.setattr(agriculture, "synthetiser_texte", lambda texte, langue: ([0.0, 0.1, -0.1], 16000))

    reponse = client.post(
        "/api/v1/agriculture/ask",
        files={"audio": ("question.wav", creer_wav(tmp_path), "audio/wav")},
        data={"language": "wolof"},
    )

    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["question"] == "ji gerte"
    assert "gerte" in donnees["answer"]
    assert donnees["audio_url"].startswith("/audio/reponse_")


def test_langue_non_disponible(tmp_path):
    reponse = client.post(
        "/api/v1/agriculture/ask",
        files={"audio": ("question.wav", creer_wav(tmp_path), "audio/wav")},
        data={"language": "serere"},
    )
    assert reponse.status_code == 400
    assert reponse.json()["error"] == "LANGUAGE_NOT_AVAILABLE"
