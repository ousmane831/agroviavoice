
"""
Service temporaire de conseils agricoles.

Cette version utilise des mots-clés pour identifier le sujet
de la question et retourner un conseil prédéfini.

IMPORTANT :
- Cette base est temporaire et sert uniquement pour le MVP / la démo.
- Les conseils agricoles devront ensuite être remplacés par de
  vraies données provenant de sources agronomiques fiables.
- Les traductions Wolof et Pulaar doivent être validées par des
  locuteurs natifs et des conseillers agricoles.
"""

import re


# ============================================================
# CONSEILS AGRICOLES TEMPORAIRES
# ============================================================

CONSEILS = {
    "wolof": [
        # ----------------------------------------------------
        # ARACHIDE
        # ----------------------------------------------------
        (
            ["gerte", "gerte yi", "arachide"],
            (
                "Bu ngay ji gerte, seet bu baax ne suuf si set na te am na tooy. "
                "Tàmbali ji bi gannaaw bu taw bi tàmbalee bu baax."
            ),
        ),

        # ----------------------------------------------------
        # MIL
        # ----------------------------------------------------
        (
            ["dugub", "dugub yi", "mil"],
            (
                "Bu ngay ji dugub, xool ne suuf si tooy na bu baax. "
                "Bul ji ci suuf bu wow lool, te seet xaalis bi gannaaw taw."
            ),
        ),

        # ----------------------------------------------------
        # EAU / IRRIGATION
        # ----------------------------------------------------
        (
            ["ndox", "wisal", "ndox mi", "taw", "taw bi"],
            (
                "Wisal sa tool ci suba walla ci ngoon, waaye xool xaalu suuf si "
                "ba noppi bañ a def ndox bu ëpp. Bu tawee, xool ndox bi ci tool bi."
            ),
        ),

        # ----------------------------------------------------
        # SOL
        # ----------------------------------------------------
        (
            ["suuf", "suuf si", "sol", "ph"],
            (
                "Xool xaalu suuf si bu njëkk. Tooy, pH ak ay nutriments "
                "mën nañu soppi ni ngay doxale sa culture."
            ),
        ),

        # ----------------------------------------------------
        # MALADIES
        # ----------------------------------------------------
        (
            ["feebar", "feebar bi", "maladie", "maladi", "wérul"],
            (
                "Bu nga gis feebar ci sa mbey, jël nataal bu leer te xool "
                "xob yi, garab yi ak coppite yi ci plant bi avant a def ay traitement."
            ),
        ),

        # ----------------------------------------------------
        # RAVAGEURS / INSECTES
        # ----------------------------------------------------
        (
            ["jëf", "jëf yi", "insect", "insectes", "mboy", "ravageur"],
            (
                "Bu nga gis ay insectes ci sa culture, xool fu ñu bari ak "
                "ni ñuy yàq plant yi. Nataal bu leer mën na dimbali ngir seetlu leen."
            ),
        ),

        # ----------------------------------------------------
        # ENGRAIS / NUTRIMENTS
        # ----------------------------------------------------
        (
            ["engrais", "fertilisant", "nutriment", "azote", "phosphore", "potassium"],
            (
                "Bul def engrais ci xel rekk. Xam xaalu suuf si moo gën a baax "
                "ngir xam li culture bi soxla. Bu amee analyse du suuf, jëfandikoo ko."
            ),
        ),

        # ----------------------------------------------------
        # SEMIS
        # ----------------------------------------------------
        (
            ["ji", "semis", "jiitu", "ji bi"],
            (
                "Bu ngay ji, xool taw yi ak xaalu suuf si. Suuf bi war na am "
                "tooy bu doy ngir graines yi man a tàmbali."
            ),
        ),

        # ----------------------------------------------------
        # RECOLTE
        # ----------------------------------------------------
        (
            ["récolte", "recolte", "njël", "njël bi", "dund"],
            (
                "Bu ñuy jeexal culture, xool màggug plant bi ak xaalam. "
                "Tànnal waxtu bu baax ngir récolte bi te aar produit yi."
            ),
        ),

        # ----------------------------------------------------
        # TOMATE / LEGUMES
        # ----------------------------------------------------
        (
            ["tomate", "tomaat", "legume", "légume", "poivron", "oignon"],
            (
                "Ci légumes yi, seet suuf si, ndox mi ak xaalu xob yi saa su nekk. "
                "Bu nga gis coppite bu doy waar, jël nataal ngir xool ko."
            ),
        ),

        # ----------------------------------------------------
        # METEO / PLUIE
        # ----------------------------------------------------
        (
            ["meteo", "météo", "taw", "taw bi", "taw yi", "weer"],
            (
                "Xool xaalu taw yi ak météo laata ngay ji, wisal walla def traitement. "
                "Xibaaru météo mën na dimbali la ngir gën a tëral sa mbey."
            ),
        ),

        # ----------------------------------------------------
        # CONSEIL GENERAL AGRICULTEUR
        # ----------------------------------------------------
        (
            ["tool", "mbay", "culture", "mbey", "parcelle"],
            (
                "Ngir gën a doxal sa mbey, xool suuf, ndox, météo ak xaalu culture bi. "
                "Données yu jóge ci sa parcelle mën nañu dimbali la ci ay décisions yu gën a baax."
            ),
        ),
    ],

    "pulaar": [
        # ----------------------------------------------------
        # EAU
        # ----------------------------------------------------
        (
            ["ndiyam", "ndiyam maa", "ndiyam e"],
            (
                "Hoto ndiyam e gese maa subaka walla kikiiɗe. "
                "Hoto waɗa ndiyam ɗuɗɗum, ngam leydi maa waawi waasde."
            ),
        ),

        # ----------------------------------------------------
        # CHAMP / CULTURE
        # ----------------------------------------------------
        (
            ["lesdi", "leydi", "ngesa", "mbay", "culture"],
            (
                "Ɗaɓɓu xaalu leydi maa, ndiyam e ɗaɓɓude culture maa. "
                "Ɗee kabaruuji mbaawi wallude maa e cuɓagol moƴƴere."
            ),
        ),

        # ----------------------------------------------------
        # MIL
        # ----------------------------------------------------
        (
            ["dugub", "milt", "mil"],
            (
                "So a waɗa dugub, ƴeewto leydi e ndiyam ndee. "
                "Waɗ semis nde taw e xaalu leydi maa moƴƴi."
            ),
        ),

        # ----------------------------------------------------
        # ARACHIDE
        # ----------------------------------------------------
        (
            ["gerte", "arachide"],
            (
                "So a waɗa gerte, ƴeewto leydi e ndiyam. "
                "Ɓeydude semis e waqtu moƴƴi waawi wallude culture maa."
            ),
        ),

        # ----------------------------------------------------
        # MALADIE
        # ----------------------------------------------------
        (
            ["feebre", "feebar", "maladie", "maladi"],
            (
                "So a yiyii feebre e culture maa, ƴeewto ɗe ngesa e leaf ɗe. "
                "Naatnu foto moƴƴo ngam ƴeewtagol feebre ndee."
            ),
        ),

        # ----------------------------------------------------
        # INSECTES
        # ----------------------------------------------------
        (
            ["insect", "insectes", "ravageur"],
            (
                "So a yiyii insectes e ngesa maa, ƴeewto ɗo ɓe heɓi e no ɓe bonniri "
                "culture maa. Foto waawi wallude e ƴeewtagol."
            ),
        ),

        # ----------------------------------------------------
        # SOL
        # ----------------------------------------------------
        (
            ["suuf", "sol", "ph"],
            (
                "Ƴeewto xaalu leydi maa. Ɓeydude kabaruuji dow suuf, ndiyam "
                "e nutriments mbaawi wallude e cuɓagol bonnude culture."
            ),
        ),
    ],
}


