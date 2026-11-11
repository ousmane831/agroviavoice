"""
Vérifie la base de conseils (app/data/conseils.json) après une modification.

Utilisation (depuis la racine du projet) :
  python -m scripts.verifier_conseils
  python -m scripts.verifier_conseils --tester "ñaata kilogramme laay jaay" wolof

Affiche :
  - les erreurs de format (le service refuserait de démarrer) ;
  - pour chaque langue, les sujets couverts et ceux qui manquent ;
  - les mots-clés présents dans plusieurs sujets (source d'ambiguïté) ;
  - les conseils pas encore validés et les notes à traiter.
Avec --tester : montre quel sujet est choisi pour une question, et pourquoi.
"""

import argparse
import sys
from collections import defaultdict

from pydantic import ValidationError

from app.core.config import NOMS_LANGUES, MODELES_TTS
from app.services.agriculture_service import (
    analyser_question,
    charger_base,
    lire_base,
    mots_cles_trouves,
    normaliser_texte,
    score,
)


def verifier() -> int:
    try:
        base = lire_base()
    except ValidationError as erreur:
        print("ERREUR : conseils.json est mal formé. Le service ne démarrera pas.\n")
        print(erreur)
        return 1
    except ValueError as erreur:
        print(f"ERREUR : conseils.json n'est pas un JSON valide : {erreur}")
        return 1

    print(f"OK : {len(base.sujets)} sujets.\n")

    # Couverture par langue (langues ayant une voix TTS = langues de réponse)
    print("Couverture par langue :")
    for langue in MODELES_TTS:
        couverts = [s.id for s in base.sujets if langue in s.conseils]
        manquants = [s.id for s in base.sujets if langue not in s.conseils]
        print(f"  {NOMS_LANGUES[langue]:7} {len(couverts)}/{len(base.sujets)} sujets"
              + (f"   manquants : {', '.join(manquants)}" if manquants else ""))
        if langue not in base.reponses_par_defaut:
            print(f"  ATTENTION : pas de réponse par défaut en {langue}")

    # Mots-clés en double
    usages = defaultdict(set)
    for sujet in base.sujets:
        for liste in sujet.mots_cles.values():
            for mot in liste:
                usages[normaliser_texte(mot.rstrip("*"))].add(sujet.id)
    doublons = {mot: ids for mot, ids in usages.items() if len(ids) > 1}
    if doublons:
        print("\nMots-clés présents dans plusieurs sujets (le premier sujet de la liste gagne) :")
        for mot, ids in sorted(doublons.items()):
            print(f"  {mot!r} : {', '.join(sorted(ids))}")

    # Validation
    non_valides = [s.id for s in base.sujets if not s.valide]
    print(f"\nConseils validés : {len(base.sujets) - len(non_valides)}/{len(base.sujets)}")
    sans_source = [s.id for s in base.sujets if not s.source]
    if sans_source:
        print(f"Sans source : {', '.join(sans_source)}")

    notes = [(s.id, s.note) for s in base.sujets if s.note]
    if notes:
        print("\nNotes à traiter :")
        for identifiant, note in notes:
            print(f"  [{identifiant}] {note}")
    return 0


def tester(question: str, langue: str) -> None:
    base = charger_base()
    question_normalisee = normaliser_texte(question)
    print(f"Question normalisée : {question_normalisee!r}\n")
    for sujet in base.sujets:
        if langue not in sujet.conseils:
            continue
        trouves = mots_cles_trouves(sujet.mots_cles[langue], question_normalisee)
        if trouves:
            points = score(sujet.mots_cles[langue], question_normalisee)
            print(f"  {sujet.id:12} score {points}  ({', '.join(trouves)})")
    sujet, reponse = analyser_question(question, langue)
    print(f"\nSujet choisi : {sujet or 'aucun (réponse par défaut)'}")
    print(f"Réponse : {reponse}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tester", nargs=2, metavar=("QUESTION", "LANGUE"))
    options = parser.parse_args()

    code = verifier()
    if code == 0 and options.tester:
        print("\n" + "=" * 60)
        tester(*options.tester)
    sys.exit(code)


if __name__ == "__main__":
    main()
