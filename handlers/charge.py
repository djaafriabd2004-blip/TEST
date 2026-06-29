from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
from database import (
    get_user, create_payment, get_payment, complete_payment, get_setting,
    is_payment_processed, get_payment_by_method, reject_payment, get_button_emojis
)
from crypto_verifier import verify_crypto_transaction, is_tx_too_old_error, get_max_tx_age_seconds, is_amount_matching
from localization import get_text
from handlers.states import ChargeStates
from cryptobot_client import create_cryptobot_invoice, get_cryptobot_invoice
import config
import keyboards
import uuid
import time
import logging

logger = logging.getLogger(__name__)
router = Router()

async def show_charge_menu(message_or_callback, user_id, lang='en'):
    db_user = await get_user(user_id)
    balance = db_user['balance'] if db_user else 0.0
    text = get_text('charge_title', lang, balance=balance)
    
    stars_enabled = (await get_setting('stars_enabled', '1')) == '1'
    cryptobot_token = await get_setting('cryptobot_token', '')
    cryptobot_enabled = len(cryptobot_token) > 0 and (await get_setting('cryptobot_enabled', '1')) == '1'
    cryptotransfer_enabled = (await get_setting('cryptotransfer_enabled', '1')) == '1'
    
    kb = keyboards.get_charge_methods_keyboard(lang, stars_enabled, cryptobot_enabled, cryptotransfer_enabled)
    
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.message(F.text.in_([
    get_text('btn_charge_balance', 'en'),
    get_text('btn_charge_balance', 'ar'),
    get_text('btn_charge_balance', 'ru')
]))
async def cmd_charge(message: Message, lang='en'):
    await show_charge_menu(message, message.from_user.id, lang)

@router.callback_query(F.data == "charge_menu")
async def cb_charge_menu(callback: CallbackQuery, lang='en'):
    await show_charge_menu(callback, callback.from_user.id, lang)
    await callback.answer()

@router.callback_query(F.data == "cancel_charge")
async def cb_cancel_charge(callback: CallbackQuery, is_admin=False, lang='en'):
    db_user = await get_user(callback.from_user.id)
    ref_by_name = "None"
    if db_user and db_user['referred_by']:
        referrer_profile = await get_user(db_user['referred_by'])
        if referrer_profile:
            ref_by_name = referrer_profile['first_name']
            
    from database import get_referral_count
    ref_count = await get_referral_count(callback.from_user.id)
    balance = db_user['balance'] if db_user else 0.0
    
    store_name = await get_setting('store_name', 'Digital Store')
    welcome_emoji_id = await get_setting('welcome_emoji_id', '')
    if welcome_emoji_id:
        welcome_emoji = f'<tg-emoji emoji-id="{welcome_emoji_id}">🔷</tg-emoji>'
    else:
        welcome_emoji = '🔷'
    welcome_text = get_text(
        'welcome', 
        lang, 
        name=callback.from_user.first_name, 
        balance=balance, 
        referred_by=ref_by_name, 
        ref_count=ref_count,
        store_name=store_name,
        welcome_emoji=welcome_emoji,
        user_id=callback.from_user.id
    )
    button_emojis = await get_button_emojis()
    await callback.message.answer(
        welcome_text,
        reply_markup=keyboards.get_main_menu(lang, is_admin, button_emojis=button_emojis),
        parse_mode="HTML"
    )
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "charge_stars")
async def cb_charge_stars_selected(callback: CallbackQuery, state: FSMContext, lang='en'):
    await state.update_data(payment_method="stars")
    await state.set_state(ChargeStates.waiting_for_amount)
    await callback.message.edit_text(get_text('enter_amount_usd', lang))
    await callback.answer()

@router.callback_query(F.data == "charge_cryptobot")
async def cb_charge_cryptobot_selected(callback: CallbackQuery, state: FSMContext, lang='en'):
    await state.update_data(payment_method="cryptobot")
    await state.set_state(ChargeStates.waiting_for_amount)
    await callback.message.edit_text(get_text('enter_amount_usd', lang))
    await callback.answer()

