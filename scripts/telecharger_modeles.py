"""
Télécharge les modèles Kiriku depuis Hugging Face et les prépare pour le service.
À lancer UNE SEULE FOIS sur le serveur (ou à chaque mise à jour des modèles).

Prérequis :
  1. Avoir un compte Hugging Face et accepter les conditions sur les pages :
       https://huggingface.co/AIHubSN/M-Kiriku-ASR
       https://huggingface.co/AIHubSN/Kiriku-Wolof-TTS
       https://huggingface.co/AIHubSN/Kiriku-Pulaar-TTS
  2. Mettre HF_TOKEN=hf_xxx dans le fichier .env

Utilisation (depuis la racine du projet) :
  python -m scripts.telecharger_modeles              # tout
  python -m scripts.telecharger_modeles --asr        # ASR seulement
  python -m scripts.telecharger_modeles --tts        # TTS seulement

Ce que fait le script :
  - TTS : télécharge les fichiers VITS (model.pth + config.json) dans models/tts/<langue>/
  - ASR : télécharge M-Kiriku-ASR (~3 Go), le convertit en int8 pour faster-whisper
          (~1,6 Go) dans models/asr/m-kiriku-asr-ct2/, puis supprime l'original.
          La conversion demande ~4 Go de RAM libre pendant quelques minutes.
"""

import argparse
import json
import re
import shutil
import sys

from app.core.config import LANGUES_ASR, MODELE_ASR_HF, MODELES_TTS, reglages


def verifier_token() -> str:
    if not reglages.hf_token:
        sys.exit("ERREUR : HF_TOKEN n'est pas défini dans le fichier .env.")
    return reglages.hf_token


def telecharger_tts(token: str) -> None:
    from huggingface_hub import snapshot_download

    for langue, depot in MODELES_TTS.items():
        dossier = reglages.dossier_tts(langue)
        print(f"[TTS {langue}] Téléchargement de {depot} -> {dossier}")
        snapshot_download(
            depot,
            local_dir=dossier,
            token=token,
            allow_patterns=["*.pth", "config.json", "*.txt", "*.json"],
        )
        if not list(dossier.glob("*.pth")):
            sys.exit(f"ERREUR : aucun fichier .pth trouvé pour {depot}.")
        print(f"[TTS {langue}] OK")


def telecharger_asr(token: str) -> None:
    from huggingface_hub import snapshot_download

    dossier_hf = reglages.dossier_modeles / "asr" / "m-kiriku-asr-hf"
    dossier_ct2 = reglages.dossier_asr

    # 1. Téléchargement du modèle original (format transformers)
    print(f"[ASR] Téléchargement de {MODELE_ASR_HF} -> {dossier_hf}")
    snapshot_download(
        MODELE_ASR_HF,
        local_dir=dossier_hf,
        token=token,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
    )

    # 2. faster-whisper a besoin de tokenizer.json. S'il manque, on le génère
    #    (sinon il prendrait celui de Whisper standard, SANS les jetons Kiriku).
    if not (dossier_hf / "tokenizer.json").is_file():
        from transformers import WhisperTokenizerFast

        print("[ASR] Génération de tokenizer.json")
        WhisperTokenizerFast.from_pretrained(dossier_hf).save_pretrained(dossier_hf)

    # 3. Conversion en int8 (CTranslate2)
    import ctranslate2

    print(f"[ASR] Conversion int8 -> {dossier_ct2} (quelques minutes...)")
    convertisseur = ctranslate2.converters.TransformersConverter(
        str(dossier_hf),
        copy_files=["tokenizer.json", "preprocessor_config.json"],
        load_as_float16=True,
        low_cpu_mem_usage=True,
    )
    convertisseur.convert(str(dossier_ct2), quantization="int8", force=True)

    # 4. Vérification des jetons de langue
    verifier_jetons_langue(dossier_ct2 / "tokenizer.json")

    # 5. L'original n'est plus utile : on libère ~3 Go
    shutil.rmtree(dossier_hf, ignore_errors=True)
    print("[ASR] OK")


def verifier_jetons_langue(chemin_tokenizer) -> None:
    """Vérifie que les codes de config.LANGUES_ASR existent dans le tokenizer."""
    donnees = json.loads(chemin_tokenizer.read_text(encoding="utf-8"))
    jetons = {jeton["content"] for jeton in donnees.get("added_tokens", [])}

    problemes = False
    for langue, code in LANGUES_ASR.items():
        present = f"<|{code}|>" in jetons
        print(f"[ASR] Jeton <|{code}|> pour {langue} : {'OK' if present else 'ABSENT'}")
        problemes |= not present

    if problemes:
        codes = sorted(
            jeton for jeton in jetons if re.fullmatch(r"<\|[a-z]{2,3}\|>", jeton)
        )
        print(
            "\nATTENTION : corriger LANGUES_ASR dans app/core/config.py.\n"
            f"Jetons de langue disponibles dans le modèle :\n  {' '.join(codes)}\n"
            "(consulter la fiche du modèle pour savoir lequel correspond à chaque langue)"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asr", action="store_true", help="ASR seulement")
    parser.add_argument("--tts", action="store_true", help="TTS seulement")
    options = parser.parse_args()
    tout = not options.asr and not options.tts

    token = verifier_token()
    if tout or options.tts:
        telecharger_tts(token)
    if tout or options.asr:
        telecharger_asr(token)
    print("\nTerminé. Les modèles sont dans :", reglages.dossier_modeles)


if __name__ == "__main__":
    main()
