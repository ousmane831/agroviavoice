"""
Service de conseils agricoles.

Les textes (conseils, mots-clés, réponses par défaut...) sont dans
app/data/conseils.json : ils se modifient sans toucher à ce fichier.

Étapes pour répondre à une question :
1. Si Django a envoyé les données de la parcelle et que la question les concerne
   (ventes, récolte...), répondre avec ces données.
2. Sinon, chercher le sujet de la question par mots-clés (mots entiers, sans
   accents) : le sujet qui reconnaît le plus de mots de la question gagne.
3. Sinon, réponse par défaut.

Chaque question est notée dans le journal des questions (logs/questions.jsonl)
pour repérer celles qui restent sans réponse.
"""

import json
import logging
import re
import string
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from pydantic import BaseModel, model_validator

from app.core.config import reglages

journal = logging.getLogger(__name__)


# ============================================================
# FORMAT DE LA BASE DE CONSEILS (validé au chargement)
# ============================================================

class Sujet(BaseModel):
    id: str
    mots_cles: dict[str, list[str]]  # langue (ou "commun") -> mots-clés
    conseils: dict[str, str]          # langue -> conseil
    source: str = ""
    valide: bool = False
    note: str = ""


class DonneesParcelle(BaseModel):
    mots_cles: dict[str, list[str]]          # type de question -> mots-clés
    reponses: dict[str, dict[str, str]]      # type de question -> langue -> modèle de phrase
    resume: dict[str, dict[str, str]] = {}   # langue -> information -> modèle de phrase


# Valeurs utilisables dans les phrases de "donnees_parcelle" : {vendu}, {culture}...
VALEURS_PARCELLE = ("id", "culture", "type_sol", "humidite", "rendement", "vendu", "invendu", "recolte")


def champs_du_modele(modele: str) -> list[str]:
    """'{vendu} kg sur {id}' -> ['vendu', 'id']"""
    return [champ for _, champ, _, _ in string.Formatter().parse(modele) if champ]


class BaseConseils(BaseModel):
    sujets: list[Sujet]
    reponses_par_defaut: dict[str, str]
    donnees_parcelle: DonneesParcelle

    @model_validator(mode="after")
    def verifier_ids_uniques(self):
        ids = [sujet.id for sujet in self.sujets]
        doublons = {i for i in ids if ids.count(i) > 1}
        if doublons:
            raise ValueError(f"identifiants de sujet en double : {sorted(doublons)}")

        modeles = [m for par_langue in self.donnees_parcelle.reponses.values() for m in par_langue.values()]
        modeles += [m for par_info in self.donnees_parcelle.resume.values() for m in par_info.values()]
        for modele in modeles:
            inconnus = set(champs_du_modele(modele)) - set(VALEURS_PARCELLE)
            if inconnus:
                raise ValueError(
                    f"valeur inconnue {sorted(inconnus)} dans la phrase {modele!r} "
                    f"(valeurs possibles : {', '.join(VALEURS_PARCELLE)})"
                )
        return self


# ============================================================
# NORMALISATION ET MOTS-CLES
# ============================================================

def normaliser_texte(texte: str) -> str:
    """
    Minuscules, sans accents, sans ponctuation, espaces uniques.
    "Récolté, l'Arachide ?" -> "recolte l arachide"
    Les lettres propres au pulaar/wolof (ɓ, ɗ, ƴ, ŋ) sont conservées.
    """
    texte = unicodedata.normalize("NFD", texte.lower())
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = re.sub(r"[^\w\s]", " ", texte)
    return " ".join(texte.split())


@dataclass(frozen=True)
class MotCle:
    texte: str
    motif: re.Pattern


def compiler_mot_cle(mot_cle: str) -> MotCle:
    """'recolt*' -> mot commençant par 'recolt' ; 'mil' -> le mot 'mil' exactement."""
    prefixe = mot_cle.endswith("*")
    texte = normaliser_texte(mot_cle.rstrip("*"))
    motif = r"(?<!\S)" + re.escape(texte) + ("" if prefixe else r"(?!\S)")
    return MotCle(texte=mot_cle, motif=re.compile(motif))


def mots_cles_trouves(mots_cles: list[MotCle], question_normalisee: str) -> list[str]:
    return [mc.texte for mc in mots_cles if mc.motif.search(question_normalisee)]


def score(mots_cles: list[MotCle], question_normalisee: str) -> int:
    """
    Nombre de mots de la question reconnus par ces mots-clés.
    Un même mot n'est compté qu'une fois ("semer" trouvé par "semer" ET "seme*" = 1).
    """
    positions = {
        trouve.start()
        for mc in mots_cles
        for trouve in mc.motif.finditer(question_normalisee)
    }
    return len(positions)


# ============================================================
# CHARGEMENT DE LA BASE
# ============================================================

@dataclass(frozen=True)
class SujetCompile:
    id: str
    mots_cles: dict[str, list[MotCle]]  # langue -> mots-clés (langue + commun)
    conseils: dict[str, str]


@dataclass(frozen=True)
class BaseCompilee:
    sujets: list[SujetCompile]
    reponses_par_defaut: dict[str, str]
    donnees_parcelle: DonneesParcelle
    mots_cles_parcelle: dict[str, list[MotCle]]