@router.callback_query(F.data == "charge_cryptotransfer")
async def cb_charge_cryptotransfer_selected(callback: CallbackQuery, state: FSMContext, lang='en'):
    await state.set_state(ChargeStates.waiting_for_crypto_coin)
    await callback.message.edit_text(
        get_text('crypto_select_coin', lang),
        reply_markup=keyboards.get_crypto_coins_keyboard(lang)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("crypto_coin_"))
async def cb_crypto_coin_selected(callback: CallbackQuery, state: FSMContext, lang='en'):
    coin = callback.data.replace("crypto_coin_", "")
    import time
    await state.update_data(crypto_coin=coin, crypto_start_time=int(time.time()))
    
    # Coin addresses configuration
    default_addresses = {
        "USDT": "0x89846777ea91dee2b25f0fcbf54884a4f79923d8",
        "LTC": "LbEuNY2o5ePVyd7dqE4dTyNToAPDtcYMXR",
        "TON": "UQC8zbAwkf9-f8SzyYYITLU8Et4g-Cf7ffyQJIhip9nupHGo",
        "BINANCE": "Not Configured"
    }
    db_key = f"crypto_addr_{coin.lower()}"
    default_address = default_addresses.get(coin, "")
    address = await get_setting(db_key, default_address)
    
    # Format instructions
    coin_labels = {
        "USDT": "USDT BEP20",
        "LTC": "Litecoin (LTC)",
        "TON": "TON",
        "BINANCE": "Binance Pay / ID"
    }
    coin_label = coin_labels.get(coin, coin)
    
    await state.set_state(ChargeStates.waiting_for_crypto_amount)
    
    if coin == "BINANCE":
        text = get_text('binance_id_instructions', lang, address=address)
    else:
        text = get_text('crypto_instructions', lang, coin=coin_label, address=address)
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(ChargeStates.waiting_for_crypto_amount)
async def process_crypto_amount(message: Message, state: FSMContext, lang='en'):
    amount_str = message.text.strip()
    try:
        amount = float(amount_str)
        if amount < 1.0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('invalid_amount', lang))
        return
        
    import time
    await state.update_data(crypto_amount=amount, crypto_start_time=int(time.time()))
    await state.set_state(ChargeStates.waiting_for_crypto_txid)
    
    data = await state.get_data()
    coin = data.get('crypto_coin')
    if coin == "BINANCE":
        await message.answer(get_text('binance_enter_txid', lang), parse_mode="Markdown")
    else:
        await message.answer(get_text('crypto_enter_txid', lang), parse_mode="Markdown")

