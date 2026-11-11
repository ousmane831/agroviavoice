import json

import pytest
from fastapi.testclient import TestClient

from app.api.routes import agriculture
from app.main import app
from app.services.agriculture_service import trouver_conseil
from tests.conftest import creer_wav

client = TestClient(app)


@pytest.fixture
def faux_modeles(monkeypatch):
    """Remplace les vrais modèles par des faux : rien n'est chargé."""
    monkeypatch.setattr(agriculture, "transcrire_audio", lambda echantillons, langue: "ji gerte")
    monkeypatch.setattr(agriculture, "synthetiser_texte", lambda texte, langue: ([0.0, 0.1, -0.1], 16000))


# --- Service de conseils -----------------------------------------------------

def test_conseil_trouve_par_mot_cle():
    assert "gerte" in trouver_conseil("Kañ laa wara ji gerte?", "wolof")


def test_reponse_par_defaut():
    assert trouver_conseil("bonjour", "pulaar").startswith("A jaaraama")


def test_vente_lue_dans_le_contexte():
    contexte = {"ventes": {"vendu_total_kg": 10474.0}}
    reponse = trouver_conseil("ñaata kilogramme laay jaay", "wolof", contexte)
    assert reponse == "Ci sa parcelle, 10474 kilogrammes nga jaay."


def test_resume_pulaar_sans_valeurs_manquantes():
    contexte = {"parcelle": {"id": 3, "culture": "mil"}, "sol": {"humidite_pct": None}}
    reponse = trouver_conseil("parcelle", "pulaar", contexte)
    assert "mil" in reponse
    assert "None" not in reponse


@pytest.mark.parametrize("contexte", [{"parcelle": None, "ventes": None}, {"ventes": "abc"}, {}])
def test_contexte_mal_forme_ne_plante_pas(contexte):
    assert "gerte" in trouver_conseil("ji gerte", "wolof", contexte)


# --- Routes ------------------------------------------------------------------

def test_poser_question(tmp_path, faux_modeles):
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


def test_repondre_avec_contexte(faux_modeles):
    reponse = client.post(
        "/api/v1/agriculture/respond",
        data={
            "question": "ñaata kilogramme laay jaay",
            "language": "wolof",
            "agricultural_context": json.dumps({"ventes": {"vendu_total_kg": 250.0}}),
        },
    )
    assert reponse.status_code == 200
    assert reponse.json()["answer"] == "Ci sa parcelle, 250 kilogrammes nga jaay."


@pytest.mark.parametrize("contexte", ["pas du json", "[1, 2]", "null"])
def test_repondre_contexte_invalide_ignore(faux_modeles, contexte):
    reponse = client.post(
        "/api/v1/agriculture/respond",
        data={"question": "ji gerte", "language": "wolof", "agricultural_context": contexte},
    )
    assert reponse.status_code == 200


def test_transcrire(tmp_path, faux_modeles):
    reponse = client.post(
        "/api/v1/agriculture/transcribe",
        files={"audio": ("question.wav", creer_wav(tmp_path), "audio/wav")},
        data={"language": "serere"},
    )
    assert reponse.status_code == 200
    assert reponse.json() == {"question": "ji gerte", "language": "serere"}


def test_synthetiser(faux_modeles):
    reponse = client.post("/api/v1/agriculture/synthesize", data={"text": "Jërëjëf", "language": "pulaar"})
    assert reponse.status_code == 200
    assert reponse.json()["audio_url"].startswith("/audio/reponse_")


def test_synthetiser_texte_vide_format_erreur_standard():
    # Pas de faux modèle : le texte vide est refusé avant tout chargement.
    reponse = client.post("/api/v1/agriculture/synthesize", data={"text": "   ", "language": "wolof"})
    assert reponse.status_code == 400
    assert reponse.json() == {"success": False, "error": "EMPTY_TEXT", "message": "Le texte à synthétiser est vide."}


def test_langue_non_disponible_en_tts(tmp_path):
    reponse = client.post(
        "/api/v1/agriculture/ask",
        files={"audio": ("question.wav", creer_wav(tmp_path), "audio/wav")},
        data={"language": "serere"},
    )
    assert reponse.status_code == 400
    assert reponse.json()["error"] == "LANGUAGE_NOT_AVAILABLE"


def test_modele_absent_renvoie_503():
    # Le dossier des modèles (temporaire) est vide.
    reponse = client.post("/api/v1/agriculture/synthesize", data={"text": "Jërëjëf", "language": "wolof"})
    assert reponse.status_code == 503
    assert reponse.json()["error"] == "MODEL_NOT_AVAILABLE"
