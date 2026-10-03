"""
Opérations sur les fichiers audio : vérification, sauvegarde, conversion,
lecture et nettoyage.

Ce fichier ne connaît ni FastAPI, ni les modèles IA.
"""

import subprocess
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from app.core.config import reglages
from app.core.errors import ErreurApp

# .ogg : format des notes vocales WhatsApp, très utilisé par les agriculteurs.
# .webm : format enregistré par le micro du navigateur (Chrome, Firefox).
EXTENSIONS_AUTORISEES = [".wav", ".mp3", ".m4a", ".ogg", ".webm"]

# Les modèles Whisper (Kiriku ASR) attendent de l'audio mono à 16 kHz.
FREQUENCE_ASR = 16000

# M-Kiriku-ASR a été entraîné sans extraits de moins de 0,5 s.
DUREE_MIN_SECONDES = 0.5

# En dessous de ce volume, on considère que l'audio est du silence.
SEUIL_SILENCE = 0.01


def verifier_fichier_audio(nom_fichier: str, contenu: bytes) -> str:
    """Vérifie l'extension et la taille du fichier reçu. Retourne l'extension."""
    extension = Path(nom_fichier or "").suffix.lower()

    # 1. Le format doit être accepté
    if extension not in EXTENSIONS_AUTORISEES:
        formats = ", ".join(EXTENSIONS_AUTORISEES)
        raise ErreurApp("INVALID_AUDIO_FILE", f"Format audio non accepté. Formats autorisés : {formats}.")

    # 2. Le fichier ne doit pas être vide
    if len(contenu) == 0:
        raise ErreurApp("EMPTY_AUDIO", "Le fichier audio est vide.")

    # 3. Le fichier ne doit pas être trop gros
    taille_max_octets = reglages.taille_max_audio_mo * 1024 * 1024
    if len(contenu) > taille_max_octets:
        raise ErreurApp(
            "AUDIO_TOO_LARGE",
            f"Le fichier audio dépasse la taille maximale de {reglages.taille_max_audio_mo} Mo.",
            code_http=413,
        )
    return extension


def sauvegarder_audio_recu(contenu: bytes, extension: str) -> Path:
    """Sauvegarde le fichier reçu sous un nom aléatoire (jamais le nom envoyé par l'utilisateur)."""
    reglages.dossier_audio_entree.mkdir(parents=True, exist_ok=True)
    chemin = reglages.dossier_audio_entree / f"input_{uuid.uuid4().hex}{extension}"
    chemin.write_bytes(contenu)
    return chemin


def convertir_audio(chemin_entree: Path) -> Path:
    """Convertit n'importe quel format accepté en WAV mono 16 kHz avec ffmpeg."""
    chemin_sortie = chemin_entree.with_name(f"{chemin_entree.stem}_converti.wav")
    commande = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(chemin_entree),
        "-ac", "1",                   # mono
        "-ar", str(FREQUENCE_ASR),    # 16 kHz
        str(chemin_sortie),
    ]
    try:
        resultat = subprocess.run(commande, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise ErreurApp("FFMPEG_NOT_FOUND", "ffmpeg n'est pas installé sur le serveur.", code_http=500)

    if resultat.returncode != 0:
        supprimer_fichier(chemin_sortie)
        raise ErreurApp("INVALID_AUDIO_FILE", "Le fichier audio est invalide ou corrompu.")
    return chemin_sortie


def lire_audio(chemin: Path) -> np.ndarray:
    """Lit un WAV mono et vérifie qu'il n'est ni vide, ni silencieux, ni trop long."""
    echantillons, frequence = sf.read(chemin, dtype="float32")
    duree = len(echantillons) / frequence

    if duree < DUREE_MIN_SECONDES or np.abs(echantillons).max() < SEUIL_SILENCE:
        raise ErreurApp("EMPTY_AUDIO", "L'audio est vide ou trop court.")

    if duree > reglages.duree_max_audio_secondes:
        raise ErreurApp(
            "AUDIO_TOO_LONG",
            f"L'audio dépasse la durée maximale de {reglages.duree_max_audio_secondes} secondes.",
        )
    return echantillons


def preparer_audio_pour_asr(nom_fichier: str, contenu: bytes) -> np.ndarray:
    """
    Passe d'un fichier envoyé par l'utilisateur à un audio 16 kHz prêt pour l'ASR.
    Les fichiers temporaires sont toujours supprimés, même en cas d'erreur.
    """
    # 1. Vérifier puis sauvegarder le fichier reçu
    extension = verifier_fichier_audio(nom_fichier, contenu)
    chemin_recu = sauvegarder_audio_recu(contenu, extension)
    chemin_converti = None
    try:
        # 2. Convertir en WAV 16 kHz puis le lire
        chemin_converti = convertir_audio(chemin_recu)
        return lire_audio(chemin_converti)
    finally:
        # 3. Nettoyer les fichiers temporaires
        supprimer_fichier(chemin_recu)
        if chemin_converti:
            supprimer_fichier(chemin_converti)


def sauvegarder_audio_reponse(echantillons, frequence: int) -> str:
    """Écrit l'audio généré dans audio/output/ et retourne le nom du fichier."""
    reglages.dossier_audio_sortie.mkdir(parents=True, exist_ok=True)
    nom_fichier = f"reponse_{uuid.uuid4().hex}.wav"
    sf.write(reglages.dossier_audio_sortie / nom_fichier, np.asarray(echantillons, dtype=np.float32), frequence)
    return nom_fichier


def supprimer_fichier(chemin: Path) -> None:
    chemin.unlink(missing_ok=True)
