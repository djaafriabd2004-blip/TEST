import asyncio
import logging
import json
import uuid
import html
import time
import datetime
from aiohttp import web
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vector SVGs (Clean, Professional, Official Brand Geometry, Zero Emojis)
# ---------------------------------------------------------------------------

SVG_GLOBE = """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>"""
SVG_WALLET = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><circle cx="18" cy="14" r="2"/></svg>"""
SVG_LIGHTNING = """<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>"""
SVG_PLANE = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>"""
SVG_SHIELD = """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>"""
SVG_ALERT = """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>"""
SVG_COPY = """<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>"""
SVG_ARROW_RIGHT = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>"""
SVG_ARROW_LEFT = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>"""
SVG_CHECK = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>"""

# Official Payment Method Logos
SVG_USDT = """
<svg width="44" height="44" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#009393"/>
  <path d="M17.922 17.383v-.002c-.11.008-.677.042-1.942.042-1.01 0-1.721-.03-1.971-.042v.002C10.638 17.228 8 16.518 8 15.66c0-.859 2.638-1.569 6.009-1.723V10.5h-4.3V8.5h12.582v2h-4.3v3.435c3.364.155 5.996.864 5.996 1.724 0 .859-2.632 1.568-5.996 1.723v.001zm0-3.053V12.5h-3.864v1.83c-2.887.13-5.066.67-5.066 1.33 0 .66 2.179 1.2 5.066 1.33v-1.33h3.864v1.33c2.88-.13 5.053-.67 5.053-1.33 0-.66-2.173-1.2-5.053-1.33z" fill="#fff"/>
</svg>
"""

SVG_GRAM_TON = """
<svg width="44" height="44" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#0088CC"/>
  <path d="M16 6.5L8 12.5L16 26.5L24 12.5L16 6.5Z" fill="#fff"/>
  <path d="M16 6.5L24 12.5L16 26.5V6.5Z" fill="#B3E5FC"/>
  <path d="M16 6.5L12 12.5L16 26.5V6.5Z" fill="#E1F5FE"/>
  <path d="M8 12.5H24L16 16.5L8 12.5Z" fill="rgba(0,0,0,0.1)"/>
</svg>
"""

SVG_BINANCE = """
<svg width="44" height="44" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#181A20"/>
  <path d="M16 8l3.2 3.2-3.2 3.2-3.2-3.2L16 8zm-6.4 6.4l3.2 3.2-3.2 3.2-3.2-3.2 3.2-3.2zm12.8 0l3.2 3.2-3.2 3.2-3.2-3.2 3.2-3.2zM16 20.8l3.2 3.2-3.2 3.2-3.2-3.2 3.2-3.2zm0-5.12l1.6 1.6-1.6 1.6-1.6-1.6 1.6-1.6z" fill="#F3BA2F"/>
</svg>
"""

SVG_LTC = """
<svg width="44" height="44" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#345D9D"/>
  <path d="M14.5 21.5h6v2h-8.5l2-9h3.2l-.7 3.2h2.5l-.5 2h-2.5l-.5 1.8z" fill="#fff"/>
</svg>
"""

SVG_CRYPTOBOT = """
<svg width="44" height="44" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#2AABEE"/>
  <path d="M11 13.5c0-1.9 1.6-3.5 3.5-3.5h3c1.9 0 3.5 1.6 3.5 3.5v5c0 1.9-1.6 3.5-3.5 3.5h-3c-1.9 0-3.5-1.6-3.5-3.5v-5z" fill="#fff"/>
  <circle cx="13.5" cy="15.5" r="1.2" fill="#2AABEE"/>
  <circle cx="18.5" cy="15.5" r="1.2" fill="#2AABEE"/>
  <path d="M16 8v2M9.5 16h1.5M21 16h1.5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/>
</svg>
"""

SVG_XROCKET = """
<svg width="44" height="44" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="16" fill="#FF5C00"/>
  <path d="M20.5 10c-2.4 2.4-4.8 3.5-6.5 3.8l-1.3-1.3 1-2.4-2.4 1-1.3-1.3c.3-1.7 1.4-4.1 3.8-6.5 3.2-3.2 7.7-2.9 7.7-2.9s.3 4.5-2.9 7.7l-1 1z" transform="translate(4,4) scale(0.7)" fill="#fff"/>