@router.message(ChargeStates.waiting_for_crypto_txid)
async def process_crypto_txid(message: Message, state: FSMContext, bot: Bot, lang='en'):
    txid = message.text.strip()
    if len(txid) < 5:
        await message.answer("❌ Invalid Transaction ID. Please enter a valid TxID/Hash/PayID:")
        return
        
    data = await state.get_data()
    coin = data.get('crypto_coin')
    amount = data.get('crypto_amount')
    import time
    start_time = data.get('crypto_start_time') or int(time.time())
    user_id = message.from_user.id
    
    await state.clear()
    
    payment_method = f"blockchain_{coin}_{txid}"
    
    # Check if this TxID is already in database
    existing_payment = await get_payment_by_method(payment_method)
    if existing_payment:
        status = existing_payment['status']
        if status == 'completed':
            await message.answer(get_text('crypto_already_processed', lang))
            return
        elif status == 'pending':
            await message.answer(
                "⏳ *Transaction already pending verification!*\n\n"
                "This transaction has already been submitted and is currently being verified. "
                "Please wait, your balance will be updated automatically.",
                parse_mode="Markdown"
            )
            return
        elif status == 'rejected':
            await message.answer(
                "❌ *Transaction Rejected!*\n\n"
                "This transaction was previously rejected. If you believe this is an error, please contact support.",
                parse_mode="Markdown"
            )
            return
            
    # Generate short unique transaction ID for DB & callbacks
    transaction_id = f"BL_{uuid.uuid4().hex[:8].upper()}"
    
    # Save pending payment to DB
    import datetime
    start_time_utc = datetime.datetime.fromtimestamp(start_time, datetime.timezone.utc)
    created_at_str = start_time_utc.strftime("%Y-%m-%d %H:%M:%S")
    await create_payment(user_id, amount, payment_method, transaction_id, created_at=created_at_str)
    
    # Format labels
    coin_labels = {
        "USDT": "USDT BEP20",
        "LTC": "Litecoin (LTC)",
        "TON": "TON",
        "BINANCE": "Binance Pay / ID"
    }
    coin_label = coin_labels.get(coin, coin)
    
    user_info = f"{message.from_user.first_name}"
    if message.from_user.username:
        user_info += f" (@{message.from_user.username})"
        
    # Attempt instant verification
    recipient_address = await get_setting(f"crypto_addr_{coin.lower()}", "")
    ts_to_pass = None if coin == "BINANCE" else start_time
    success, result_val = await verify_crypto_transaction(coin, txid, recipient_address, min_timestamp=ts_to_pass)
    
    if success:
        # Verify that verified on-chain amount matches requested amount (exempt Binance Pay)
        if coin != "BINANCE" and not is_amount_matching(amount, result_val, coin):
            logger.warning(f"Instant check amount mismatch for user {user_id}: requested {amount}, on-chain {result_val}")
            await reject_payment(transaction_id)
            
            err_text = {
                "ar": f"❌ *خطأ في تطابق المبلغ!*\n\nالمبلغ الفعلي في المعاملة (`${result_val:.2f} USD`) لا يتطابق مع المبلغ الذي طلبته (`${amount:.2f} USD`). تم رفض العملية لأسباب أمنية.",
                "en": f"❌ *Amount Mismatch Error!*\n\nThe actual transaction amount (`${result_val:.2f} USD`) does not match your declared deposit amount (`${amount:.2f} USD`). Transaction rejected for security reasons.",
                "ru": f"❌ *Ошибка совпадения суммы!*\n\nФактическая сумма транзакции (`${result_val:.2f} USD`) не совпадает с заявленной (`${amount:.2f} USD`). Транзакция отклонена из соображений безопасности."
            }
            await message.answer(err_text.get(lang, err_text['en']), parse_mode="Markdown")
            
            # Send high-priority alert to admins about suspicious TxID submission
            admin_alert = (
                f"🚨 *SUSPICIOUS DEPOSIT: Amount Mismatch! (TxID Reuse/Theft Attempt)*\n\n"
                f"👤 *User:* {user_info} (`{user_id}`)\n"
                f"🪙 *Coin:* `{coin_label}`\n"
                f"🔗 *TxID:* `{txid}`\n"
                f"📥 *User Entered:* `${amount:.2f} USD`\n"
                f"🔗 *Actual On-Chain:* `${result_val:.2f} USD`\n"
                f"⚠️ *Status:* Automatically Rejected."
            )
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=admin_id, text=admin_alert, parse_mode="Markdown")
                except Exception:
                    pass
            return

        # Update payment amount in DB to the actual verified amount on-chain
        import aiosqlite
        from config import DB_NAME
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE payments SET amount = ? WHERE transaction_id = ?;", 
                (result_val, transaction_id)
            )
            await db.commit()
            
        # Complete payment
        res = await complete_payment(transaction_id)
        if res:
            db_user = await get_user(user_id)
            new_balance = db_user['balance'] if db_user else 0.0
            
            await message.answer(
                get_text('payment_success', lang, amount=result_val, new_balance=new_balance),
                parse_mode="Markdown"
            )
            
            # Notify referrer if any
            ref_notif = res.get('referrer_notif')
            if ref_notif:
                ref_id = ref_notif['referrer_id']
                ref_bonus = ref_notif['bonus']
                try:
                    await bot.send_message(
                        chat_id=ref_id,
                        text=f"🎉 *Referral Bonus!*\n💰 You earned `${ref_bonus:.2f} USD` from your referral's deposit!",
                        parse_mode="Markdown"
                    )
                except Exception as re:
                    logger.warning(f"Could not notify referrer {ref_id}: {re}")
                    
            # Notify admins of instant auto-verification
            admin_notif = (
                f"✅ *Instant Auto-Verified Crypto Deposit!*\n\n"
                f"👤 *User:* {user_info} (`{user_id}`)\n"
                f"🪙 *Coin:* `{coin_label}`\n"
                f"💵 *Amount Credited:* `${result_val:.2f} USD`\n"
                f"🔗 *TxID:* `{txid}`"
            )
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=admin_id, text=admin_notif, parse_mode="Markdown")
                except Exception:
                    pass
    else:
        if is_tx_too_old_error(result_val):
            await reject_payment(transaction_id)
            
            # Send alert to admins about the potential fraud/older TxID reuse
            admin_alert = (
                f"⚠️ *Potential Fraud / Older TxID Reuse Attempt!*\n\n"
                f"👤 *User:* {user_info} (`{user_id}`)\n"
                f"🪙 *Coin:* `{coin_label}`\n"
                f"🔗 *TxID/PayID:* `{txid}`\n"
                f"❌ *Reason:* {result_val.replace('TX_TOO_OLD: ', '')}"
            )
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=admin_id, text=admin_alert, parse_mode="Markdown")
                except Exception:
                    pass
                    
            max_hours = max(1, (await get_max_tx_age_seconds()) // 3600)
            await message.answer(
                get_text('crypto_tx_too_old', lang, hours=max_hours),
                parse_mode="Markdown"
            )
            return

        # Verification failed or pending. Tell user we are auto-checking in the background
        await message.answer(
            get_text('crypto_deposit_submitted_auto', lang),
            parse_mode="Markdown"
        )
        
        # Send to admin with [Auto-Checking] prefix as backup manual approve/reject
        admin_notif_text = (
            f"⏳ *[Auto-Checking] Pending Crypto Deposit!*\n\n"
            f"👤 *User:* {user_info} (`{user_id}`)\n"
            f"🪙 *Coin:* `{coin_label}`\n"
            f"💵 *Amount:* `${amount:.2f} USD`\n"
            f"🔗 *TxID:* `{txid}`\n\n"
            f"The system is currently auto-verifying this transaction on the blockchain. "
            f"You can also manually Approve/Reject below if needed."
        )
        
        kb = keyboards.get_admin_payment_approval_keyboard(transaction_id)
                
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_notif_text,
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id} for deposit: {e}")

