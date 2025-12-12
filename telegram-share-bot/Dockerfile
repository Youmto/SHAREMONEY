# ============================================
# Dockerfile pour Telegram Share Bot
# Optimisé pour Render.com
# ============================================

# Image de base Python légère
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY . .

# Créer un utilisateur non-root pour la sécurité
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Commande de démarrage
CMD ["python", "run_bots.py"]