def lire_base(chemin=None) -> BaseConseils:
    """Lit et valide le fichier JSON (lève une erreur claire s'il est mal formé)."""
    chemin = chemin or reglages.chemin_conseils
    return BaseConseils.model_validate_json(chemin.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def charger_base() -> BaseCompilee:
    base = lire_base()
    sujets = []
    for sujet in base.sujets:
        communs = sujet.mots_cles.get("commun", [])
        par_langue = {
            langue: [compiler_mot_cle(m) for m in sujet.mots_cles.get(langue, []) + communs]
            for langue in sujet.conseils
        }
        sujets.append(SujetCompile(id=sujet.id, mots_cles=par_langue, conseils=sujet.conseils))

    mots_cles_parcelle = {
        type_question: [compiler_mot_cle(m) for m in mots]
        for type_question, mots in base.donnees_parcelle.mots_cles.items()
    }
    journal.info("Base de conseils chargée : %d sujets.", len(sujets))
    return BaseCompilee(sujets, base.reponses_par_defaut, base.donnees_parcelle, mots_cles_parcelle)


def recharger_base() -> BaseCompilee:
    """Relit conseils.json (après une modification, sans redémarrer)."""
    charger_base.cache_clear()
    return charger_base()


# ============================================================
# REPONSES BASEES SUR LES DONNEES DE LA PARCELLE
# ============================================================

def _section(contexte: dict, cle: str) -> dict:
    """Retourne une section du contexte, ou {} si elle est absente ou mal formée."""
    valeur = contexte.get(cle)
    return valeur if isinstance(valeur, dict) else {}


def _nombre(valeur):
    """10474.0 -> 10474 (plus naturel à l'oral)."""
    if isinstance(valeur, float) and valeur.is_integer():
        return int(valeur)
    return valeur


def _valeurs_parcelle(contexte: dict) -> dict:
    """Extrait les valeurs utiles du contexte envoyé par Django (None si absentes)."""
    parcelle = _section(contexte, "parcelle")
    sol = _section(contexte, "sol")
    production = _section(contexte, "production")
    ventes = _section(contexte, "ventes")
    return {
        "id": parcelle.get("id", ""),
        "culture": parcelle.get("culture"),
        "type_sol": parcelle.get("type_sol"),
        "humidite": _nombre(sol.get("humidite_pct")),
        "rendement": _nombre(production.get("rendement_moyen")),
        "vendu": _nombre(ventes.get("vendu_total_kg")),
        "invendu": _nombre(ventes.get("invendu_total_kg")),
        "recolte": _nombre(ventes.get("recolte_total_kg")),
    }


def _repondre_avec_contexte(question: str, langue: str, contexte: dict) -> tuple[str, str] | None:
    """Retourne (type_de_reponse, texte) ou None si la question ne concerne pas les données."""
    base = charger_base()
    donnees = base.donnees_parcelle
    valeurs = _valeurs_parcelle(contexte)

    def complet(modele: str) -> bool:
        """Toutes les valeurs dont la phrase a besoin sont connues."""
        return all(valeurs.get(champ) is not None for champ in champs_du_modele(modele))

    # Questions précises : ventes, récolte...
    for type_question, mots_cles in base.mots_cles_parcelle.items():
        modele = donnees.reponses.get(type_question, {}).get(langue)
        if modele and complet(modele) and mots_cles_trouves(mots_cles, question):
            return f"parcelle:{type_question}", modele.format(**valeurs)

    # Résumé général : seules les phrases dont les valeurs sont connues sont lues.
    modeles_resume = donnees.resume.get(langue)
    if modeles_resume and _section(contexte, "parcelle"):
        morceaux = [modele.format(**valeurs) for modele in modeles_resume.values() if complet(modele)]
        if morceaux:
            return "parcelle:resume", " ".join(morceaux)

    return None


# ============================================================
# RECHERCHE DU CONSEIL
# ============================================================

def analyser_question(question: str, langue: str, contexte: dict | None = None) -> tuple[str | None, str]:
    """
    Retourne (identifiant_du_sujet, reponse).
    L'identifiant vaut None quand aucun sujet n'a été reconnu (réponse par défaut).
    """
    base = charger_base()
    question_normalisee = normaliser_texte(question)

    # 1. Données de la parcelle
    if isinstance(contexte, dict):
        resultat = _repondre_avec_contexte(question_normalisee, langue, contexte)
        if resultat:
            return resultat

    # 2. Sujet ayant le plus de mots-clés trouvés (à égalité : le premier de la liste)
    meilleur, meilleur_score = None, 0
    for sujet in base.sujets:
        if langue not in sujet.conseils:
            continue
        points = score(sujet.mots_cles[langue], question_normalisee)
        if points > meilleur_score:
            meilleur, meilleur_score = sujet, points
    if meilleur:
        return meilleur.id, meilleur.conseils[langue]

    # 3. Réponse par défaut
    return None, base.reponses_par_defaut.get(
        langue, "Désolé, je ne peux pas encore répondre à cette question."
    )


def trouver_conseil(question: str, langue: str, contexte: dict | None = None) -> str:
    """Retourne le conseil agricole dans la langue demandée et note la question au journal."""
    sujet, reponse = analyser_question(question, langue, contexte)
    journal.debug("Question (%s) -> sujet %s", langue, sujet)
    journaliser_question(question, langue, sujet, avec_contexte=isinstance(contexte, dict))
    return reponse


# ============================================================
# JOURNAL DES QUESTIONS
# ============================================================

_verrou_journal = threading.Lock()


def journaliser_question(question: str, langue: str, sujet: str | None, avec_contexte: bool) -> None:
    """Ajoute une ligne au journal. Une erreur d'écriture ne bloque jamais la réponse."""
    if not reglages.journaliser_questions:
        return
    ligne = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "langue": langue,
        "question": question,
        "sujet": sujet,
        "contexte": avec_contexte,
    }
    try:
        chemin = reglages.chemin_journal_questions
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with _verrou_journal, chemin.open("a", encoding="utf-8") as fichier:
            fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    except OSError:
        journal.exception("Impossible d'écrire dans le journal des questions")
