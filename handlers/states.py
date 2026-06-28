from aiogram.fsm.state import State, StatesGroup

class SupportStates(StatesGroup):
    waiting_for_message = State()

class ChargeStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_crypto_coin = State()
    waiting_for_crypto_amount = State()
    waiting_for_crypto_txid = State()

class ProductStates(StatesGroup):
    # Add Product
    waiting_for_name = State()
    waiting_for_desc = State()
    waiting_for_price = State()
    waiting_for_custom_emoji = State()
    
    # Edit Product fields
    waiting_for_edit_name = State()
    waiting_for_edit_desc = State()
    waiting_for_edit_price = State()
    waiting_for_edit_specific_value = State()
    waiting_for_edit_custom_emoji = State()

class ShopStates(StatesGroup):
    waiting_for_buy_quantity = State()

class StockStates(StatesGroup):
    waiting_for_stock_product = State()
    waiting_for_stock_data = State()
    waiting_for_bulk_stock = State()

class AdminStates(StatesGroup):
    waiting_for_reply_text = State()
    waiting_for_broadcast = State()
    waiting_for_setting_value = State()
    waiting_for_discount_user_id = State()
    waiting_for_discount_percent = State()
    waiting_for_edit_discount_percent = State()
    waiting_for_store_name = State()
    waiting_for_balance_user_id = State()
    waiting_for_new_balance = State()
    waiting_for_inspect_user_id = State()
    waiting_for_btn_emoji = State()
    waiting_for_restore_db = State()
    waiting_for_api_key_user_id = State()

class ProvidersStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_key = State()
    waiting_for_price = State()
