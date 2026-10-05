# 🛍️ Ultimate Telegram Digital Store & Auto-Fulfillment Bot

> **The Most Advanced, Feature-Rich, and Scalable Digital Goods Marketplace & Auto-Fulfillment Bot for Telegram.**  
> Built with **Python 3.12**, **Aiogram 3.x (Async)**, and modern **Telegram Bot API 9.4+**.

---

## 🌟 Executive Summary

This bot is a complete, enterprise-grade solution for selling digital products (game keys, streaming accounts, software licenses, VPNs, gift cards, subscriptions, and more) directly inside Telegram. It features **instant automated delivery**, **multiple crypto & fiat payment gateways**, an **external provider dropshipping engine**, **built-in B2B Reseller REST API**, **Telegram Premium custom animated emoji UI**, and a **complete administrative dashboard** operated entirely within Telegram.

---

## 🚀 Key Feature Highlights

- 🌐 **8 Supported Languages:** English, Arabic, Russian, French, Chinese, Hindi, Korean, and Portuguese.
- 🎨 **Telegram Premium Animated Custom Emojis:** Native `icon_custom_emoji_id` support across all buttons, welcome headers, and country flags with automatic fallback to classic Unicode emojis.
- 💳 **5+ Payment Methods:** Binance Pay (Instant & Manual), Telegram Stars, CryptoBot (@CryptoBot), and On-Chain Direct Crypto (USDT BEP20/TRC20, LTC, TON).
- 🤖 **External Provider Dropshipping Engine:** Connect to third-party suppliers (ProdSeller, ShopDigital, SMM Panels, Custom APIs) with automated order fulfillment and live cost synchronization.
- 📈 **Smart Dynamic Pricing:** Set fixed profit markups, percentage margins, and minimum floor price protections that update automatically when supplier costs change.
- 🔑 **Built-In Reseller REST API:** Host your own automated API (FastAPI/Swagger) allowing other bot owners and websites to resell your stock.
- ⏳ **Automated Pre-Order System:** Customers can reserve out-of-stock products; the bot automatically fulfills orders the moment stock is replenished.
- 🔔 **Stock Availability Alerts:** "Notify Me When Available" button for instant restock push notifications.
- 👥 **Viral Referral & Affiliate System:** Rewarding referral program with configurable bonus balance credited upon friends' purchases.
- 📢 **Social Proof & Auto-Proofs Channel:** Automatically broadcasts sanitized proof-of-purchase receipts to your public channel at randomized intervals.
- 🔒 **Mandatory Channel Force-Join:** Restrict bot usage until users subscribe to your designated channels.
- 📊 **Real-Time Analytics & Admin Dashboard:** Full control over products, categories, stock, discounts, user balances, broadcast messages, and 24h revenue stats.

---

## 🛠️ Detailed Feature Breakdown

### 1. 🌐 Global 8-Language Localization
- Fully translated and localized into **8 major languages**:
  - 🇺🇸 **English** (`en`)
  - 🇸🇦 **Arabic** (`ar`)
  - 🇫🇷 **French** (`fr`)
  - 🇨🇳 **Chinese** (`zh`)
  - 🇮🇳 **Hindi** (`hi`)
  - 🇰🇷 **Korean** (`ko`)
  - 🇷🇺 **Russian** (`ru`)
  - 🇵🇹 **Portuguese** (`pt`)
- Clean language selector with custom animated country flags.
- Dual-string router matching: users can interact smoothly whether buttons show standard emojis or premium animated icons.
- Instant language switching with immediate menu re-rendering.

---

### 2. 🎨 Next-Gen UI with Premium Custom Emojis
- Built on **Telegram Bot API 9.4+**:
  - Animated custom emojis on all Reply Keyboard menu buttons (`KeyboardButton.icon_custom_emoji_id`).
  - Animated custom emojis on Inline Keyboard buttons (`InlineKeyboardButton.icon_custom_emoji_id`).
  - Animated welcome header banner (`<tg-emoji>`).
