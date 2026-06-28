# 🛍️ Telegram Digital Store Bot — Features

A fully-featured Telegram bot for selling digital products with automated payments and delivery.

---

## 🌐 Multi-Language Support
- English 🇺🇸 | Arabic 🇸🇦 | Russian 🇷🇺
- Users can switch language anytime from the main menu

## 🛒 Digital Shop
- Browse and purchase digital products directly in Telegram
- View product details, stock availability, and pricing
- Buy multiple quantities at once
- Instant automated delivery of purchased items (accounts, keys, etc.)
- Order history for users to review past purchases

## 💳 Multiple Payment Methods
- **Telegram Stars** — Native in-app payment with configurable exchange rate
- **Crypto Bot (@CryptoBot)** — Instant invoice-based crypto payments (Mainnet & Testnet support)
- **Manual Crypto Transfer** — Direct on-chain deposits with automatic blockchain verification:
  - USDT (BEP20)
  - Litecoin (LTC)
  - TON
- Each payment method can be enabled/disabled independently from the admin panel

## 🔗 Automated Blockchain Verification
- Real-time on-chain transaction verification for USDT, LTC, and TON
- Background verification loop for pending deposits
- Fallback to manual admin approval if verification fails
- Duplicate transaction protection

## 👥 Referral System
- Unique referral link for every user
- Configurable bonus percentage on referral deposits
- Referral stats tracking (count & total earned)

## 📢 Channel Integration
- **Force Join** — Require users to join specific channels before using the bot
- **News Channel** — Automatic purchase announcements posted to your channel

## 🎧 Support System
- Users can contact support directly through the bot
- Admin receives support tickets with one-click reply
- Messages delivered back to the user seamlessly

## ⚙️ Full Admin Panel
- **Product Management** — Add, edit, delete products (name, description, price in 3 languages)
- **Stock Management** — Add stock items one-by-one or bulk upload
- **User Management** — View user details, edit balances, set per-user discounts
- **Deposit Management** — View and manually approve/reject pending deposits
- **Broadcast** — Send messages to all users at once
- **Store Settings** — Customize store name, support handle, and channel settings
- **Payment Configuration** — Toggle payment methods, set crypto wallet addresses, configure Stars rate
- **API Keys** — Manage BscScan, Blockcypher, Toncenter, and Crypto Bot tokens from the panel
- **Referral Settings** — Adjust bonus percentage

## 💰 Per-User Discounts
- Set individual discount percentages for specific users
- Discounts applied automatically at checkout

## 🏗️ Deployment Ready
- Built with **aiogram 3** (async Python)
- SQLite database (lightweight, no external DB needed)
- Railway-compatible with `Procfile` included
- Environment-based configuration via `.env`

---

## 🤝 Hosting Assistance Available

Need help deploying the bot to a server or cloud hosting (Railway, VPS, etc.)?  
**We offer free assistance with setup and deployment.**  
Contact us and we'll help you get your store up and running!
