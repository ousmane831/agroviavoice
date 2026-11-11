# Image du service IA (FastAPI).
# Python 3.12 : même version que le VPS (Ubuntu 24.04).
FROM python:3.12-slim

# Pas de fichiers .pyc, et des logs affichés immédiatement.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ffmpeg convertit les audios reçus (mp3, m4a, ogg, webm) en WAV 16 kHz pour l'ASR.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installées avant de copier le code : Docker réutilise cette étape
# tant que requirements.txt ne change pas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# Les modèles (~5 Go) ne sont pas dans l'image : monter le dossier models/ en volume.
# ex. docker run -v /var/www/agroviavoice/models:/app/models ...
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
