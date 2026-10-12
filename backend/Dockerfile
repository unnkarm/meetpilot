FROM python:3.11-slim

WORKDIR /app


# System deps for psycopg2 build, audio mimetype detection, and pydub audio chunking (ffmpeg/ffprobe).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    espeak-ng \
    chromium \
    xvfb xauth xdotool xclip x11-utils fluxbox pulseaudio pulseaudio-utils \
    x11vnc novnc websockify \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/voices && python -m piper.download_voices --data-dir /app/voices en_US-lessac-medium en_US-ryan-medium
# Fetch the default STT model while building, so live transcription never
# depends on Hugging Face access after the stack has been provisioned.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
ENV HF_HUB_OFFLINE=1

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

RUN mkdir -p /app/storage/audio

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