@router.message(ChargeStates.waiting_for_amount)
async def process_charge_amount(message: Message, state: FSMContext, bot: Bot, lang='en'):
    amount_str = message.text.strip()
    try:
        amount = float(amount_str)
        if amount < 1.0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('invalid_amount', lang))
        return
        
    data = await state.get_data()
    method = data.get('payment_method')
    user_id = message.from_user.id
    
    await state.clear()
            
    if method == "stars":
        stars_rate = float(await get_setting('stars_rate', '0.02'))
        stars_amount = int(amount / stars_rate)
        if stars_amount < 1:
            stars_amount = 1
            
        transaction_id = f"STARS_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        
        await create_payment(user_id, amount, 'telegram_stars', transaction_id)
        
        title = get_text('stars_invoice_title', lang, amount=amount)
        desc = get_text('stars_invoice_desc', lang, amount=amount)
        payload = f"stars_dep_{user_id}_{amount}_{transaction_id}"
        
        try:
            await bot.send_invoice(
                chat_id=user_id,
                title=title,
                description=desc,
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Stars", amount=stars_amount)],
                start_parameter="stars_deposit"
            )
        except Exception as e:
            logger.error(f"Stars invoice failed: {e}")
            await message.answer(f"❌ Failed to generate Telegram Stars invoice: {e}")
            
    elif method == "cryptobot":
        transaction_id = f"CP_{uuid.uuid4().hex[:8].upper()}"
        store_name = await get_setting('store_name', 'Digital Store')
        description = f"Deposit to {store_name}"
        
        invoice = await create_cryptobot_invoice(amount, f"cryptobot_dep_{transaction_id}", description)
        if not invoice:
            await message.answer("❌ Failed to create Crypto Bot invoice. Please verify settings or contact admin.")
            return
            
        invoice_id = invoice['invoice_id']
        pay_url = invoice['pay_url']
        
        await create_payment(user_id, amount, f"cryptobot_{invoice_id}", transaction_id)
        
        inst_text = get_text('cryptobot_instructions', lang, amount=amount)
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('btn_pay_now', lang), url=pay_url)
        builder.button(text=get_text('btn_check_payment', lang), callback_data=f"check_cryptobot_{transaction_id}")
        builder.button(text=get_text('btn_back', lang), callback_data="charge_menu")
        builder.adjust(1)
        
        await message.answer(inst_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

# PreCheckout handler (Must reply within 10 seconds)
@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

# Successful Payment handler
@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot, lang='en'):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    
    if payload.startswith("stars_dep_"):
        parts = payload.split("_")
        if len(parts) >= 5:
            transaction_id = "_".join(parts[4:])
            
            result = await complete_payment(transaction_id)
            if result:
                user_id = result['user_id']
                amount = result['amount']
                
                db_user = await get_user(user_id)
                new_balance = db_user['balance'] if db_user else 0.0
                
                await message.answer(
                    get_text('payment_success', lang, amount=amount, new_balance=new_balance),
                    parse_mode="Markdown"
                )
                
                ref_notif = result['referrer_notif']
                if ref_notif:
                    ref_id = ref_notif['referrer_id']
                    ref_bonus = ref_notif['bonus']
                    
                    try:
                        await bot.send_message(
                            chat_id=ref_id,
                            text=f"🎉 *Referral Bonus!*\n💰 You earned `${ref_bonus:.2f} USD` from your referral's deposit!",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.warning(f"Could not notify referrer {ref_id}: {e}")


@router.callback_query(F.data.startswith("check_cryptobot_"))
async def cb_check_cryptobot_payment(callback: CallbackQuery, bot: Bot, lang='en'):
    transaction_id = callback.data.replace("check_cryptobot_", "")
    payment = await get_payment(transaction_id)
    if not payment:
        await callback.answer(get_text('crypto_already_processed', lang), show_alert=True)
        return
        
    method_str = payment['payment_method']
    if not method_str.startswith("cryptobot_"):
        await callback.answer("❌ Invalid transaction method.")
        return
        
    invoice_id_str = method_str.replace("cryptobot_", "")
    try:
        invoice_id = int(invoice_id_str)
    except ValueError:
        await callback.answer("❌ Invalid invoice ID.")
        return
        
    await callback.answer(get_text('payment_pending_check', lang))
    
    invoice = await get_cryptobot_invoice(invoice_id)
    if invoice and invoice.get("status") == "paid":
        res = await complete_payment(transaction_id)
        if res:
            db_user = await get_user(payment['user_id'])
            new_balance = db_user['balance'] if db_user else 0.0
            
            await callback.message.edit_text(
                get_text('payment_success', lang, amount=payment['amount'], new_balance=new_balance),
                parse_mode="Markdown"
            )
            
            ref_notif = res.get('referrer_notif')
            if ref_notif:
                ref_id = ref_notif['referrer_id']
                ref_bonus = ref_notif['bonus']
                try:
                    await bot.send_message(
                        chat_id=ref_id,
                        text=f"🎉 *Referral Bonus!*\n💰 You earned `${ref_bonus:.2f} USD` from your referral's deposit!",
                        parse_mode="Markdown"
                    )
                except Exception as re:
                    logger.warning(f"Could not notify referrer {ref_id}: {re}")
                    
            user_info = f"{callback.from_user.first_name}"
            if callback.from_user.username:
                user_info += f" (@{callback.from_user.username})"
            admin_notif = (
                f"✅ *Verified Crypto Bot Deposit!*\n\n"
                f"👤 *User:* {user_info} (`{payment['user_id']}`)\n"
                f"💵 *Amount Credited:* `${payment['amount']:.2f} USD`\n"
                f"🆔 *Invoice ID:* `{invoice_id}`"
            )
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(chat_id=admin_id, text=admin_notif, parse_mode="Markdown")
                except Exception:
                    pass
    else:
        await callback.message.answer(
            get_text('payment_not_found_or_pending', lang),
            parse_mode="Markdown"
        )

