# Déploiement d'AgroviaVoice sur le VPS OVH (modèles en local)

Serveur cible : Ubuntu 24.04, 4 vCPU (AMD EPYC, AVX2), 7,6 Go RAM, sans GPU.
Projet installé dans `/var/www/agroviavoice`.

Mémoire utilisée par le service une fois démarré : **~4 Go**
(ASR int8 ~2 Go + 2 voix TTS + torch). Lancer **un seul worker** uvicorn.

---

## 1. Paquets système (une seule fois)

```bash
sudo apt update
sudo apt install -y ffmpeg python3.12-venv libsndfile1
```

## 2. Accès aux modèles Hugging Face (une seule fois)

1. Se connecter sur https://huggingface.co et accepter les conditions sur :
   - https://huggingface.co/AIHubSN/M-Kiriku-ASR
   - https://huggingface.co/AIHubSN/Kiriku-Wolof-TTS
   - https://huggingface.co/AIHubSN/Kiriku-Pulaar-TTS
2. Créer un jeton en lecture : https://huggingface.co/settings/tokens

## 3. Mise à jour du code et des dépendances

```bash
cd /var/www/agroviavoice
git pull
python3.12 -m venv venv          # si le venv n'existe pas encore
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configuration

```bash
cp .env.example .env    # si .env n'existe pas encore
nano .env               # mettre HF_TOKEN=hf_xxx, NOMBRE_THREADS=4
```

Supprimer de l'ancien `.env` les lignes `KIRIKU_API_KEY` / `KIRIKU_API_URL` (plus utilisées).

## 5. Téléchargement et conversion des modèles (une seule fois, ~15 min)

La conversion de l'ASR demande ~4 Go de RAM : **arrêter le service pendant ce temps**.

```bash
sudo systemctl stop <nom-du-service>      # voir § 7 pour trouver le nom
python -m scripts.telecharger_modeles
```

Vérifier dans la sortie que les jetons de langue sont `OK` :

```
[ASR] Jeton <|wo|> pour wolof : OK
[ASR] Jeton <|pu|> pour pulaar : OK
[ASR] Jeton <|se|> pour serere : OK
```

S'il y a `ABSENT`, le script affiche les jetons disponibles : corriger
`LANGUES_ASR` dans `app/core/config.py` (sans re-télécharger).

Résultat : `models/asr/m-kiriku-asr-ct2/` (~1,6 Go) et `models/tts/{wolof,pulaar}/`.
Le jeton `HF_TOKEN` peut ensuite être retiré du `.env`.

## 6. Démarrage et vérification

```bash
sudo systemctl start <nom-du-service>
sudo journalctl -u <nom-du-service> -f     # attendre "Chargement du modèle ..." x3
curl http://127.0.0.1:8001/api/v1/health/models
# {"status":"ok","models":{"asr":true,"tts:wolof":true,"tts:pulaar":true}}
```

Test de bout en bout :

```bash
curl -X POST http://127.0.0.1:8001/api/v1/agriculture/synthesize \
     -F text="Jërëjëf" -F language=wolof
```

## 7. Service systemd

Trouver le service existant : `systemctl list-units --type=service | grep -i -E "agro|uvicorn|voice"`.

Exemple de fichier `/etc/systemd/system/agroviavoice.service` :

```ini
[Unit]
Description=AgroviaVoice (service IA vocal)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/agroviavoice
ExecStart=/var/www/agroviavoice/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1
Restart=always
# Le chargement des modèles prend ~1 minute au démarrage
TimeoutStartSec=300
Environment=HF_HUB_OFFLINE=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now agroviavoice
```

`HF_HUB_OFFLINE=1` garantit que le service ne contacte jamais Internet.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `MODEL_NOT_AVAILABLE` (503) | Étape 5 non faite, ou mauvais dossier `DOSSIER_MODELES` |
| `FFMPEG_NOT_FOUND` | `sudo apt install ffmpeg` |
| Service tué au démarrage (OOM) | Plusieurs workers, ou autre programme gourmand : `free -h` |
| Transcription lente | Normal sur CPU (~1x temps réel). `ASR_BEAM_SIZE=1`, `NOMBRE_THREADS=4` |
