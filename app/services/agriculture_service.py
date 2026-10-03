"""
Réponse agricole : à partir du texte de la question, trouver un conseil.

Version simple : on cherche des mots-clés dans la question.
Si un mot-clé est trouvé, on renvoie le conseil correspondant,
sinon une réponse par défaut.

ATTENTION : les phrases en wolof et en pulaar doivent être relues
par un locuteur natif et par un conseiller agricole.
"""

# Pour chaque langue : liste de (mots-clés, conseil)
CONSEILS = {
    "wolof": [
        (["gerte"], "Ji gerte bi ci njëlbéenu nawet, bu taw bi tàmbalee."),
        (["dugub"], "Ji dugub bi bu suuf si tooyee ci taw bi."),
        (["ndox", "wisal"], "Wisal sa tool ci suba walla ci ngoon, bu naaj bi wàññikoo."),
    ],
    "pulaar": [
        (["ndiyam"], "Yuppu ndiyam e gese maa subaka walla kikiiɗe."),
    ],
}

REPONSES_PAR_DEFAUT = {
    "wolof": "Jërëjëf ci sa laaj. Duma xam tontu bi léegi. Laajal sa ndimbalkat ci mbay.",
    "pulaar": "A jaaraama e naamnal maa. Mi anndaa jaabawol ngol jooni. Naamno balloowo maa e ndema.",
}


def trouver_conseil(question: str, langue: str) -> str:
    """Retourne un conseil agricole dans la langue de l'agriculteur."""
    question = question.lower()

    for mots_cles, conseil in CONSEILS.get(langue, []):
        for mot in mots_cles:
            if mot in question:
                return conseil

    return REPONSES_PAR_DEFAUT[langue]
