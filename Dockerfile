# Image du service IA (FastAPI).
# Python 3.11 : la version exigée par Coqui TTS 0.19.0 (modèles Kiriku TTS).
FROM python:3.11-slim

# Pas de fichiers .pyc, et des logs affichés immédiatement.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ffmpeg convertit les audios reçus (mp3, m4a, ogg, webm) en WAV 16 kHz pour l'ASR.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installées avant de copier le code : Docker réutilise cette étape
# tant que requirements.txt ne change pas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
