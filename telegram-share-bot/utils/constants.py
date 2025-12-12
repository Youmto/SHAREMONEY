"""
Constantes et messages du bot
"""

# ============================================
# MESSAGES DU BOT UTILISATEUR
# ============================================

WELCOME_MESSAGE = """
🎉 <b>Bienvenue sur ShareBot !</b>

Gagnez <b>100 FCFA</b> pour chaque partage de vidéo validé !

📋 <b>Comment ça marche :</b>
1️⃣ Regardez la vidéo du jour
2️⃣ Partagez-la dans un groupe Telegram (250+ membres) ou WhatsApp (200+ membres)
3️⃣ Envoyez une capture d'écran comme preuve
4️⃣ Recevez vos gains une fois validé !

💰 <b>Règles :</b>
• Maximum 10 partages par jour par plateforme
• Retrait possible dès 500 FCFA
• Paiement sous 24h

🚀 <b>Prêt à gagner ?</b>
"""

PHONE_REQUEST_MESSAGE = """
📱 Pour continuer, partagez votre numéro de téléphone.

Cela nous permet de :
• Sécuriser votre compte
• Faciliter vos retraits

👇 Cliquez sur le bouton ci-dessous :
"""

REGISTRATION_SUCCESS_MESSAGE = """
✅ <b>Inscription réussie !</b>

🎫 Votre code de parrainage : <code>{referral_code}</code>
💰 Partagez-le et gagnez 50 FCFA par filleul !

📹 Tapez /video pour voir la vidéo du jour et commencer à gagner !
"""

NO_VIDEO_MESSAGE = """
😕 <b>Aucune vidéo disponible</b>

Il n'y a pas de vidéo à partager pour le moment.
Revenez plus tard !

🔔 Vous serez notifié dès qu'une nouvelle vidéo sera disponible.
"""

VIDEO_TEMPLATE = """
📹 <b>VIDÉO DU JOUR</b>
━━━━━━━━━━━━━━━━━━

📝 <b>{title}</b>

{caption}

⏰ Expire dans : <b>{time_remaining}</b>
💰 Gain : <b>100 FCFA</b> par partage validé

👇 Choisissez où partager :
"""

SHARE_INSTRUCTIONS_TELEGRAM = """
📘 <b>PARTAGE TELEGRAM</b>

📊 Partages aujourd'hui : <b>{shares_today}/5</b>

📋 <b>Instructions :</b>
1. Transférez la vidéo + message dans un groupe de <b>250+ membres</b>
2. Faites une capture d'écran montrant :
   • Le nom du groupe
   • Le nombre de membres
   • Votre message avec la vidéo

📤 Transférez ce contenu, puis envoyez votre preuve !
"""

SHARE_INSTRUCTIONS_WHATSAPP = """
💚 <b>PARTAGE WHATSAPP</b>

📊 Partages aujourd'hui : <b>{shares_today}/5</b>

📋 <b>Instructions :</b>
1. Partagez la vidéo + message dans un groupe de <b>200+ membres</b>
2. Faites une capture d'écran montrant :
   • Le nom du groupe
   • Le nombre de participants
   • Votre message avec la vidéo

📤 Partagez ce contenu, puis envoyez votre preuve !
"""

PROOF_REQUEST_MESSAGE = """
📸 <b>Envoyez votre preuve de partage</b>

Votre screenshot doit montrer :
✓ Le nom du groupe
✓ Le nombre de membres
✓ Votre message avec la vidéo visible

📷 Envoyez votre capture d'écran maintenant :
"""

GROUP_LINK_REQUEST = """
🔗 <b>Entrez le lien du groupe</b>

Envoyez le lien du groupe {platform} où vous avez partagé :

{example}
"""

GROUP_NAME_REQUEST = """
📝 <b>Quel est le nom du groupe ?</b>

Entrez le nom exact du groupe où vous avez partagé :
"""

SHARE_SUBMITTED_MESSAGE = """
✅ <b>Preuve soumise avec succès !</b>

📋 <b>Récapitulatif :</b>
• Plateforme : {platform}
• Groupe : {group_name}
• Lien : {group_link}
• Statut : ⏳ En attente de validation

⏱️ Délai de validation : généralement sous 24h

Vous serez notifié dès validation !
"""

BALANCE_MESSAGE = """
💰 <b>Votre solde</b>

📊 Solde actuel : <b>{balance}</b>
💵 Total gagné : <b>{total_earned}</b>

📈 <b>Statistiques :</b>
• Partages validés : {approved_shares}
• Partages en attente : {pending_shares}
• Taux de validation : {validation_rate}%

💳 Minimum de retrait : 500 FCFA
"""

WITHDRAWAL_METHOD_MESSAGE = """
💳 <b>Retrait de fonds</b>

💰 Solde disponible : <b>{balance}</b>
📍 Minimum : 500 FCFA

Choisissez votre méthode de paiement :
"""

WITHDRAWAL_DETAILS_MESSAGE = """
📝 <b>Entrez vos informations</b>

Méthode : {method}

{placeholder}
"""

