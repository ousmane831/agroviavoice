import json

import pytest

from app.core.config import reglages
from app.services import agriculture_service
from app.services.agriculture_service import (
    analyser_question,
    lire_base,
    normaliser_texte,
    recharger_base,
    trouver_conseil,
)


@pytest.fixture
def base_temporaire(tmp_path, monkeypatch):
    """Permet d'écrire une fausse base de conseils pour un test."""
    def ecrire(contenu: dict):
        chemin = tmp_path / "conseils.json"
        chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(reglages, "chemin_conseils", chemin)
        return chemin
    yield ecrire
    monkeypatch.undo()
    recharger_base()


BASE_MINIMALE = {
    "sujets": [],
    "reponses_par_defaut": {"wolof": "défaut"},
    "donnees_parcelle": {"mots_cles": {}, "reponses": {}},
}


# --- La vraie base -----------------------------------------------------------

def test_vraie_base_valide():
    base = lire_base()
    assert len(base.sujets) > 0
    assert {"wolof", "pulaar"} <= set(base.reponses_par_defaut)


# --- Normalisation et détection ----------------------------------------------

def test_normalisation():
    assert normaliser_texte("  Récolté, l'Arachide ?! ") == "recolte l arachide"
    assert normaliser_texte("Ɓeydude ŋ") == "ɓeydude ŋ"  # lettres pulaar conservées


@pytest.mark.parametrize("question, sujet_attendu", [
    ("Kañ laa wara ji gerte?", "arachide"),
    ("Quand semer l'arachide", "arachide"),
    ("Naka laa wara def ak phosphore", "engrais"),   # "ph" ne doit plus être trouvé dans "phosphore"
    ("le pH de mon sol", "sol"),
    ("dugub bi", "mil"),
    ("famille", None),                               # "mil" ne doit pas être trouvé dans "famille"
    ("RÉCOLTER mes tomates", "legumes"),             # 1 mot légumes, 1 mot récolte : égalité -> le premier (legumes)
    ("taw bi", "meteo"),
    ("ndox ak wisal ak taw", "eau"),                 # 2 mots eau contre 1 météo
])
def test_detection_du_sujet_wolof(question, sujet_attendu):
    sujet, _ = analyser_question(question, "wolof")
    assert sujet == sujet_attendu


def test_le_sujet_avec_le_plus_de_mots_cles_gagne(base_temporaire):
    base_temporaire({**BASE_MINIMALE, "sujets": [
        {"id": "a", "mots_cles": {"commun": ["eau"]}, "conseils": {"wolof": "A"}},
        {"id": "b", "mots_cles": {"commun": ["eau", "pluie*"]}, "conseils": {"wolof": "B"}},
    ]})
    recharger_base()
    assert analyser_question("eau de pluie", "wolof") == ("b", "B")
    assert analyser_question("eau", "wolof") == ("a", "A")  # égalité : le premier


def test_sujet_sans_conseil_dans_la_langue_ignore(base_temporaire):
    base_temporaire({**BASE_MINIMALE, "reponses_par_defaut": {"pulaar": "défaut pulaar"}, "sujets": [
        {"id": "engrais", "mots_cles": {"commun": ["engrais"]}, "conseils": {"wolof": "W"}},
    ]})
    recharger_base()
    assert analyser_question("engrais", "pulaar") == (None, "défaut pulaar")


# --- Validation du fichier ---------------------------------------------------

def test_id_en_double_refuse(base_temporaire):
    sujet = {"id": "x", "mots_cles": {}, "conseils": {}}
    base_temporaire({**BASE_MINIMALE, "sujets": [sujet, sujet]})
    with pytest.raises(ValueError, match="double"):
        lire_base()


def test_valeur_inconnue_dans_une_phrase_refusee(base_temporaire):
    base_temporaire({**BASE_MINIMALE, "donnees_parcelle": {
        "mots_cles": {"vente": ["jaay*"]},
        "reponses": {"vente": {"wolof": "{vendus} kg"}},
    }})
    with pytest.raises(ValueError, match="vendus"):
        lire_base()


# --- Données de la parcelle --------------------------------------------------

def test_vente_ignoree_si_valeur_absente():
    sujet, _ = analyser_question("ñaata laay jaay", "wolof", {"ventes": {"vendu_total_kg": None}})
    assert sujet != "parcelle:vente"


def test_vente_avec_valeur():
    assert analyser_question("ñaata laay jaay", "wolof", {"ventes": {"vendu_total_kg": 12.0}}) == (
        "parcelle:vente", "Ci sa parcelle, 12 kilogrammes nga jaay.")


# --- Journal -----------------------------------------------------------------

def test_questions_journalisees():
    trouver_conseil("ji gerte", "wolof")
    trouver_conseil("bonjour", "pulaar")
    lignes = [json.loads(l) for l in reglages.chemin_journal_questions.read_text(encoding="utf-8").splitlines()]
    assert [(l["question"], l["sujet"]) for l in lignes] == [("ji gerte", "arachide"), ("bonjour", None)]


def test_journal_desactivable(monkeypatch):
    monkeypatch.setattr(reglages, "journaliser_questions", False)
    trouver_conseil("ji gerte", "wolof")
    assert not reglages.chemin_journal_questions.exists()


def test_erreur_de_journal_ne_bloque_pas(monkeypatch, tmp_path):
    (tmp_path / "fichier").write_text("x")
    monkeypatch.setattr(reglages, "chemin_journal_questions", tmp_path / "fichier" / "impossible.jsonl")
    assert "gerte" in trouver_conseil("ji gerte", "wolof")