</svg>
"""

# Small Badge SVGs
SVG_BADGE_TRON = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 3L21.5 2L15 22L2 3Z" fill="#EF4444"/><path d="M21.5 2L10 11L15 22L21.5 2Z" fill="#F87171"/></svg>"""
SVG_BADGE_BNB = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="#F3BA2F"/><path d="M12 7L14.5 9.5L12 12L9.5 9.5L12 7Z" fill="#181A20"/><path d="M7 12L9.5 9.5L12 12L9.5 14.5L7 12Z" fill="#181A20"/></svg>"""
SVG_BADGE_TON = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 3L19 8L12 21L5 8L12 3Z" fill="#38BDF8"/></svg>"""
SVG_BADGE_BINANCE = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 4L15 7L12 10L9 7L12 4Z" fill="#F3BA2F"/><path d="M12 14L15 17L12 20L9 17L12 14Z" fill="#F3BA2F"/></svg>"""
SVG_BADGE_LTC = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="#345D9D"/><path d="M10 16H15V18H8L10 9H13L12 12H14.5L14 14H11.5L10 16Z" fill="white"/></svg>"""

# ---------------------------------------------------------------------------
# Multi-Language Dictionary (Clean, Professional, Zero Emojis)
# ---------------------------------------------------------------------------

I18N = {
    'ar': {
        'page_title': 'Global Web Checkout',
        'amount_title': 'حدد مبلغ الإيداع',
        'amount_subtitle': 'أدخل المبلغ بالدولار الذي ترغب في شحنه لحسابك للمتابعة.',
        'btn_continue': 'متابعة لاختيار وسيلة الدفع',
        'tab_crypto': 'العملات الرقمية (Cryptocurrency)',
        'tab_local': 'المدفوعات الفورية (Instant Pay)',
        'banner_title': 'طرق الإيداع المباشر',
        'banner_desc': 'قم بالتحويل إلى العنوان أو المعرّف الموضح، ثم أدخل رقم المعاملة (TxID) للتأكيد الفوري.',
        'cur_bal': 'الرصيد المتاح',
        'step_1_title': '1. اختر وسيلة الدفع والشبكة:',
        'step_2_title': '2. تفاصيل التحويل والتأكيد:',
        'locked_amt_label': 'المبلغ المطلوب دفعه:',
        'btn_edit_amt': 'تغيير المبلغ',
        'timestamp_note': 'نظام التحقق نشط من وقت تحديد المبلغ:',
        'addr_label': 'عنوان المحفظة / معرّف الدفع:',
        'copy_btn': 'نسخ',
        'copied_msg': 'تم النسخ بنجاح',
        'txid_label': 'رقم المعاملة / Order ID أو TxID:',
        'txid_placeholder': 'الصق رقم المعاملة أو الهاش هنا...',
        'confirm_btn': 'تأكيد الدفع وإضافة الرصيد فوراً',
        'bot_redirect_msg': 'سيتم فتح تطبيق الفاتورة في تليجرام تلقائياً لإتمام الدفع بضغطة زر واحدة.',
        'bot_pay_btn': 'فتح الفاتورة والدفع الآن',
        'return_btn': 'العودة إلى البوت في تليجرام',
        'succ_title': 'تم شحن الرصيد بنجاح',
        'succ_desc': 'تمت إضافة الرصيد إلى حسابك فوراً وبشكل تلقائي',
        'succ_return': 'فتح البوت ومتابعة التسوق',
        'warning_trc20': 'تأكد من التحويل عبر شبكة Tron (TRC20) حصراً لتفادي ضياع الأموال.',
        'warning_bep20': 'تأكد من التحويل عبر شبكة BNB Smart Chain (BEP20) فقط.',
        'warning_ton': 'أرسل عملة TON إلى العنوان أدناه عبر شبكة TON Net.',
        'warning_binance': 'افتح تطبيق بينانس > Pay > إرسال إلى المعرّف (Pay ID) أدناه.',
        'warning_ltc': 'أرسل Litecoin (LTC) إلى العنوان أدناه.',
        'verifying_msg': 'جاري التحقق من المعاملة في الشبكة...',
        'creating_inv': 'جاري إنشاء الفاتورة...',
        'min_dep_err': 'الحد الأدنى للشحن هو $',
        'invalid_txid_err': 'يرجى إدخال معرّف التحويل / TxID بشكل صحيح',
    },
    'en': {
        'page_title': 'Global Web Checkout',
        'amount_title': 'Select Deposit Amount',
        'amount_subtitle': 'Enter the amount in USD you wish to credit to your balance.',
        'btn_continue': 'Continue to Payment Methods',
        'tab_crypto': 'Cryptocurrency',
        'tab_local': 'Instant Payments',
        'banner_title': 'Instant Deposit Method',
        'banner_desc': 'Transfer funds to the address shown below, then enter the Transaction Hash (TxID) for instant credit.',
        'cur_bal': 'Available Balance',
        'step_1_title': '1. Select Payment Method & Network:',
        'step_2_title': '2. Transfer Details & Confirmation:',
        'locked_amt_label': 'Amount to Pay:',
        'btn_edit_amt': 'Change Amount',
        'timestamp_note': 'Automatic verification active from:',
        'addr_label': 'Wallet Address / Pay ID:',
        'copy_btn': 'Copy',
        'copied_msg': 'Copied to clipboard',
        'txid_label': 'Transaction Hash / Order ID (TxID):',
        'txid_placeholder': 'Paste transaction hash or ID here...',
        'confirm_btn': 'Confirm Payment & Credit Balance',
        'bot_redirect_msg': 'The Telegram invoice will open automatically to complete payment with 1-click.',
        'bot_pay_btn': 'Open Invoice & Pay Now',
        'return_btn': 'Return to Telegram Bot',
        'succ_title': 'Deposit Successful',
        'succ_desc': 'Funds have been credited directly to your Telegram account',
        'succ_return': 'Open Bot & Continue Shopping',
        'warning_trc20': 'Make sure to transfer via Tron (TRC20) network only to prevent loss of funds.',
        'warning_bep20': 'Make sure to transfer via BNB Smart Chain (BEP20) network only.',
        'warning_ton': 'Send TON cryptocurrency to the address below via TON Net.',
        'warning_binance': 'Open Binance app > Pay > Send to the Pay ID below.',
        'warning_ltc': 'Send Litecoin (LTC) to the address below.',
        'verifying_msg': 'Verifying transaction on-chain...',
        'creating_inv': 'Generating invoice...',
        'min_dep_err': 'Minimum deposit amount is $',
        'invalid_txid_err': 'Please enter a valid Transaction Hash / TxID',
    },
    'ru': {
        'page_title': 'Global Web Checkout',
        'amount_title': 'Укажите сумму пополнения',
        'amount_subtitle': 'Введите сумму в USD, которую вы хотите зачислить на свой баланс.',
        'btn_continue': 'Перейти к способам оплаты',
        'tab_crypto': 'Криптовалюта',
        'tab_local': 'Мгновенная оплата',
        'banner_title': 'Метод мгновенного пополнения',
        'banner_desc': 'Переведите средства на указанный адрес и введите TxID для мгновенного зачисления.',
        'cur_bal': 'Доступный баланс',
        'step_1_title': '1. Выберите способ оплаты и сеть:',
        'step_2_title': '2. Реквизиты перевода и подтверждение:',
        'locked_amt_label': 'Сумма к оплате:',
        'btn_edit_amt': 'Изменить сумму',
        'timestamp_note': 'Автоматическая проверка активна с:',
        'addr_label': 'Адрес кошелька / Pay ID:',
        'copy_btn': 'Копировать',
        'copied_msg': 'Скопировано в буфер',
        'txid_label': 'Hash транзакции / Order ID (TxID):',
        'txid_placeholder': 'Вставьте Hash транзакции сюда...',
        'confirm_btn': 'Подтвердить оплату и пополнить баланс',
        'bot_redirect_msg': 'Счет Telegram откроется автоматически для оплаты в 1 клик.',
        'bot_pay_btn': 'Открыть счет и оплатить',
        'return_btn': 'Вернуться в Telegram бот',
        'succ_title': 'Баланс успешно пополнен',
        'succ_desc': 'Средства моментально зачислены на ваш баланс в Telegram',
        'succ_return': 'Открыть бот и продолжить покупки',
        'warning_trc20': 'Переводите только через сеть Tron (TRC20) во избежание потери средств.',
        'warning_bep20': 'Переводите только через сеть BNB Smart Chain (BEP20).',
        'warning_ton': 'Отправьте TON на указанный ниже адрес сети TON Net.',
        'warning_binance': 'Откройте приложение Binance > Pay > Отправить на Pay ID ниже.',
        'warning_ltc': 'Отправьте Litecoin (LTC) на указанный адрес.',
        'verifying_msg': 'Проверка транзакции в блокчейне...',
        'creating_inv': 'Создание счета...',
        'min_dep_err': 'Минимальная сумма пополнения: $',
        'invalid_txid_err': 'Пожалуйста, укажите корректный TxID/Hash',
    },
    'fr': {
        'page_title': 'Global Web Checkout',
        'amount_title': 'Montant du Dépôt',
        'amount_subtitle': 'Saisissez le montant en USD que vous souhaitez créditer sur votre compte.',
        'btn_continue': 'Continuer vers les modes de paiement',
        'tab_crypto': 'Crypto-monnaie',
        'tab_local': 'Paiements Instantanés',
        'banner_title': 'Méthode de Dépôt Instantané',
        'banner_desc': 'Transférez les fonds à l\'adresse indiquée ci-dessous, puis saisissez le hash de transaction (TxID).',
        'cur_bal': 'Solde Disponible',
        'step_1_title': '1. Sélectionnez le Mode de Paiement & Réseau :',
        'step_2_title': '2. Détails du Transfert & Confirmation :',
        'locked_amt_label': 'Montant à payer :',
        'btn_edit_amt': 'Modifier',
        'timestamp_note': 'Vérification active depuis :',
        'addr_label': 'Adresse du Portefeuille / Pay ID :',
        'copy_btn': 'Copier',
        'copied_msg': 'Copié dans le presse-papiers',
        'txid_label': 'Hash de Transaction / Order ID (TxID) :',
        'txid_placeholder': 'Collez le hash de transaction ici...',
        'confirm_btn': 'Confirmer le Paiement & Créditer le Solde',
        'bot_redirect_msg': 'La facture Telegram s\'ouvrira automatiquement pour payer en 1 clic.',
        'bot_pay_btn': 'Ouvrir la Facture & Payer',
        'return_btn': 'Retourner au Bot Telegram',
        'succ_title': 'Dépôt Réussi',
        'succ_desc': 'Les fonds ont été immédiatement crédités sur votre compte Telegram',
        'succ_return': 'Ouvrir le Bot & Continuer les Achats',
        'warning_trc20': 'Assurez-vous de transférer via le réseau Tron (TRC20) uniquement.',
        'warning_bep20': 'Assurez-vous de transférer via le réseau BNB Smart Chain (BEP20) uniquement.',
        'warning_ton': 'Envoyez des TON à l\'adresse ci-dessous via le réseau TON Net.',
        'warning_binance': 'Ouvrez l\'application Binance > Pay > Envoyez au Pay ID ci-dessous.',
        'warning_ltc': 'Envoyez du Litecoin (LTC) à l\'adresse ci-dessous.',
        'verifying_msg': 'Vérification de la transaction sur la blockchain...',
        'creating_inv': 'Génération de la facture...',
        'min_dep_err': 'Le montant minimum de dépôt est de $',
        'invalid_txid_err': 'Veuillez saisir un hash de transaction valide (TxID)',
    }
}

COMMON_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    :root {
        --bg-main: #0B0E14;
        --bg-card: #141824;
        --bg-card-hover: #182030;
        --border: #1E2638;
        --border-active: #00C087;
        --primary: #1D64F2;
        --accent: #00C087;
        --accent-glow: rgba(0, 192, 135, 0.22);
        --text-main: #F9FAFB;
        --text-muted: #8E99A8;
        --font: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: var(--font);
        background-color: var(--bg-main);
        color: var(--text-main);
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .badge-trc20 { background: rgba(239, 68, 68, 0.12); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.25); }
    .badge-bep20 { background: rgba(245, 158, 11, 0.12); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.25); }
    .badge-ton { background: rgba(0, 136, 204, 0.12); color: #38BDF8; border: 1px solid rgba(0, 136, 204, 0.25); }
    .badge-ltc { background: rgba(148, 163, 184, 0.12); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.25); }
    .badge-binance { background: rgba(243, 186, 47, 0.12); color: #F3BA2F; border: 1px solid rgba(243, 186, 47, 0.25); }
    .badge-bot { background: rgba(42, 171, 238, 0.12); color: #2AABEE; border: 1px solid rgba(42, 171, 238, 0.25); }
    .badge-rocket { background: rgba(255, 92, 0, 0.12); color: #FB923C; border: 1px solid rgba(255, 92, 0, 0.25); }
    .badge-success { background: rgba(0, 192, 135, 0.15); color: #00C087; border: 1px solid rgba(0, 192, 135, 0.3); }
    .badge-pending { background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-danger { background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 13px 20px;
        border-radius: 14px;
        font-size: 0.96rem;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        outline: none;
        text-decoration: none;
    }
    .btn-full { width: 100%; }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: #1852C5; transform: translateY(-1px); }
    .btn-success { background: var(--accent); color: #fff; box-shadow: 0 4px 14px rgba(0, 192, 135, 0.3); }
    .btn-success:hover { background: #00A674; transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0, 192, 135, 0.4); }
    .btn-outline { background: transparent; color: var(--text-main); border: 1px solid var(--border); }
    .btn-outline:hover { background: var(--bg-card-hover); border-color: var(--text-muted); }
    .btn-danger { background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.25); }
    .btn-copy { padding: 6px 12px; font-size: 0.8rem; border-radius: 8px; }
    input, select, textarea {
        background: #0E121B;
        border: 1px solid var(--border);
        color: var(--text-main);
        padding: 13px 16px;
        border-radius: 12px;
        font-family: inherit;
        font-size: 0.95rem;
        width: 100%;
        outline: none;
        transition: border-color 0.2s;
    }
    input:focus, select:focus, textarea:focus { border-color: #3B82F6; }
    .toast {
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #182030;
        color: #fff;
        padding: 12px 20px;
        border-radius: 12px;
        border: 1px solid #2B3A55;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        z-index: 9999;
        display: none;
        font-size: 0.9rem;
        font-weight: 600;
        animation: fadeIn 0.3s;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
"""

# ---------------------------------------------------------------------------
# 1. USER CHECKOUT PAGE RENDERER (Amount-First, Dynamic Filtering, Zero Emojis)
# ---------------------------------------------------------------------------

