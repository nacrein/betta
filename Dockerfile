FROM python:3.12-slim

# ffmpeg is required for voice playback; the others cover PyNaCl builds if no
# prebuilt wheel is available for the platform.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

CMD ["python", "-m", "src"]