WITHDRAWAL_AMOUNT_MESSAGE = """
💵 <b>Montant à retirer</b>

💰 Solde disponible : <b>{balance}</b>

Entrez le montant ou choisissez une option :
"""

WITHDRAWAL_CONFIRM_MESSAGE = """
📋 <b>Confirmation de retrait</b>

💰 Montant : <b>{amount}</b>
📱 Méthode : {method}
📍 Envoyé à : {details}

⚠️ Vérifiez bien les informations !
"""

WITHDRAWAL_SUCCESS_MESSAGE = """
✅ <b>Demande de retrait enregistrée !</b>

📊 Statut : ⏳ En traitement
⏱️ Délai : Sous 24h

Vous recevrez une notification une fois le paiement effectué.
"""

REFERRAL_MESSAGE = """
👥 <b>Programme de parrainage</b>

🎫 Votre code : <code>{referral_code}</code>

🔗 Lien de parrainage :
{referral_link}

💰 Gagnez <b>50 FCFA</b> pour chaque ami qui s'inscrit !

📊 <b>Vos statistiques :</b>
• Filleuls inscrits : {referral_count}
• Bonus gagnés : {referral_earnings}
"""

HELP_MESSAGE = """
❓ <b>Aide - ShareBot</b>

📋 <b>Commandes disponibles :</b>
• /start - Démarrer le bot
• /video - Voir la vidéo du jour
• /share - Soumettre une preuve
• /balance - Voir votre solde
• /withdraw - Retirer vos gains
• /history - Historique des partages
• /referral - Code de parrainage
• /help - Cette aide

💬 <b>Questions fréquentes :</b>

<b>Q: Combien puis-je gagner ?</b>
R: 100 FCFA par partage validé, jusqu'à 10 partages/jour.

<b>Q: Comment être validé ?</b>
R: Assurez-vous que votre screenshot montre clairement le groupe et son nombre de membres.

<b>Q: Quand suis-je payé ?</b>
R: Les paiements sont traités sous 24h après validation.

🆘 Problème ? Contactez @admin
"""

# ============================================
# MESSAGES D'ERREUR
# ============================================

ERROR_NOT_REGISTERED = "❌ Vous devez d'abord vous inscrire. Tapez /start"
ERROR_USER_BLOCKED = "❌ Votre compte est bloqué. Contactez le support."
ERROR_NO_ACTIVE_VIDEO = "❌ Aucune vidéo active. Revenez plus tard."
ERROR_DAILY_LIMIT = "❌ Limite journalière atteinte. Revenez demain !"
ERROR_INSUFFICIENT_BALANCE = "❌ Solde insuffisant. Minimum : 500 FCFA"
ERROR_INVALID_AMOUNT = "❌ Montant invalide. Entrez un nombre valide."
ERROR_INVALID_LINK = "❌ Lien invalide. Vérifiez le format."
ERROR_GENERIC = "❌ Une erreur est survenue. Réessayez."

# ============================================
# ÉTATS DE CONVERSATION
# ============================================

class ConversationState:
    # Inscription
    WAITING_PHONE = "waiting_phone"
    
    # Partage
    SELECTING_PLATFORM = "selecting_platform"
    SELECTING_TESTIMONIAL = "selecting_testimonial"
    WRITING_CUSTOM_TESTIMONIAL = "writing_custom_testimonial"
    WAITING_PROOF = "waiting_proof"
    WAITING_GROUP_LINK = "waiting_group_link"
    WAITING_GROUP_NAME = "waiting_group_name"
    
    # Retrait
    SELECTING_PAYMENT_METHOD = "selecting_payment_method"
    WAITING_PAYMENT_DETAILS = "waiting_payment_details"
    WAITING_AMOUNT = "waiting_amount"
    CONFIRMING_WITHDRAWAL = "confirming_withdrawal"

# ============================================
# CALLBACKS
# ============================================

class Callback:
    # Partage
    SHARE = "share"
    PLATFORM_TELEGRAM = "platform_telegram"
    PLATFORM_WHATSAPP = "platform_whatsapp"
    TESTIMONIAL_PREFIX = "testimonial_"
    CUSTOM_TESTIMONIAL = "custom_testimonial"
    COPY_TEXT = "copy_text"
    
    # Retrait
    WITHDRAW = "withdraw"
    PAYMENT_METHOD_PREFIX = "payment_"
    AMOUNT_PREFIX = "amount_"
    CONFIRM_WITHDRAWAL = "confirm_withdrawal"
    CANCEL_WITHDRAWAL = "cancel_withdrawal"
    
    # Navigation
    BACK = "back"
    MAIN_MENU = "main_menu"
    
    # Admin
    APPROVE = "approve_"
    REJECT = "reject_"
    REJECT_REASON_PREFIX = "reject_reason_"
    SKIP = "skip_"
    COMPLETE_WITHDRAWAL = "complete_w_"
    REJECT_WITHDRAWAL = "reject_w_"
