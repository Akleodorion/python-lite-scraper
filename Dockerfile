FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y \
    wget \
    unzip \
    xvfb \
    chromium


WORKDIR /app

# Copier le script Python
COPY . /app

# Télécharger et installer chromedriver
RUN wget https://github.com/electron/electron/releases/download/v31.1.0/chromedriver-v31.1.0-linux-arm64.zip && \
    unzip chromedriver-v31.1.0-linux-arm64.zip -d /usr/local/bin/ && \
    rm chromedriver-v31.1.0-linux-arm64.zip

# Installer les dépendances Python
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    pip3 install nodriver

# Commande par défaut pour démarrer l'application
CMD ["python", "lite_scraper.py"]