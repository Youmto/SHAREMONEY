# 🎬 ShareBot - Bot Telegram de Partage Rémunéré

Bot Telegram permettant aux utilisateurs de gagner de l'argent en partageant des vidéos promotionnelles dans des groupes Telegram et WhatsApp.

## 📋 Fonctionnalités

### Bot Utilisateur
- ✅ Inscription avec numéro de téléphone
- 📹 Visionnage de la vidéo du jour
- 📤 Soumission de preuves de partage (screenshot + lien groupe)
- 💰 Consultation du solde
- 💳 Demande de retrait (Orange Money, MTN Money, Binance, Bitcoin)
- 👥 Système de parrainage (+50 FCFA par filleul)
- 📊 Historique des partages et retraits

### Bot Admin
- ✅ Validation/rejet des preuves de partage
- 💳 Traitement des demandes de retrait
- 📹 Gestion des vidéos (ajout, durée de validité)
- 💬 Gestion des messages témoignages
- 📊 Statistiques en temps réel
- 📢 Broadcast à tous les utilisateurs

## 💰 Économie

| Paramètre | Valeur |
|-----------|--------|
| Récompense par partage | 100 FCFA |
| Bonus parrainage | 50 FCFA |
| Minimum de retrait | 500 FCFA |
| Max partages Telegram/jour | 5 |
| Max partages WhatsApp/jour | 5 |
| Min membres Telegram | 250 |
| Min membres WhatsApp | 200 |

## 🛠️ Installation

### Prérequis
- Python 3.10+
- PostgreSQL (Neon recommandé)
- Compte Telegram et tokens de bot

### 1. Cloner le projet
```bash
git clone https://github.com/votre-repo/telegram-share-bot.git
cd telegram-share-bot
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

### 4. Créer les bots Telegram
1. Ouvrir [@BotFather](https://t.me/BotFather) sur Telegram
2. Créer 2 bots : un pour les utilisateurs, un pour l'admin
3. Copier les tokens dans `.env`

### 5. Configurer la base de données Neon
1. Créer un compte sur [neon.tech](https://neon.tech)
2. Créer un nouveau projet
3. Copier l'URL de connexion dans `.env`

### 6. Lancer les bots

**Option 1 : Les deux bots ensemble**
```bash
python run_bots.py
```

**Option 2 : Séparément**
```bash
# Terminal 1 - Bot utilisateur
python -m bot_user.main

# Terminal 2 - Bot admin
python -m bot_admin.main
```

## 🚀 Déploiement sur Render

### Option A : Un seul service (économique)
1. Créer un nouveau **Background Worker** sur Render
2. Connecter votre repo GitHub
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python run_bots.py`
5. Ajouter les variables d'environnement

### Option B : Deux services séparés (recommandé)
1. Créer 2 **Background Workers**
2. Service 1 (User Bot): `python -m bot_user.main`
3. Service 2 (Admin Bot): `python -m bot_admin.main`

## 📁 Structure du projet

```
telegram-share-bot/
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration globale
├── database/
│   ├── __init__.py
│   ├── connection.py        # Connexion PostgreSQL
│   └── queries.py           # Requêtes SQL
├── bot_user/
│   ├── main.py              # Point d'entrée utilisateur
│   ├── handlers/
│   │   ├── start.py         # Inscription
│   │   ├── video.py         # Gestion vidéos
│   │   ├── share.py         # Soumission partages
│   │   ├── balance.py       # Solde et historique
│   │   ├── withdraw.py      # Retraits
│   │   └── referral.py      # Parrainage
│   └── keyboards/
│       └── menus.py         # Claviers inline
├── bot_admin/
│   ├── main.py              # Point d'entrée admin
│   ├── handlers/
│   │   └── admin.py         # Tous les handlers admin
│   └── keyboards/
│       └── admin_menus.py   # Claviers admin
├── services/
│   ├── fraud_detector.py    # Validation et anti-fraude
│   └── notifications.py     # Notifications Telegram
├── utils/
│   ├── helpers.py           # Fonctions utilitaires
│   └── constants.py         # Messages et constantes
├── requirements.txt
├── .env.example
├── Procfile
├── run_bots.py              # Script combiné
└── README.md
```

## 🔒 Sécurité et Anti-fraude

- **Hash des images** : Détection des doublons
- **Limite par groupe** : Un partage par groupe tous les 7 jours
- **Limite journalière** : Max 5 partages par plateforme
- **Blacklist de groupes** : Possibilité de bloquer des groupes
- **Score de confiance** : Aide à la validation manuelle
- **Validation manuelle** : Toutes les preuves sont vérifiées

## 📝 Commandes

### Bot Utilisateur
| Commande | Description |
|----------|-------------|
| `/start` | Inscription ou menu principal |
| `/video` | Voir la vidéo du jour |
| `/share` | Soumettre une preuve |
| `/balance` | Voir le solde |
| `/withdraw` | Demander un retrait |
| `/referral` | Code de parrainage |
| `/help` | Aide |

### Bot Admin
| Commande | Description |
|----------|-------------|
| `/start` | Menu admin |
| `/pending` | Preuves en attente |
| `/stats` | Statistiques |

## ⚙️ Configuration avancée

Modifiez `config/settings.py` pour personnaliser :
- Récompenses et limites
- Taille minimum des groupes
- Méthodes de paiement
- Plafonds budgétaires
- Messages par défaut

## 🆘 Support

Pour toute question ou problème, ouvrez une issue sur GitHub.

## 📄 Licence

MIT License - Voir LICENSE pour plus de détails.