def render_user_checkout_html(session: dict, settings: dict, store_name: str, bot_username: str = "") -> str:
    user_id = session.get("user_id")
    user_name = session.get("first_name") or session.get("username") or f"User #{user_id}"
    cur_balance = float(session.get("user_current_balance") or 0.0)
    token = session.get("token")
    preset_amount = float(session.get("amount") or 0.0)

    # Determine user's bot language
    raw_lang = (session.get("language") or "en").lower().strip()
    user_lang = raw_lang if raw_lang in I18N else "en"
    page_dir = "rtl" if user_lang == "ar" else "ltr"
    t = I18N[user_lang]

    # Global method toggles from bot settings
    cryptotransfer_enabled = (settings.get("cryptotransfer_enabled", "1") == "1")
    cryptobot_enabled = (settings.get("cryptobot_enabled", "1") == "1") and bool(settings.get("cryptobot_token", "").strip())
    xrocket_enabled = (settings.get("xrocket_enabled", "1") == "1") and bool(settings.get("xrocket_token", "").strip())

    # Direct crypto addresses
    binance_id = settings.get("crypto_addr_binance", "").strip()
    if binance_id.lower() == "not configured":
        binance_id = ""
    usdt_trc20 = (settings.get("crypto_addr_usdt_trc20") or "").strip()
    usdt_bep20 = (settings.get("crypto_addr_usdt_bep20") or settings.get("crypto_addr_usdt") or "").strip()
    ton_addr = settings.get("crypto_addr_ton", "").strip()
    if ton_addr.lower() == "not configured":
        ton_addr = ""
    ltc_addr = settings.get("crypto_addr_ltc", "").strip()
    if ltc_addr.lower() == "not configured":
        ltc_addr = ""

    # Determine enabled status for each method
    methods_status = {
        'usdt_trc20': cryptotransfer_enabled and bool(usdt_trc20),
        'usdt_bep20': cryptotransfer_enabled and bool(usdt_bep20),
        'ton': cryptotransfer_enabled and bool(ton_addr),
        'binance': cryptotransfer_enabled and bool(binance_id),
        'ltc': cryptotransfer_enabled and bool(ltc_addr),
        'cryptobot': cryptobot_enabled,
        'xrocket': xrocket_enabled,
    }

    has_crypto_methods = any([methods_status['usdt_trc20'], methods_status['usdt_bep20'], methods_status['ton'], methods_status['binance'], methods_status['ltc']])
    has_local_methods = any([methods_status['cryptobot'], methods_status['xrocket']])

    # Default selected method
    default_method = 'usdt_trc20'
    for m_k in ['usdt_trc20', 'usdt_bep20', 'binance', 'ton', 'ltc', 'cryptobot', 'xrocket']:
        if methods_status.get(m_k):
            default_method = m_k
            break

    min_dep = float(settings.get("min_deposit_amount", "1.0") or 1.0)
    default_amt = preset_amount if preset_amount > 0 else 10.0
    tg_return_url = f"https://t.me/{bot_username}" if bot_username else "tg://resolve"

    i18n_json = json.dumps(I18N, ensure_ascii=False)
    enabled_json = json.dumps(methods_status)

    return f"""<!DOCTYPE html>
<html lang="{user_lang}" dir="{page_dir}">
<head>
    {COMMON_HEAD}
    <title>{t['page_title']} | {html.escape(store_name)}</title>
    <style>
        .container {{
            max-width: 500px;
            width: 100%;
            margin: 0 auto;
            padding: 20px 16px 40px;
            flex: 1;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .brand-logo {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.15rem;
            font-weight: 800;
            color: #fff;
        }}
        .brand-icon {{
            color: #60A5FA;
            display: flex;
            align-items: center;
        }}
        .lang-switch {{
            display: flex;
            background: #101522;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 3px;
            gap: 3px;
        }}
        .lang-pill {{
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.74rem;
            font-weight: 700;
            background: transparent;
            color: var(--text-muted);
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .lang-pill.active {{
            background: #182030;
            color: #fff;
        }}
        .amount-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.4);
            margin-bottom: 20px;
        }}
        .amount-card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 18px;
        }}
        .amount-card-icon {{
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: rgba(29, 100, 242, 0.15);
            color: #60A5FA;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .amount-card-header h1 {{
            font-size: 1.15rem;
            font-weight: 800;
            color: #fff;
            margin-bottom: 2px;
        }}
        .amount-card-header p {{
            font-size: 0.84rem;
            color: var(--text-muted);
        }}
        .amount-row {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin-bottom: 16px;
        }}
        .amt-btn {{
            background: #10141E;
            border: 1px solid var(--border);
            color: #fff;
            padding: 11px 4px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }}
        .amt-btn.active, .amt-btn:hover {{
            background: rgba(29, 100, 242, 0.18);
            border-color: #3B82F6;
            color: #60A5FA;
        }}
        .input-wrap {{
            position: relative;
            margin-bottom: 20px;
        }}
        .input-wrap input {{
            font-size: 1.25rem;
            font-weight: 800;
            padding-left: 36px;
            direction: ltr;
        }}
        .currency-prefix {{
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-weight: 800;
            font-size: 1.15rem;
        }}
        .locked-banner {{
            background: #0E1626;
            border: 1px solid #1D2D49;
            border-radius: 14px;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .locked-banner .lbl {{
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-bottom: 2px;
        }}
        .locked-banner .val {{
            font-size: 1.3rem;
            font-weight: 900;
            color: var(--accent);
        }}
        .btn-change-amt {{
            background: rgba(29, 100, 242, 0.15);
            border: 1px solid rgba(29, 100, 242, 0.35);
            color: #60A5FA;
            padding: 7px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
        }}
        .btn-change-amt:hover {{
            background: rgba(29, 100, 242, 0.25);
        }}
        .timestamp-badge {{
            background: rgba(0, 192, 135, 0.08);
            border: 1px solid rgba(0, 192, 135, 0.25);
            color: #00C087;
            padding: 9px 14px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .top-filter-bar {{
            background: #10141E;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 5px;
            display: flex;
            gap: 6px;
            margin-bottom: 18px;
        }}
        .top-filter-btn {{
            flex: 1;
            padding: 11px 14px;
            border-radius: 12px;
            font-size: 0.92rem;
            font-weight: 700;
            color: var(--text-muted);
            background: transparent;
            border: 1px solid transparent;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s;
        }}
        .top-filter-btn.active {{
            background: #171E2E;
            border-color: #26334A;
            color: #fff;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .banner-card {{
            background: #111522;
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 22px;
            display: flex;
            align-items: flex-start;
            gap: 14px;
        }}
        .banner-icon {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            background: #1D64F2;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 4px 14px rgba(29, 100, 242, 0.35);
        }}
        .banner-info h2 {{
            font-size: 1.12rem;
            font-weight: 800;
            color: #fff;
            margin-bottom: 4px;
            letter-spacing: -0.01em;
        }}
        .banner-info p {{
            font-size: 0.84rem;
            color: var(--text-muted);
            line-height: 1.45;
        }}
        .step-label {{
            font-size: 1.02rem;
            font-weight: 800;
            color: #fff;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 9px;
        }}
        .step-num {{
            background: #1D64F2;
            color: #fff;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.78rem;
            font-weight: 800;
            flex-shrink: 0;
        }}
        .grid-methods {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 22px;
        }}
        .method-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 20px 12px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            cursor: pointer;
            position: relative;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
        }}
        .method-card:hover {{
            background: var(--bg-card-hover);
            border-color: #2B374E;
            transform: translateY(-2px);
        }}
        .method-card.selected {{
            border: 2px solid var(--border-active);
            background: #0D1C1E;
            box-shadow: 0 0 20px var(--accent-glow);
        }}
        .check-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--accent);
            color: #fff;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 900;
        }}
        html[dir="rtl"] .check-badge {{
            right: auto;
            left: 10px;
        }}
        .method-card.selected .check-badge {{ display: flex; }}
        .coin-icon {{ margin-bottom: 8px; }}
        .coin-name {{
            font-size: 1.05rem;
            font-weight: 800;
            color: #fff;
            margin-bottom: 6px;
        }}
        .detail-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 22px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.4);
        }}
        .warning-pill {{
            background: rgba(245, 158, 11, 0.08);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #FBBF24;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 0.82rem;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .address-box {{
            background: #0A0E17;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            gap: 10px;
        }}
        .address-val {{
            font-family: monospace;
            font-size: 0.88rem;
            font-weight: 700;
            color: #fff;
            word-break: break-all;
            direction: ltr;
            text-align: left;
        }}
        .qr-wrapper {{
            text-align: center;
            margin: 16px 0;
        }}
        .qr-wrapper img {{
            border-radius: 14px;
            background: #fff;
            padding: 8px;
            max-width: 170px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.5);
        }}
    </style>
</head>
<body>
    <div class="container" id="main-portal">
        <!-- HEADER TOP & LANGUAGE SWITCHER -->
        <div class="header-top">
            <div class="brand-logo">
                <span class="brand-icon">{SVG_GLOBE}</span>
                <span>{html.escape(store_name)}</span>
            </div>
            <div class="lang-switch">
                <button class="lang-pill {'active' if user_lang == 'ar' else ''}" onclick="switchLang('ar')">AR</button>
                <button class="lang-pill {'active' if user_lang == 'en' else ''}" onclick="switchLang('en')">EN</button>
                <button class="lang-pill {'active' if user_lang == 'ru' else ''}" onclick="switchLang('ru')">RU</button>
                <button class="lang-pill {'active' if user_lang == 'fr' else ''}" onclick="switchLang('fr')">FR</button>
            </div>
        </div>

        <!-- ================= STAGE 1: AMOUNT ENTRY (INITIAL VIEW ONLY) ================= -->
        <div id="phase-amount">
            <div class="amount-card">
                <div class="amount-card-header">
                    <div class="amount-card-icon">{SVG_WALLET}</div>
                    <div>
                        <h1 id="txt-amount-title">{t['amount_title']}</h1>
                        <p id="txt-amount-subtitle">{t['amount_subtitle']}</p>
                    </div>
                </div>

                <div class="amount-row">
                    <button class="amt-btn {'active' if default_amt == 5 else ''}" onclick="pickAmt(5)">$5</button>
                    <button class="amt-btn {'active' if default_amt == 10 else ''}" onclick="pickAmt(10)">$10</button>
                    <button class="amt-btn {'active' if default_amt == 25 else ''}" onclick="pickAmt(25)">$25</button>
                    <button class="amt-btn {'active' if default_amt == 50 else ''}" onclick="pickAmt(50)">$50</button>
                    <button class="amt-btn {'active' if default_amt == 100 else ''}" onclick="pickAmt(100)">$100</button>
                </div>

                <div class="input-wrap">
                    <span class="currency-prefix">$</span>
                    <input type="number" id="charge-amt" min="{min_dep}" step="0.5" value="{default_amt}">
                </div>

                <button class="btn btn-primary btn-full" onclick="proceedToPayment()">
                    <span id="txt-btn-continue">{t['btn_continue']}</span>
                    <span>{SVG_ARROW_RIGHT}</span>
                </button>
            </div>

            <div style="text-align:center; margin-top:20px;">
                <a href="{tg_return_url}" class="btn btn-outline btn-full">
                    <span>{SVG_ARROW_LEFT}</span> <span id="txt-return-btn-p1">{t['return_btn']}</span>
                </a>
            </div>
        </div>

        <!-- ================= STAGE 2: PAYMENT METHODS & DETAILS (UNLOCKED AFTER AMOUNT) ================= -->
        <div id="phase-payment" style="display:none;">
            <!-- LOCKED AMOUNT BAR WITH EDIT BUTTON -->
            <div class="locked-banner">
                <div>
                    <div class="lbl" id="txt-locked-amt-lbl">{t['locked_amt_label']}</div>
                    <div class="val" id="disp-locked-amt">${default_amt:.2f} USD</div>
                </div>
                <button class="btn-change-amt" onclick="backToAmount()" id="txt-btn-edit-amt">
                    {t['btn_edit_amt']}
                </button>
            </div>

            <!-- TIMESTAMP BADGE (NO EMOJIS, CLEAN SHIELD SVG) -->
            <div class="timestamp-badge" id="timestamp-info">
                <span>{SVG_SHIELD}</span>
                <span id="txt-timestamp-note">{t['timestamp_note']}</span>
                <strong id="disp-confirmed-time" style="direction:ltr; display:inline-block; margin:0 4px;">--:--:--</strong>
            </div>

            <!-- CATEGORY TABS (HIDDEN IF NO LOCAL METHODS) -->
            <div class="top-filter-bar" id="category-tabs-bar" style="{'display:none;' if not (has_crypto_methods and has_local_methods) else ''}">
                <button class="top-filter-btn active" id="f-crypto" onclick="filterCategory('crypto')">
                    <span>{SVG_LIGHTNING}</span> <span id="txt-tab-crypto">{t['tab_crypto']}</span>
                </button>
                <button class="top-filter-btn" id="f-local" onclick="filterCategory('local')">
                    <span>{SVG_PLANE}</span> <span id="txt-tab-local">{t['tab_local']}</span>
                </button>
            </div>

            <!-- BANNER CARD -->
            <div class="banner-card">
                <div class="banner-icon">{SVG_LIGHTNING}</div>
                <div class="banner-info">
                    <h2 id="txt-banner-title">{t['banner_title']}</h2>
                    <p id="txt-banner-desc">{t['banner_desc']}</p>
                </div>
            </div>

            <!-- STEP 1: SELECT METHOD -->
            <div class="step-label">
                <span class="step-num">1</span> <span id="txt-step-1-title">{t['step_1_title']}</span>
            </div>

            <!-- DYNAMIC PAYMENT METHOD CARDS (ONLY ENABLED ONES ARE SHOWN) -->
            <div class="grid-methods" id="methods-grid">
                <!-- 1. USDT TRC20 -->
                <div class="method-card {'selected' if default_method == 'usdt_trc20' else ''}" data-cat="crypto" id="card-usdt_trc20" style="{'display:flex;' if methods_status['usdt_trc20'] else 'display:none;'}" onclick="selectMethod('usdt_trc20')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_USDT}</div>
                    <div class="coin-name">USDT</div>
                    <span class="badge badge-trc20">{SVG_BADGE_TRON} TRC20</span>
                </div>

                <!-- 2. USDT BEP20 -->
                <div class="method-card {'selected' if default_method == 'usdt_bep20' else ''}" data-cat="crypto" id="card-usdt_bep20" style="{'display:flex;' if methods_status['usdt_bep20'] else 'display:none;'}" onclick="selectMethod('usdt_bep20')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_USDT}</div>
                    <div class="coin-name">USDT</div>
                    <span class="badge badge-bep20">{SVG_BADGE_BNB} BEP20</span>
                </div>

                <!-- 3. GRAM / TON -->
                <div class="method-card {'selected' if default_method == 'ton' else ''}" data-cat="crypto" id="card-ton" style="{'display:flex;' if methods_status['ton'] else 'display:none;'}" onclick="selectMethod('ton')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_GRAM_TON}</div>
                    <div class="coin-name">GRAM</div>
                    <span class="badge badge-ton">{SVG_BADGE_TON} TON Net</span>
                </div>

                <!-- 4. BINANCE PAY -->
                <div class="method-card {'selected' if default_method == 'binance' else ''}" data-cat="crypto" id="card-binance" style="{'display:flex;' if methods_status['binance'] else 'display:none;'}" onclick="selectMethod('binance')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_BINANCE}</div>
                    <div class="coin-name">Binance</div>
                    <span class="badge badge-binance">{SVG_BADGE_BINANCE} Pay ID • $0.5</span>
                </div>

                <!-- 5. LITECOIN -->
                <div class="method-card {'selected' if default_method == 'ltc' else ''}" data-cat="crypto" id="card-ltc" style="{'display:flex;' if methods_status['ltc'] else 'display:none;'}" onclick="selectMethod('ltc')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_LTC}</div>
                    <div class="coin-name">Litecoin</div>
                    <span class="badge badge-ltc">{SVG_BADGE_LTC} LTC Net</span>
                </div>

                <!-- 6. CRYPTOBOT (In Local Payments tab, only if enabled) -->
                <div class="method-card {'selected' if default_method == 'cryptobot' else ''}" data-cat="local" id="card-cryptobot" style="display:none;" onclick="selectMethod('cryptobot')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_CRYPTOBOT}</div>
                    <div class="coin-name">CryptoBot</div>
                    <span class="badge badge-bot">Telegram Bot</span>
                </div>

                <!-- 7. XROCKET (In Local Payments tab, only if enabled) -->
                <div class="method-card {'selected' if default_method == 'xrocket' else ''}" data-cat="local" id="card-xrocket" style="display:none;" onclick="selectMethod('xrocket')">
                    <div class="check-badge">{SVG_CHECK}</div>
                    <div class="coin-icon">{SVG_XROCKET}</div>
                    <div class="coin-name">xRocket</div>
                    <span class="badge badge-rocket">Telegram Pay</span>
                </div>
            </div>

            <!-- STEP 2: TRANSFER DETAILS & CONFIRMATION -->
            <div class="step-label">
                <span class="step-num">2</span> <span id="txt-step-2-title">{t['step_2_title']}</span>
            </div>

            <div class="detail-panel">
                <!-- WARNING BANNER -->
                <div class="warning-pill" id="net-warning">
                    <span>{SVG_ALERT}</span>
                    <span id="net-warning-text">{t['warning_trc20']}</span>
                </div>

                <div style="font-size:0.82rem; font-weight:700; color:var(--text-muted); margin-bottom:6px;" id="txt-addr-label">{t['addr_label']}</div>
                <div class="address-box">
                    <span class="address-val" id="disp-address">{html.escape(usdt_trc20 or usdt_bep20 or binance_id or ton_addr or ltc_addr)}</span>
                    <button class="btn btn-outline btn-copy" onclick="copyActiveAddress()" id="txt-copy-btn">
                        <span>{SVG_COPY}</span> <span id="txt-copy-label">{t['copy_btn']}</span>
                    </button>
                </div>

                <div class="qr-wrapper" id="qr-container">
                    <img id="disp-qr" src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={html.escape(usdt_trc20 or usdt_bep20 or binance_id or ton_addr or ltc_addr)}" alt="QR Code">
                </div>

                <div id="blockchain-txid-wrap">
                    <div style="font-size:0.82rem; font-weight:700; color:var(--text-muted); margin-bottom:6px;" id="txt-txid-label">{t['txid_label']}</div>
                    <input type="text" id="input-txid" placeholder="{t['txid_placeholder']}" style="direction:ltr; margin-bottom:16px;">
                    <button class="btn btn-success btn-full" id="btn-confirm-pay" onclick="handleConfirmPayment()">
                        <span>{SVG_LIGHTNING}</span> <span id="txt-btn-confirm-text">{t['confirm_btn']}</span>
                    </button>
                </div>

                <div id="bot-redirect-wrap" style="display:none;">
                    <p style="font-size:0.85rem; color:var(--text-muted); text-align:center; margin-bottom:14px;" id="txt-bot-redirect">
                        {t['bot_redirect_msg']}
                    </p>
                    <button class="btn btn-primary btn-full" id="btn-bot-pay" onclick="handleBotInvoice()">
                        <span>{SVG_PLANE}</span> <span id="txt-btn-bot-text">{t['bot_pay_btn']}</span>
                    </button>
                </div>
            </div>

            <div style="text-align:center; margin-top:20px;">
                <a href="{tg_return_url}" class="btn btn-outline btn-full">
                    <span>{SVG_ARROW_LEFT}</span> <span id="txt-return-btn-p2">{t['return_btn']}</span>
                </a>
            </div>
        </div>
    </div>

    <!-- SUCCESS SCREEN -->
    <div class="container" id="success-screen" style="display:none; text-align:center; padding-top:40px;">
        <div style="width:70px; height:70px; border-radius:50%; background:rgba(0,192,135,0.18); color:var(--accent); display:flex; align-items:center; justify-content:center; margin:0 auto 16px;">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h1 style="color:var(--accent); font-size:1.6rem; font-weight:900; margin-bottom:6px;" id="txt-succ-title">{t['succ_title']}</h1>
        <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:20px;" id="txt-succ-desc">{t['succ_desc']}</p>
        <div class="detail-panel" style="text-align:center;">
            <div style="color:var(--text-muted); font-size:0.85rem;" id="txt-succ-cur-lbl">{t['cur_bal']}</div>
            <div style="font-size:2.4rem; font-weight:900; color:#fff;" id="succ-amt">$0.00</div>
            <div class="badge badge-success" id="succ-txid" style="margin-top:8px;">Completed</div>
        </div>
        <a href="{tg_return_url}" class="btn btn-primary btn-full" id="txt-succ-return">
            {t['succ_return']}
        </a>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const SESSION_TOKEN = "{token}";
        const MIN_DEP = {min_dep};
        const I18N_DICT = {i18n_json};
        const ENABLED_METHODS = {enabled_json};
        let currentLang = "{user_lang}";
        
        let amountConfirmedTimestamp = Math.floor(Date.now() / 1000);
        let lockedAmount = {default_amt};
        let activeMethod = "{default_method}";

        const METHODS = {{
            'usdt_trc20': {{
                name: 'USDT TRC20',
                addr: '{html.escape(usdt_trc20)}',
                warningKey: 'warning_trc20',
                isBot: false,
                coinCode: 'USDT_TRC20'
            }},
            'usdt_bep20': {{
                name: 'USDT BEP20',
                addr: '{html.escape(usdt_bep20)}',
                warningKey: 'warning_bep20',
                isBot: false,
                coinCode: 'USDT'
            }},
            'ton': {{
                name: 'TON / GRAM',
                addr: '{html.escape(ton_addr)}',
                warningKey: 'warning_ton',
                isBot: false,
                coinCode: 'TON'
            }},
            'binance': {{
                name: 'Binance Pay ID',
                addr: '{html.escape(binance_id)}',
                warningKey: 'warning_binance',
                isBot: false,
                coinCode: 'BINANCE'
            }},
            'ltc': {{
                name: 'Litecoin',
                addr: '{html.escape(ltc_addr)}',
                warningKey: 'warning_ltc',
                isBot: false,
                coinCode: 'LTC'
            }},
            'cryptobot': {{
                name: 'CryptoBot',
                addr: '',
                isBot: true,
                botType: 'cryptobot'
            }},
            'xrocket': {{
                name: 'xRocket',
                addr: '',
                isBot: true,
                botType: 'xrocket'
            }}
        }};

        function t(key) {{
            const langData = I18N_DICT[currentLang] || I18N_DICT['en'];
            return langData[key] || I18N_DICT['en'][key] || key;
        }}

        function updateConfirmedTimeDisplay() {{
            const d = new Date(amountConfirmedTimestamp * 1000);
            const timeStr = d.toLocaleTimeString();
            document.getElementById('disp-confirmed-time').textContent = timeStr;
        }}

        function switchLang(lang) {{
            if (!I18N_DICT[lang]) return;
            currentLang = lang;
            const dir = (lang === 'ar') ? 'rtl' : 'ltr';
            document.documentElement.dir = dir;
            document.documentElement.lang = lang;

            document.querySelectorAll('.lang-pill').forEach(p => p.classList.remove('active'));
            const p = document.querySelector('.lang-pill:nth-child(' + (lang === 'ar' ? 1 : lang === 'en' ? 2 : lang === 'ru' ? 3 : 4) + ')');
            if (p) p.classList.add('active');

            // Text elements in Stage 1
            document.getElementById('txt-amount-title').textContent = t('amount_title');
            document.getElementById('txt-amount-subtitle').textContent = t('amount_subtitle');
            document.getElementById('txt-btn-continue').textContent = t('btn_continue');
            document.getElementById('txt-return-btn-p1').textContent = t('return_btn');

            // Text elements in Stage 2
            document.getElementById('txt-tab-crypto').textContent = t('tab_crypto');
            document.getElementById('txt-tab-local').textContent = t('tab_local');
            document.getElementById('txt-banner-title').textContent = t('banner_title');
            document.getElementById('txt-banner-desc').textContent = t('banner_desc');
            document.getElementById('txt-step-1-title').textContent = t('step_1_title');
            document.getElementById('txt-step-2-title').textContent = t('step_2_title');
            document.getElementById('txt-locked-amt-lbl').textContent = t('locked_amt_label');
            document.getElementById('txt-btn-edit-amt').textContent = t('btn_edit_amt');
            document.getElementById('txt-timestamp-note').textContent = t('timestamp_note');
            document.getElementById('txt-addr-label').textContent = t('addr_label');
            document.getElementById('txt-copy-label').textContent = t('copy_btn');
            document.getElementById('txt-txid-label').textContent = t('txid_label');
            document.getElementById('input-txid').placeholder = t('txid_placeholder');
            document.getElementById('txt-btn-confirm-text').textContent = t('confirm_btn');
            document.getElementById('txt-bot-redirect').textContent = t('bot_redirect_msg');
            document.getElementById('txt-btn-bot-text').textContent = t('bot_pay_btn');
            document.getElementById('txt-return-btn-p2').textContent = t('return_btn');
            document.getElementById('txt-succ-title').textContent = t('succ_title');
            document.getElementById('txt-succ-desc').textContent = t('succ_desc');
            document.getElementById('txt-succ-return').textContent = t('succ_return');

            const m = METHODS[activeMethod];
            if (m && m.warningKey) {{
                document.getElementById('net-warning-text').textContent = t(m.warningKey);
            }}
        }}

        function showToast(msg) {{
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.style.display = 'block';
            setTimeout(() => {{ toast.style.display = 'none'; }}, 3000);
        }}

        function pickAmt(val) {{
            document.getElementById('charge-amt').value = val;
            document.querySelectorAll('.amt-btn').forEach(b => {{
                if (b.textContent.trim() === '$' + val) b.classList.add('active');
                else b.classList.remove('active');
            }});
        }}

        function proceedToPayment() {{
            const val = parseFloat(document.getElementById('charge-amt').value) || 0;
            if (val < MIN_DEP) {{
                showToast(t('min_dep_err') + MIN_DEP);
                return;
            }}
            lockedAmount = val;
            amountConfirmedTimestamp = Math.floor(Date.now() / 1000);
            
            document.getElementById('disp-locked-amt').textContent = '$' + lockedAmount.toFixed(2) + ' USD';
            updateConfirmedTimeDisplay();

            // Transition from Stage 1 to Stage 2
            document.getElementById('phase-amount').style.display = 'none';
            document.getElementById('phase-payment').style.display = 'block';
            
            // Auto select first enabled method
            selectMethod(activeMethod);
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function backToAmount() {{
            document.getElementById('phase-payment').style.display = 'none';
            document.getElementById('phase-amount').style.display = 'block';
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function filterCategory(cat) {{
            document.querySelectorAll('.top-filter-btn').forEach(b => b.classList.remove('active'));
            if (cat === 'crypto') document.getElementById('f-crypto').classList.add('active');
            else document.getElementById('f-local').classList.add('active');

            let firstFound = null;
            document.querySelectorAll('.method-card').forEach(card => {{
                const methodId = card.id.replace('card-', '');
                const isEnabled = ENABLED_METHODS[methodId];
                if (card.dataset.cat === cat && isEnabled) {{
                    card.style.display = 'flex';
                    if (!firstFound) firstFound = methodId;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            if (firstFound) selectMethod(firstFound);
        }}

        function selectMethod(key) {{
            activeMethod = key;
            document.querySelectorAll('.method-card').forEach(c => c.classList.remove('selected'));
            const selectedCard = document.getElementById('card-' + key);
            if (selectedCard) selectedCard.classList.add('selected');

            const m = METHODS[key];
            if (!m) return;

            const qrWrap = document.getElementById('qr-container');
            const addrWrap = document.querySelector('.address-box');
            const warnWrap = document.getElementById('net-warning');
            const warnText = document.getElementById('net-warning-text');
            const bcWrap = document.getElementById('blockchain-txid-wrap');
            const botWrap = document.getElementById('bot-redirect-wrap');

            if (m.isBot) {{
                qrWrap.style.display = 'none';
                addrWrap.style.display = 'none';
                warnWrap.style.display = 'none';
                bcWrap.style.display = 'none';
                botWrap.style.display = 'block';
            }} else {{
                qrWrap.style.display = 'block';
                addrWrap.style.display = 'flex';
                warnWrap.style.display = 'flex';
                warnText.textContent = t(m.warningKey);
                bcWrap.style.display = 'block';
                botWrap.style.display = 'none';

                document.getElementById('disp-address').textContent = m.addr || 'N/A';
                if (m.addr) {{
                    document.getElementById('disp-qr').src = 'https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=' + encodeURIComponent(m.addr);
                }}
            }}
        }}

        function copyActiveAddress() {{
            const m = METHODS[activeMethod];
            if (!m || !m.addr) return;
            navigator.clipboard.writeText(m.addr).then(() => {{
                showToast(t('copied_msg'));
            }}).catch(() => {{
                showToast("Copy error");
            }});
        }}

        async function handleConfirmPayment() {{
            const txid = (document.getElementById('input-txid').value || '').trim();
            const amt = lockedAmount;
            const m = METHODS[activeMethod];

            if (amt < MIN_DEP) {{
                showToast(t('min_dep_err') + MIN_DEP);
                return;
            }}
            if (!txid || txid.length < 4) {{
                showToast(t('invalid_txid_err'));
                return;
            }}

            const btn = document.getElementById('btn-confirm-pay');
            const origText = btn.innerHTML;
            btn.disabled = true;
            btn.textContent = t('verifying_msg');

            try {{
                const res = await fetch('/api/pay/verify-transaction', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        token: SESSION_TOKEN,
                        coin: m.coinCode,
                        txid: txid,
                        amount: amt,
                        start_time: amountConfirmedTimestamp
                    }})
                }});
                const data = await res.json();
                if (data.ok && data.status === 'completed') {{
                    document.getElementById('main-portal').style.display = 'none';
                    document.getElementById('succ-amt').textContent = '$' + (data.amount || amt).toFixed(2);
                    document.getElementById('succ-txid').textContent = 'TxID: ' + txid;
                    document.getElementById('success-screen').style.display = 'block';
                }} else if (data.ok && data.status === 'pending') {{
                    showToast(data.message || "Transaction received, verifying...");
                }} else {{
                    showToast(data.error || "Verification failed");
                }}
            }} catch(e) {{
                showToast("Server connection error");
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = origText;
            }}
        }}

        async function handleBotInvoice() {{
            const amt = lockedAmount;
            if (amt < MIN_DEP) {{
                showToast(t('min_dep_err') + MIN_DEP);
                return;
            }}
            const btn = document.getElementById('btn-bot-pay');
            btn.disabled = true;
            btn.textContent = t('creating_inv');

            const endpoint = (activeMethod === 'xrocket') ? '/api/pay/create-xrocket' : '/api/pay/create-cryptobot';
            try {{
                const res = await fetch(endpoint, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        token: SESSION_TOKEN,
                        amount: amt
                    }})
                }});
                const data = await res.json();
                if (data.ok && data.pay_url) {{
                    window.location.href = data.pay_url;
                }} else {{
                    showToast(data.error || "Failed to create invoice");
                }}
            }} catch(e) {{
                showToast("Connection error");
            }} finally {{
                btn.disabled = false;
                btn.textContent = t('bot_pay_btn');
            }}
        }}

        // Initialize state
        updateConfirmedTimeDisplay();
        selectMethod(activeMethod);
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# 2. ADMIN PANEL RENDERER
# ---------------------------------------------------------------------------

def render_admin_login_html(error: str = None) -> str:
    err_box = f'<div style="background:rgba(239,68,68,0.15); border:1px solid #EF4444; color:#EF4444; padding:12px; border-radius:10px; margin-bottom:16px; font-size:0.9rem;">{html.escape(error)}</div>' if error else ''
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    {COMMON_HEAD}
    <title>Admin Portal Login | تسجيل الدخول</title>
    <style>
        .login-wrap {{ max-width: 400px; width: 100%; margin: auto; padding: 24px; }}
        .card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 30px 24px; text-align: center; }}
    </style>
</head>
<body>
    <div class="login-wrap">
        <div class="card">
            <div style="font-size:2rem; margin-bottom:12px; color:#1D64F2;">{SVG_SHIELD}</div>
            <h1 style="font-size:1.3rem; margin-bottom:6px;">لوحة تحكم الدفع (الأدمن)</h1>
            <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:20px;">أدخل الرمز السري للأدمن للوصول إلى لوحة التحكم</p>
            {err_box}
            <form method="GET" action="/admin/web">
                <input type="password" name="key" placeholder="Admin Secret Key" style="direction:ltr; text-align:center; margin-bottom:16px;" required>
                <button type="submit" class="btn btn-primary" style="width:100%;">دخول اللوحة</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

def render_admin_dashboard_html(stats: dict, settings: dict, payments: list, total_count: int, admin_key: str, store_name: str) -> str:
    total_volume = float(stats.get("total_volume") or 0.0)
    completed_tx = int(stats.get("completed_tx") or 0)
    pending_tx = int(stats.get("pending_tx") or 0)
    rejected_tx = int(stats.get("rejected_tx") or 0)

    binance_id = settings.get("crypto_addr_binance", "")
    usdt_trc20 = settings.get("crypto_addr_usdt_trc20") or ""
    usdt_bep20 = settings.get("crypto_addr_usdt_bep20") or settings.get("crypto_addr_usdt", "")
    ton_addr = settings.get("crypto_addr_ton", "")
    ltc_addr = settings.get("crypto_addr_ltc", "")
    cryptobot_token = settings.get("cryptobot_token", "")
    xrocket_token = settings.get("xrocket_token", "")
    min_dep = settings.get("min_deposit_amount", "1.0")

    rows_html = ""
    for p in payments:
        status = p.get("status", "pending")
        if status == "completed":
            badge = '<span class="badge badge-success">مكتمل</span>'
        elif status == "pending":
            badge = '<span class="badge badge-pending">معلق</span>'
        else:
            badge = '<span class="badge badge-danger">مرفوض</span>'

        tx_id = html.escape(str(p.get("transaction_id", "")))
        uid = p.get("user_id")
        uname = html.escape(str(p.get("username") or p.get("first_name") or f"User #{uid}"))
        amt = float(p.get("amount") or 0.0)
        method = html.escape(str(p.get("payment_method", "")))
        created_at = html.escape(str(p.get("created_at", "")))

        actions = ""
        if status == "pending":
            actions = f"""
            <div style="display:flex; gap:6px;">
                <button class="btn btn-success btn-copy" onclick="actionPayment('{tx_id}', 'approve')">قبول وشحن</button>
                <button class="btn btn-danger btn-copy" onclick="actionPayment('{tx_id}', 'reject')">رفض</button>
            </div>
            """

        rows_html += f"""
        <tr>
            <td style="font-weight:600; color:#fff;">{tx_id}</td>
            <td><a href="https://t.me/{uname.replace('@','')}" target="_blank" style="color:#60A5FA; text-decoration:none;">{uname}</a> <span style="font-size:0.75rem; color:var(--text-muted);">({uid})</span></td>
            <td><span style="font-weight:700; color:var(--accent);">${amt:.2f}</span></td>
            <td style="font-size:0.8rem; color:var(--text-muted); direction:ltr;">{method}</td>
            <td>{badge}</td>
            <td style="font-size:0.8rem; color:var(--text-muted);">{created_at}</td>
            <td>{actions}</td>
        </tr>
        """

    if not rows_html:
        rows_html = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">لا توجد معاملات مسجلة بعد</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    {COMMON_HEAD}
    <title>لوحة تحكم الدفع والمعاملات (Admin) | {html.escape(store_name)}</title>
    <style>
        .admin-nav {{
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .admin-nav .brand {{
            font-size: 1.15rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .main-wrap {{
            max-width: 1100px;
            width: 100%;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
        }}
        .stat-card .lbl {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px; }}
        .stat-card .val {{ font-size: 1.6rem; font-weight: 800; color: #fff; }}
        .tabs {{
            display: flex;
            gap: 8px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 20px;
            overflow-x: auto;
        }}
        .tab-link {{
            padding: 12px 18px;
            color: var(--text-muted);
            font-weight: 700;
            font-size: 0.95rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .tab-link.active {{ color: #fff; border-bottom-color: var(--primary); }}
        .tab-page {{ display: none; }}
        .tab-page.active {{ display: block; }}
        .table-wrap {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow-x: auto;
        }}
        table {{ width: 100%; border-collapse: collapse; text-align: right; font-size: 0.9rem; }}
        th {{ background: #0E131F; padding: 14px 16px; font-weight: 700; color: var(--text-muted); border-bottom: 1px solid var(--border); }}
        td {{ padding: 14px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:hover td {{ background: var(--bg-card-hover); }}
        .form-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px; }}
        .form-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }}
        .form-group {{ margin-bottom: 14px; }}
        .form-group label {{ display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: #D1D5DB; }}
    </style>
</head>
<body>
    <nav class="admin-nav">
        <div class="brand">
            <span style="color:#1D64F2;">{SVG_SHIELD}</span>
            <span>لوحة تحكم الدفع (الأدمن) | {html.escape(store_name)}</span>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
            <a href="/admin/web" class="btn btn-outline btn-copy">تحديث</a>
            <a href="/admin/web?key=logout" class="btn btn-danger btn-copy">تسجيل خروج</a>
        </div>
    </nav>

    <div class="main-wrap">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="lbl">إجمالي الإيداعات الناجحة</div>
                <div class="val" style="color:var(--accent);">${total_volume:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="lbl">المعاملات المكتملة</div>
                <div class="val">{completed_tx}</div>
            </div>
            <div class="stat-card">
                <div class="lbl">المعاملات المعلقة</div>
                <div class="val" style="color:var(--warning);">{pending_tx}</div>
            </div>
            <div class="stat-card">
                <div class="lbl">المعاملات المرفوضة</div>
                <div class="val" style="color:var(--danger);">{rejected_tx}</div>
            </div>
        </div>

        <div class="tabs">
            <div class="tab-link active" onclick="showTab('tab-tx')">سجل المعاملات ({total_count})</div>
            <div class="tab-link" onclick="showTab('tab-settings')">إدارة بوابات وطرق الدفع</div>
        </div>

        <!-- TRANSACTIONS TAB -->
        <div class="tab-page active" id="tab-tx">
            <div style="display:flex; gap:6px; margin-bottom:14px;">
                <a href="/admin/web?key={admin_key}&status=all" class="btn btn-outline btn-copy">الكل</a>
                <a href="/admin/web?key={admin_key}&status=pending" class="btn btn-outline btn-copy" style="color:var(--warning);">المعلقة</a>
                <a href="/admin/web?key={admin_key}&status=completed" class="btn btn-outline btn-copy" style="color:var(--accent);">الناجحة</a>
                <a href="/admin/web?key={admin_key}&status=rejected" class="btn btn-outline btn-copy" style="color:var(--danger);">المرفوضة</a>
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>رقم المعاملة</th>
                            <th>العميل</th>
                            <th>المبلغ</th>
                            <th>وسيلة الدفع / TxID</th>
                            <th>الحالة</th>
                            <th>التاريخ</th>
                            <th>الإجراءات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- SETTINGS TAB -->
        <div class="tab-page" id="tab-settings">
            <form id="admin-settings-form" onsubmit="saveSettings(event)">
                <div class="form-grid">
                    <div class="form-card">
                        <h3 style="font-size:1.05rem; margin-bottom:16px;">إعدادات Binance Pay</h3>
                        <div class="form-group">
                            <label>Binance Pay ID:</label>
                            <input type="text" name="crypto_addr_binance" value="{html.escape(binance_id)}" placeholder="e.g. 443008971">
                        </div>
                        <div class="form-group">
                            <label>الحد الأدنى للشحن ($):</label>
                            <input type="number" step="0.5" name="min_deposit_amount" value="{html.escape(str(min_dep))}">
                        </div>
                    </div>

                    <div class="form-card">
                        <h3 style="font-size:1.05rem; margin-bottom:16px;">محافظ USDT (TRC20 & BEP20)</h3>
                        <div class="form-group">
                            <label>عنوان محفظة USDT (TRC20):</label>
                            <input type="text" name="crypto_addr_usdt_trc20" value="{html.escape(usdt_trc20)}" placeholder="T...">
                        </div>
                        <div class="form-group">
                            <label>عنوان محفظة USDT (BEP20):</label>
                            <input type="text" name="crypto_addr_usdt_bep20" value="{html.escape(usdt_bep20)}" placeholder="0x...">
                        </div>
                    </div>

                    <div class="form-card">
                        <h3 style="font-size:1.05rem; margin-bottom:16px;">عملات GRAM / TON و Litecoin</h3>
                        <div class="form-group">
                            <label>عنوان محفظة TON / GRAM:</label>
                            <input type="text" name="crypto_addr_ton" value="{html.escape(ton_addr)}" placeholder="UQ...">
                        </div>
                        <div class="form-group">
                            <label>عنوان محفظة Litecoin (LTC):</label>
                            <input type="text" name="crypto_addr_ltc" value="{html.escape(ltc_addr)}" placeholder="L...">
                        </div>
                    </div>

                    <div class="form-card">
                        <h3 style="font-size:1.05rem; margin-bottom:16px;">بوابات الدفع التلقائية (APIs)</h3>
                        <div class="form-group">
                            <label>توكن CryptoBot:</label>
                            <input type="password" name="cryptobot_token" value="{html.escape(cryptobot_token)}" placeholder="API Token from @CryptoBot">
                        </div>
                        <div class="form-group">
                            <label>توكن xRocket:</label>
                            <input type="password" name="xrocket_token" value="{html.escape(xrocket_token)}" placeholder="xRocket API Token">
                        </div>
                    </div>
                </div>

                <div style="text-align: left;">
                    <button type="submit" class="btn btn-primary" id="btn-save-settings">
                        حفظ التعديلات الآن
                    </button>
                </div>
            </form>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        const ADMIN_KEY = "{admin_key}";

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
        }}

        function showTab(tabId) {{
            document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
            if (tabId === 'tab-tx') document.querySelectorAll('.tab-link')[0].classList.add('active');
            else if (tabId === 'tab-settings') document.querySelectorAll('.tab-link')[1].classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }}

        async function actionPayment(txid, action) {{
            if (!confirm("هل أنت متأكد من " + (action === 'approve' ? 'قبول وشحن رصيد العميل' : 'رفض') + " هذه العملية؟")) return;
            try {{
                const res = await fetch('/api/admin/action-payment', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        key: ADMIN_KEY,
                        transaction_id: txid,
                        action: action
                    }})
                }});
                const data = await res.json();
                if (data.ok) {{
                    showToast("تمت العملية بنجاح");
                    setTimeout(() => {{ window.location.reload(); }}, 1000);
                }} else {{
                    showToast(data.error || "فشلت العملية");
                }}
            }} catch(e) {{
                showToast("خطأ في الاتصال");
            }}
        }}

        async function saveSettings(e) {{
            e.preventDefault();
            const btn = document.getElementById('btn-save-settings');
            btn.disabled = true;
            btn.textContent = "جاري الحفظ...";

            const form = document.getElementById('admin-settings-form');
            const formData = new FormData(form);
            const payload = {{ key: ADMIN_KEY }};
            formData.forEach((val, k) => {{ payload[k] = val; }});

            try {{
                const res = await fetch('/api/admin/save-settings', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const data = await res.json();
                if (data.ok) {{
                    showToast("تم حفظ الإعدادات بنجاح");
                }} else {{
                    showToast(data.error || "فشل الحفظ");
                }}
            }} catch(e) {{
                showToast("خطأ في الاتصال");
            }} finally {{
                btn.disabled = false;
                btn.textContent = "حفظ التعديلات الآن";
            }}
        }}
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# 3. HTTP HANDLERS
# ---------------------------------------------------------------------------

async def get_checkout_page(request: web.Request) -> web.Response:
    token = request.match_info.get("token") or request.query.get("token")
    if not token:
        return web.Response(text="Invalid or missing payment token.", status=400)

    from database import get_payment_session, get_setting
    session = await get_payment_session(token)
    if not session:
        return web.Response(
            text="""<div style="font-family:sans-serif; text-align:center; padding:50px; background:#0B0E14; color:#fff; min-height:100vh;">
                <h2>Payment Session Expired</h2>
                <p style="color:#8E99A8;">Please return to the Telegram bot and request a new deposit link.</p>
            </div>""",
            content_type="text/html",
            status=404
        )

    store_name = await get_setting("store_name", "Digital Store")
    settings = {
        "crypto_addr_binance": await get_setting("crypto_addr_binance", ""),
        "crypto_addr_usdt": await get_setting("crypto_addr_usdt", ""),
        "crypto_addr_usdt_trc20": await get_setting("crypto_addr_usdt_trc20", ""),
        "crypto_addr_usdt_bep20": await get_setting("crypto_addr_usdt_bep20", ""),
        "crypto_addr_ton": await get_setting("crypto_addr_ton", ""),
        "crypto_addr_ltc": await get_setting("crypto_addr_ltc", ""),
        "cryptobot_token": await get_setting("cryptobot_token", ""),
        "xrocket_token": await get_setting("xrocket_token", ""),
        "min_deposit_amount": await get_setting("min_deposit_amount", "1.0"),
        "cryptotransfer_enabled": await get_setting("cryptotransfer_enabled", "1"),
        "cryptobot_enabled": await get_setting("cryptobot_enabled", "1"),
        "xrocket_enabled": await get_setting("xrocket_enabled", "1"),
    }

    bot_username = ""
    bot = request.app.get("bot")
    if bot:
        try:
            me = await bot.get_me()
            bot_username = me.username
        except Exception:
            pass

    html_content = render_user_checkout_html(session, settings, store_name, bot_username)
    return web.Response(text=html_content, content_type="text/html")


async def api_verify_payment(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    token = (data.get("token") or "").strip()
    coin = (data.get("coin") or "").strip().upper()
    txid = (data.get("txid") or "").strip()
    try:
        amount = float(data.get("amount") or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    raw_start_time = data.get("start_time")
    try:
        start_time = int(raw_start_time) if raw_start_time else int(time.time())
    except (ValueError, TypeError):
        start_time = int(time.time())

    if not token or not txid or amount <= 0:
        return web.json_response({"ok": False, "error": "Missing required fields"}, status=400)

    from database import get_payment_session, get_payment_by_method, create_payment, complete_payment, reject_payment, get_setting, mark_payment_session_completed, get_user
    session = await get_payment_session(token)
    if not session:
        return web.json_response({"ok": False, "error": "Payment session expired or invalid"}, status=403)

    user_id = session["user_id"]
    payment_method = f"blockchain_{coin}_{txid}"

    existing = await get_payment_by_method(payment_method)
    if existing:
        st = existing["status"]
        if st == "completed":
            return web.json_response({"ok": True, "status": "completed", "amount": existing["amount"]})
        elif st == "pending":
            return web.json_response({"ok": True, "status": "pending", "message": "Transaction is already under verification"})
        elif st == "rejected":
            return web.json_response({"ok": False, "error": "This transaction was previously rejected"}, status=400)

    trans_id = f"GW_{uuid.uuid4().hex[:8].upper()}"
    start_time_utc = datetime.datetime.fromtimestamp(start_time, datetime.timezone.utc)
    created_at_str = start_time_utc.strftime("%Y-%m-%d %H:%M:%S")
    await create_payment(user_id, amount, payment_method, trans_id, created_at=created_at_str)

    from crypto_verifier import verify_crypto_transaction, is_amount_matching
    
    ts_to_pass = None if coin == "BINANCE" else start_time

    if coin in ["USDT_TRC20", "TRC20"]:
        recipient_address = await get_setting("crypto_addr_usdt_trc20", "") or await get_setting("crypto_addr_usdt", "")
        success, result_val = False, "Pending TRC20 verification"
    elif coin in ["USDT_BEP20", "USDT"]:
        recipient_address = await get_setting("crypto_addr_usdt_bep20", "") or await get_setting("crypto_addr_usdt", "")
        success, result_val = await verify_crypto_transaction("USDT", txid, recipient_address, min_timestamp=ts_to_pass)
    elif coin == "BINANCE":
        recipient_address = await get_setting("crypto_addr_binance", "")
        success, result_val = await verify_crypto_transaction("BINANCE", txid, recipient_address, min_timestamp=None)
    else:
        recipient_address = await get_setting(f"crypto_addr_{coin.lower()}", "")
        success, result_val = await verify_crypto_transaction(coin, txid, recipient_address, min_timestamp=ts_to_pass)

    bot = request.app.get("bot")

    if success:
        if not is_amount_matching(amount, result_val, coin):
            await reject_payment(trans_id)
            return web.json_response({"ok": False, "error": f"Amount mismatch: received ${result_val:.2f}, expected ${amount:.2f}"}, status=400)

        comp_res = await complete_payment(trans_id)
        await mark_payment_session_completed(token)

        if bot and comp_res:
            try:
                db_user = await get_user(user_id)
                u_lang = db_user.get("language", "en") if db_user else "en"
                from localization import get_text
                msg_txt = get_text('payment_success', u_lang, amount=amount, new_balance=db_user.get('balance', 0.0) if db_user else amount)
                await bot.send_message(chat_id=user_id, text=f"🌐 Global Web Checkout\n\n{msg_txt}", parse_mode="Markdown")
            except Exception as notify_err:
                logger.warning(f"Could not send Telegram notification for user {user_id}: {notify_err}")

        return web.json_response({"ok": True, "status": "completed", "amount": amount})
    else:
        user_lang = session.get("language", "ar")
        pending_msg = {
            "ar": "تم استلام المعاملة وجاري التحقق من الشبكة وإضافة الرصيد لحسابك تلقائياً.",
            "en": "Transaction received! Verifying on-chain and crediting your balance shortly.",
            "ru": "Транзакция получена! Проверяем в сети и зачисляем средства.",
            "fr": "Transaction reçue ! Vérification sur la blockchain en cours."
        }
        return web.json_response({
            "ok": True,
            "status": "pending",
            "message": pending_msg.get(user_lang, pending_msg["en"])
        })


async def api_create_cryptobot(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    token = (data.get("token") or "").strip()
    try:
        amount = float(data.get("amount") or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    from database import get_payment_session, create_payment
    session = await get_payment_session(token)
    if not session or amount <= 0:
        return web.json_response({"ok": False, "error": "Invalid session or amount"}, status=400)

    from cryptobot_client import create_cryptobot_invoice
    user_id = session["user_id"]
    payload = f"gw_{user_id}_{uuid.uuid4().hex[:6]}"
    inv = await create_cryptobot_invoice(amount, payload, description="Global Web Deposit")
    if inv and inv.get("pay_url"):
        trans_id = f"CB_{inv.get('invoice_id')}"
        await create_payment(user_id, amount, f"cryptobot_{inv.get('invoice_id')}", trans_id)
        return web.json_response({"ok": True, "pay_url": inv["pay_url"]})
    return web.json_response({"ok": False, "error": "CryptoBot token not configured or API error"}, status=500)


async def api_create_xrocket(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    token = (data.get("token") or "").strip()
    try:
        amount = float(data.get("amount") or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    from database import get_payment_session, create_payment
    session = await get_payment_session(token)
    if not session or amount <= 0:
        return web.json_response({"ok": False, "error": "Invalid session or amount"}, status=400)

    from xrocket_client import create_xrocket_invoice
    user_id = session["user_id"]
    payload = f"gw_{user_id}_{uuid.uuid4().hex[:6]}"
    inv = await create_xrocket_invoice(amount, payload, description="Global Web Deposit")
    if inv and inv.get("pay_url"):
        trans_id = f"XR_{inv.get('invoice_id')}"
        await create_payment(user_id, amount, f"xrocket_{inv.get('invoice_id')}", trans_id)
        return web.json_response({"ok": True, "pay_url": inv["pay_url"]})
    return web.json_response({"ok": False, "error": "xRocket token not configured or API error"}, status=500)


# ---------------------------------------------------------------------------
# 4. ADMIN HTTP HANDLERS
# ---------------------------------------------------------------------------

async def get_admin_web_page(request: web.Request) -> web.Response:
    from database import verify_admin_web_token, get_payments_paginated, get_payments_dashboard_stats, get_setting

    provided_key = request.query.get("key") or request.cookies.get("admin_web_key") or ""
    if provided_key == "logout":
        resp = web.Response(text=render_admin_login_html("تم تسجيل الخروج بنجاح"), content_type="text/html")
        resp.del_cookie("admin_web_key")
        return resp

    is_valid = await verify_admin_web_token(provided_key)
    if not is_valid:
        return web.Response(text=render_admin_login_html("مفتاح الأدمن غير صحيح أو منتهي الصلاحية"), content_type="text/html")

    filter_status = request.query.get("status")
    payments, total_count = await get_payments_paginated(limit=50, offset=0, status=filter_status)
    stats = await get_payments_dashboard_stats()

    store_name = await get_setting("store_name", "Digital Store")
    settings = {
        "crypto_addr_binance": await get_setting("crypto_addr_binance", ""),
        "crypto_addr_usdt": await get_setting("crypto_addr_usdt", ""),
        "crypto_addr_usdt_trc20": await get_setting("crypto_addr_usdt_trc20", ""),
        "crypto_addr_usdt_bep20": await get_setting("crypto_addr_usdt_bep20", ""),
        "crypto_addr_ton": await get_setting("crypto_addr_ton", ""),
        "crypto_addr_ltc": await get_setting("crypto_addr_ltc", ""),
        "cryptobot_token": await get_setting("cryptobot_token", ""),
        "xrocket_token": await get_setting("xrocket_token", ""),
        "min_deposit_amount": await get_setting("min_deposit_amount", "1.0"),
    }

    html_content = render_admin_dashboard_html(stats, settings, payments, total_count, provided_key, store_name)
    response = web.Response(text=html_content, content_type="text/html")
    response.set_cookie("admin_web_key", provided_key, max_age=86400 * 7, httponly=True)
    return response


async def api_admin_save_settings(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    admin_key = data.get("key")
    from database import verify_admin_web_token, set_setting
    if not await verify_admin_web_token(admin_key):
        return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

    allowed_keys = [
        "crypto_addr_binance", "crypto_addr_usdt_trc20", "crypto_addr_usdt_bep20",
        "crypto_addr_ton", "crypto_addr_ltc", "cryptobot_token", "xrocket_token", "min_deposit_amount"
    ]
    for k in allowed_keys:
        if k in data:
            await set_setting(k, str(data[k]).strip())

    return web.json_response({"ok": True})


async def api_admin_action_payment(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    admin_key = data.get("key")
    from database import verify_admin_web_token, complete_payment, reject_payment, get_payment, get_user
    if not await verify_admin_web_token(admin_key):
        return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

    tx_id = data.get("transaction_id")
    action = data.get("action")
    if not tx_id or action not in ["approve", "reject"]:
        return web.json_response({"ok": False, "error": "Invalid parameters"}, status=400)

    payment = await get_payment(tx_id)
    if not payment:
        return web.json_response({"ok": False, "error": "Payment record not found"}, status=404)

    bot = request.app.get("bot")
    user_id = payment.get("user_id")

    if action == "approve":
        res = await complete_payment(tx_id)
        if res and bot and user_id:
            try:
                db_user = await get_user(user_id)
                u_lang = db_user.get("language", "ar") if db_user else "ar"
                from localization import get_text
                msg_txt = get_text('payment_success', u_lang, amount=payment['amount'], new_balance=db_user.get('balance', 0.0) if db_user else payment['amount'])
                await bot.send_message(chat_id=user_id, text=f"Global Web Checkout\n\n{msg_txt}", parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Failed to send approval message: {e}")
        return web.json_response({"ok": bool(res)})
    else:
        res = await reject_payment(tx_id)
        if res and bot and user_id:
            try:
                await bot.send_message(chat_id=user_id, text=f"تم رفض إيداعك بقيمة ${payment['amount']:.2f} (معرّف المعاملة: {tx_id}). يرجى مراجعة الدعم الفني.", parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Failed to send rejection message: {e}")
        return web.json_response({"ok": bool(res)})


def setup_web_portal_routes(app: web.Application):
    app.router.add_get("/pay/{token}", get_checkout_page)
    app.router.add_get("/pay", get_checkout_page)
    app.router.add_post("/api/pay/verify-transaction", api_verify_payment)
    app.router.add_post("/api/pay/create-cryptobot", api_create_cryptobot)
    app.router.add_post("/api/pay/create-xrocket", api_create_xrocket)

    app.router.add_get("/admin/web", get_admin_web_page)
    app.router.add_get("/admin/login", lambda req: web.Response(text=render_admin_login_html(), content_type="text/html"))
    app.router.add_post("/api/admin/save-settings", api_admin_save_settings)
    app.router.add_post("/api/admin/action-payment", api_admin_action_payment)
