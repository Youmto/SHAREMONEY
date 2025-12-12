"""
Configuration principale du Bot de Partage
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# === TOKENS TELEGRAM ===
BOT_USER_TOKEN = os.getenv("BOT_USER_TOKEN", "")
BOT_ADMIN_TOKEN = os.getenv("BOT_ADMIN_TOKEN", "")

# === BASE DE DONNÉES ===
# Render utilise "postgres://" mais asyncpg nécessite "postgresql://"
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Validation des variables obligatoires
def validate_config():
    """Vérifie que toutes les variables obligatoires sont configurées"""
    errors = []
    
    if not BOT_USER_TOKEN or BOT_USER_TOKEN == "YOUR_USER_BOT_TOKEN":
        errors.append("❌ BOT_USER_TOKEN non configuré")
    
    if not BOT_ADMIN_TOKEN or BOT_ADMIN_TOKEN == "YOUR_ADMIN_BOT_TOKEN":
        errors.append("❌ BOT_ADMIN_TOKEN non configuré")
    
    if not DATABASE_URL:
        errors.append("❌ DATABASE_URL non configuré")
    
    if errors:
        print("\n" + "="*50)
        print("⚠️  ERREUR DE CONFIGURATION")
        print("="*50)
        for error in errors:
            print(error)
        print("\n📝 Sur Render, configurez ces variables dans:")
        print("   Dashboard → Votre Service → Environment")
        print("\n💡 Pour DATABASE_URL sur Render:")
        print("   1. Créez une base PostgreSQL (New → PostgreSQL)")
        print("   2. Copiez l'Internal Database URL")
        print("   3. Ajoutez-la dans les variables d'environnement")
        print("="*50 + "\n")
        sys.exit(1)

# Convertir postgres:// en postgresql:// si nécessaire
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# === CONFIGURATION ÉCONOMIQUE ===
REWARD_PER_SHARE = 100  # FCFA par partage validé
REFERRAL_BONUS = 50  # FCFA par filleul inscrit
MIN_WITHDRAWAL = 500  # FCFA minimum pour retirer
WITHDRAWAL_DELAY_HOURS = 24  # Délai de traitement

# === LIMITES DE PARTAGE ===
MAX_TELEGRAM_SHARES_PER_DAY = 5
MAX_WHATSAPP_SHARES_PER_DAY = 5
MIN_TELEGRAM_MEMBERS = 250
MIN_WHATSAPP_MEMBERS = 200
VIDEO_VALIDITY_HOURS = 48

# === LIENS ===
BOT_CHANNEL_LINK = "https://t.me/+Hzohxyi7XFY5ZWJk"

# === ADMINS (Telegram IDs) ===
ADMIN_IDS = [
    int(id.strip()) 
    for id in os.getenv("ADMIN_IDS", "").split(",") 
    if id.strip()
]

# === MÉTHODES DE PAIEMENT ===
PAYMENT_METHODS = {
    "orange_money": {
        "name": "Orange Money",
        "emoji": "🟠",
        "placeholder": "Numéro Orange Money (ex: 691234567)"
    },
    "mtn_money": {
        "name": "MTN Money", 
        "emoji": "🟡",
        "placeholder": "Numéro MTN Money (ex: 671234567)"
    },
    "binance": {
        "name": "Binance",
        "emoji": "🔶",
        "placeholder": "Binance ID ou Email"
    },
    "bitcoin": {
        "name": "Bitcoin",
        "emoji": "₿",
        "placeholder": "Adresse Bitcoin (BTC)"
    }
}

# === PLATEFORMES DE PARTAGE ===
PLATFORMS = {
    "telegram": {
        "name": "Telegram",
        "emoji": "📘",
        "min_members": MIN_TELEGRAM_MEMBERS,
        "max_shares": MAX_TELEGRAM_SHARES_PER_DAY
    },
    "whatsapp": {
        "name": "WhatsApp",
        "emoji": "💚",
        "min_members": MIN_WHATSAPP_MEMBERS,
        "max_shares": MAX_WHATSAPP_SHARES_PER_DAY
    }
}

# === STATUTS ===
class ShareStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class WithdrawalStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"

# === MESSAGES TÉMOIGNAGES PAR DÉFAUT ===
DEFAULT_TESTIMONIALS = [
    "✅ Ça fonctionne parfait ! J'ai déjà retiré de l'argent. Rejoignez maintenant : {link}",
    "💰 Je confirme, c'est fiable ! Paiement reçu en 24h. Inscrivez-vous : {link}",
    "🎯 Meilleure décision ! Simple et rapide. Rejoignez : {link}",
    "🔥 100% légit ! J'ai gagné en partageant simplement. Cliquez ici : {link}",
    "⭐ Je recommande ! Paiement rapide et sécurisé. Rejoignez-nous : {link}"
]

# === CONFIGURATION BUDGET (optionnel) ===
DAILY_BUDGET_LIMIT = int(os.getenv("DAILY_BUDGET_LIMIT", "50000"))  # FCFA
MONTHLY_BUDGET_LIMIT = int(os.getenv("MONTHLY_BUDGET_LIMIT", "1000000"))  # FCFA

# === ANTI-FRAUDE ===
MIN_IMAGE_SIZE = 500  # pixels minimum
GROUP_REUSE_DAYS = 7  # jours avant de réutiliser un groupe
MIN_DELAY_BETWEEN_SHARES = 30  # minutes entre partages

# === CLOUDINARY (Stockage vidéos) ===
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")