- **Complete Admin Customization:**
  - One-click toggle between **Premium Animated Emojis** and **Classic Unicode Emojis**.
  - Change any button or flag emoji on-the-fly by simply sending the animated emoji or its numeric ID to the bot.
  - Reset to default presets with a single click.

---

### 3. 💳 Comprehensive Payment Gateways

| Payment Gateway | Type | Details |
| :--- | :--- | :--- |
| **Binance Pay** | Instant API & Manual ID | Instant checkout QR code/deep-link, plus manual Binance Pay ID / TxID submission with automated background order verification. |
| **Telegram Stars** | In-App Native | Native Telegram Stars checkout with configurable Stars-to-USD exchange rate. |
| **Crypto Bot** | Automated Invoices | Integrated with `@CryptoBot` (supports USDT, TON, BTC, ETH, LTC). Full Mainnet and Testnet support. |
| **Direct Crypto Transfer** | On-Chain Verification | Automatic on-chain blockchain verification for **USDT (BEP20)**, **Litecoin (LTC)**, and **TON** via BscScan, BlockCypher, and TonCenter APIs. |
| **Internal Wallet Balance** | Escrow / Stored Value | Instant checkout using pre-funded user wallet balance. Supports deposit history and transaction logs. |

- **Duplicate Prevention & Security:** Cryptographic transaction hash checks to prevent double-spending or replay attacks.
- **Fail-Safe Refunds:** If a direct payment product goes out of stock during external provider execution, funds are automatically credited to the customer's wallet balance.

---

### 4. 🤖 External Provider Engine (Dropshipping & Auto-Fulfillment)
- Sell unlimited products without holding inventory.
- Connect to any external provider API:
  - **ProdSeller** (Official API v1 certified integration with `Idempotency-Key` and transient connection auto-retry).
  - **ShopDigital**.
  - **Custom REST / OpenAPI / Swagger APIs**.
- **Live Wholesale Cost Sync:** Automatically fetches real-time wholesale costs from suppliers before processing orders.
- **Dynamic Pricing Strategies:**
  - `Fixed`: Manual fixed retail price.
  - `Margin Fixed`: Provider wholesale cost + fixed dollar markup (e.g. Cost + $2.00).
  - `Margin Percent`: Provider wholesale cost + percentage markup (e.g. Cost + 25%).
  - `Floor Price Protection`: Minimum price threshold to prevent losses if wholesale prices fluctuate.
- **Automated Activation Email Capture:**
  - Automatically prompts customers to enter their target email address when purchasing subscription services (e.g., Canva Pro, CapCut, Spotify, shared family accounts).
  - Supports single and bulk quantity purchases (captures separate emails per unit).
- **Network Resilience:** Smart 3-attempt exponential auto-retry mechanism on transient connection timeouts.

---

### 5. 🔑 Built-In Reseller REST API (B2B Marketplace)
- Turn your bot into a wholesale provider for other store owners and web apps.
- **FastAPI / Async REST Server** running on port 8080:
  - `GET /api/v1/products`: Product catalog with live pricing and available stock.
  - `GET /api/v1/balance`: User balance check via API key.
  - `POST /api/v1/orders`: Automated order execution and instant key delivery.
  - `GET /api/v1/orders/{order_id}`: Order lookup and credential retrieval.
- **API Key Management:** Users can generate, regenerate, or revoke their unique API key directly in the bot.
- **Interactive Documentation:** Built-in Swagger / OpenAPI UI (`/docs`).

---