# ============================================================
# REPONSES PAR DEFAUT
# ============================================================

REPONSES_PAR_DEFAUT = {
    "wolof": (
        "Jërëjëf ci sa laaj. Léegi, man naa dimbali la ci suuf, ndox, "
        "culture, feebar, insectes walla météo. Wax ma lu ngay jàngale "
        "ci sa tool ngir ma gën a dimbali la."
    ),

    "pulaar": (
        "A jaaraama e naamnal maa. Mi waawi wallude maa e leydi, ndiyam, "
        "culture, feebre, insectes walla météo. Haaldu-mi ko wonde e ngesa maa "
        "ngam mi wallu maa ɓurɗo."
    ),
}


# ============================================================
# NORMALISATION
# ============================================================

def normaliser_question(question: str) -> str:
    """
    Nettoie légèrement la question avant la recherche.
    """

    question = question.lower().strip()

    # Remplace les espaces multiples
    question = re.sub(r"\s+", " ", question)

    return question


# ============================================================
# RECHERCHE DU CONSEIL
# ============================================================

def trouver_conseil(question: str, langue: str) -> str:
    """
    Retourne un conseil agricole temporaire dans la langue
    demandée.

    La recherche se fait actuellement par mots-clés.

    Cette fonction sera remplacée plus tard par une recherche
    dans la vraie base de connaissances agricoles / RAG.
    """

    question = normaliser_question(question)

    conseils_langue = CONSEILS.get(langue, [])

    # Recherche des mots-clés
    for mots_cles, conseil in conseils_langue:
        for mot in mots_cles:
            if mot.lower() in question:
                return conseil

    # Aucun sujet reconnu
    return REPONSES_PAR_DEFAUT.get(
        langue,
        "Désolé, je ne peux pas encore répondre à cette question."
    )