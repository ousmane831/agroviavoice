"""
Analyse le journal des questions (logs/questions.jsonl).

Utilisation (depuis la racine du projet) :
  python -m scripts.questions_sans_reponse            # résumé + 30 dernières questions sans réponse
  python -m scripts.questions_sans_reponse --tout     # toutes les questions sans réponse
  python -m scripts.questions_sans_reponse --jours 7  # seulement les 7 derniers jours

Sert à décider quels conseils écrire en priorité : les questions sans réponse
sont celles pour lesquelles aucun sujet de conseils.json n'a été reconnu.
"""

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.core.config import reglages


def lire_journal(jours: int | None) -> list[dict]:
    chemin = reglages.chemin_journal_questions
    if not chemin.is_file():
        return []
    limite = datetime.now(timezone.utc) - timedelta(days=jours) if jours else None
    lignes = []
    for texte in chemin.read_text(encoding="utf-8").splitlines():
        try:
            ligne = json.loads(texte)
        except json.JSONDecodeError:
            continue
        if limite and datetime.fromisoformat(ligne["date"]) < limite:
            continue
        lignes.append(ligne)
    return lignes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tout", action="store_true", help="afficher toutes les questions sans réponse")
    parser.add_argument("--jours", type=int, help="limiter aux N derniers jours")
    options = parser.parse_args()

    lignes = lire_journal(options.jours)
    if not lignes:
        print(f"Aucune question dans {reglages.chemin_journal_questions}")
        return

    sans_reponse = [ligne for ligne in lignes if ligne["sujet"] is None]
    print(f"Questions : {len(lignes)}  |  sans réponse : {len(sans_reponse)} "
          f"({100 * len(sans_reponse) // len(lignes)} %)\n")

    print("Sujets les plus demandés :")
    for sujet, nombre in Counter(l["sujet"] or "(aucun)" for l in lignes).most_common():
        print(f"  {nombre:5}  {sujet}")

    print("\nPar langue :")
    for langue, nombre in Counter(l["langue"] for l in lignes).most_common():
        perdues = sum(1 for l in sans_reponse if l["langue"] == langue)
        print(f"  {langue:8} {nombre:5} questions, {perdues} sans réponse")

    affichees = sans_reponse if options.tout else sans_reponse[-30:]
    if affichees:
        print(f"\nQuestions sans réponse ({'toutes' if options.tout else 'les 30 dernières'}) :")
        for ligne in affichees:
            print(f"  {ligne['date'][:10]}  [{ligne['langue']}]  {ligne['question']}")


if __name__ == "__main__":
    main()