### 6. 🛒 Enhanced Customer Shopping Experience
- **Category System:** Clean category hierarchy with custom emoji icons; toggle to view all products or browse by category.
- **Drag-and-Drop Product Reordering:** Easily change the visual display order of items (Top, Up, Down, Custom Position).
- **Hide Out-of-Stock Toggle:** Option to automatically hide or display depleted products.
- **Volume Bulk Discounts (Tiered Pricing):** Set automatic discounts for quantity purchases (e.g. Buy 5 get $1 off each, Buy 10 get $2 off each).
- **Pre-Order Reservations:** Customers can lock funds to reserve out-of-stock items, fulfilled automatically upon supplier restock.
- **Back-in-Stock Alerts:** Push notifications sent to interested users when items are restocked.
- **Order History:** Complete purchase ledger with instant retrieval of keys, passwords, and instructions.
- **Customer Support Tickets:** In-bot messaging system allowing customers to submit support inquiries; admins can reply directly with one click.

---

### 7. ⚙️ Robust In-Telegram Admin Panel
No external web browser required — manage your entire business directly within Telegram:
- **Product & Category Manager:** Add, edit, delete, reorder products, modify titles/descriptions across all languages.
- **Stock Manager:** Add single codes or paste thousands of keys in bulk (`bulk_add_stock`).
- **User Inspector:** Search any user by ID or username; inspect balance, total spend, invited referrals, and order history.
- **Manual Financial Adjustments:** Credit or debit balances manually with instant notification to the user.
- **VIP & Custom Discounts:** Set permanent custom discount percentages or custom fixed product prices for VIP customers.
- **Deposit Approval Center:** Review, approve, or reject pending crypto and Binance Pay deposits with a single click.
- **Anti-Fraud & Ban System:** Ban malicious users with custom reason tracking; banned users are blocked by custom middleware.
- **Global Broadcast Tool:** Send rich HTML/Markdown announcements to all registered users with live delivery stats.
- **Channel & Security Controls:** Configure mandatory force-join channels, news channels, and support handles.
- **24-Hour Sales Analytics:** Instant breakdown of sales count, revenue, and profit within the last 24 hours.

---

### 8. 📢 Built-In Viral Growth & Marketing Tools
- **Affiliate & Referral System:**
  - Each customer gets a unique referral invite link (`t.me/bot?start=ref_XXXX`).
  - Configurable bonus reward automatically credited to the referrer upon the invited friend's first purchase.
  - Real-time stats showing total invited users and earnings.
- **Automated Social Proof Broadcaster:**
  - Automatically shares masked, verifiable proof-of-purchase receipts to your Telegram channel at randomized intervals (5 to 20 minutes).
  - Builds trust and drives urgency without revealing sensitive customer credentials.
- **Mandatory Channel Lock (Force-Join):**
  - Require users to join one or multiple Telegram channels before unlocking the bot.
  - Automatically checks channel membership via Telegram API.

---

## 🏗️ Architecture & Technical Stack

- **Framework:** `Python 3.12` + `aiogram 3.x` (Fully Asynchronous, Event-Driven).
- **HTTP Client:** `aiohttp` with connection pooling, custom timeouts, and auto-retry.
- **Database:** `SQLite 3` via `aiosqlite` with **WAL (Write-Ahead Logging)** mode enabled, foreign keys enforced, and 30-second busy timeout for high-concurrency collision prevention.
- **API Server:** Built-in lightweight async REST server for Reseller API.
- **Deployment Compatibility:**
  - **Railway.app** (1-click deploy with included `Procfile` and `railway.json`).
  - **VPS / Dedicated Server** (Ubuntu/Debian, systemd service, Docker).
  - **Docker** (`Dockerfile` included with multi-stage build support).
- **Source Protection Ready:** Compatible with **Cython** and **PyArmor** for compiling `.py` into compiled binary `.so` modules for safe code distribution.

---

## 📦 What's Included in the Package

1. Complete clean Python source code (`handlers/`, `middlewares/`, `database.py`, `keyboards.py`, `localization.py`, `providers_engine.py`, etc.).
2. Production `Dockerfile` and `Procfile`.
3. Pre-configured `.env.example` file.
4. Comprehensive Setup & Deployment Guide (`DEPLOY_GUIDE_EN.txt`).
5. Complete OpenAPI / Swagger Reseller API documentation.
6. Lifetime access to code updates and improvements.
