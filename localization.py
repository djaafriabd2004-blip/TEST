# Localization configurations for English, Arabic, and Russian

LOCALIZATION = {
    'welcome': {
        'en': (
            "{welcome_emoji} <b>{store_name}</b>\n"
            "══════════════════\n\n"
            "Hey <b>{name}</b>! 👋\n\n"
            "<blockquote>"
            "🆔 <b>ID:</b> <code>{user_id}</code>\n"
            "💎 <b>Balance:</b> <code>${balance:.2f} USD</code>\n"
            "👥 <b>Referrals:</b> <code>{ref_count}</code> users\n"
            "🤝 <b>Invited by:</b> <code>{referred_by}</code>"
            "</blockquote>\n\n"
            "📌 <i>Pick an option from the menu below</i> 👇"
        ),
        'ar': (
            "{welcome_emoji} <b>{store_name}</b>\n"
            "══════════════════\n\n"
            "أهلاً <b>{name}</b>! 👋\n\n"
            "<blockquote>"
            "🆔 <b>المعرف:</b> <code>{user_id}</code>\n"
            "💎 <b>الرصيد:</b> <code>${balance:.2f} USD</code>\n"
            "👥 <b>الإحالات:</b> <code>{ref_count}</code> مستخدم\n"
            "🤝 <b>أحالك:</b> <code>{referred_by}</code>"
            "</blockquote>\n\n"
            "📌 <i>اختر ما تريد من القائمة أدناه</i> 👇"
        ),
        'ru': (
            "{welcome_emoji} <b>{store_name}</b>\n"
            "══════════════════\n\n"
            "Привет <b>{name}</b>! 👋\n\n"
            "<blockquote>"
            "🆔 <b>ID:</b> <code>{user_id}</code>\n"
            "💎 <b>Баланс:</b> <code>${balance:.2f} USD</code>\n"
            "👥 <b>Рефералы:</b> <code>{ref_count}</code> польз.\n"
            "🤝 <b>Пригласил:</b> <code>{referred_by}</code>"
            "</blockquote>\n\n"
            "📌 <i>Выберите опцию из меню ниже</i> 👇"
        ),
    },
    'btn_shop': {
        'en': "🛍️ Shop",
        'ar': "🛍️ المتجر",
        'ru': "🛍️ Магазин"
    },
    'btn_my_orders': {
        'en': "📦 My Orders",
        'ar': "📦 طلباتي",
        'ru': "📦 Мои заказы"
    },
    'btn_support': {
        'en': "🎧 Support",
        'ar': "🎧 الدعم",
        'ru': "🎧 Поддержка"
    },
    'btn_charge_balance': {
        'en': "💳 Charge Balance",
        'ar': "💳 شحن الرصيد",
        'ru': "💳 Пополнить баланс"
    },
    'btn_referral': {
        'en': "🔗 Referral Link",
        'ar': "🔗 رابط الإحالة",
        'ru': "🔗 Реферальная ссылка"
    },
    'btn_language': {
        'en': "🌐 Language / اللغة",
        'ar': "🌐 اللغة / Language",
        'ru': "🌐 Язык / Language"
    },
    'btn_reseller_api': {
        'en': "🔑 Reseller API",
        'ar': "🔑 بوابة الموزعين",
        'ru': "🔑 API Реселлера"
    },
    'btn_admin_panel': {
        'en': "⚙️ Admin Panel",
        'ar': "⚙️ لوحة التحكم",
        'ru': "⚙️ Админ-панель"
    },
    'select_lang': {
        'en': "🌍 Please select your language / الرجاء اختيار اللغة / Пожалуйста, выберите язык:",
        'ar': "🌍 Please select your language / الرجاء اختيار اللغة / Пожалуйста, выберите язык:",
        'ru': "🌍 Please select your language / الرجاء اختيار اللغة / Пожалуйста, выберите язык:"
    },
    'lang_updated': {
        'en': "✅ Language updated to English!",
        'ar': "✅ تم تغيير اللغة إلى العربية!",
        'ru': "✅ Язык изменен на Русский!"
    },
    'support_info': {
        'en': "💬 To contact support, please contact the admin directly: @{username}",
        'ar': "💬 للتواصل مع الدعم، يرجى التواصل مع المسؤول مباشرة: @{username}",
        'ru': "💬 Для связи с поддержкой обратитесь к администратору напрямую: @{username}"
    },
    'btn_contact_support': {
        'en': "🎧 Contact Support",
        'ar': "🎧 تواصل مع الدعم",
        'ru': "🎧 Связаться с поддержкой"
    },
    'support_no_handle': {
        'en': "❌ Support is currently unavailable.",
        'ar': "❌ الدعم غير متوفر حالياً.",
        'ru': "❌ Поддержка временно недоступна."
    },
    'support_ticket_sent': {
        'en': "✅ Your message has been sent to support. We will get back to you shortly.",
        'ar': "✅ تم إرسال رسالتك إلى الدعم. سنرد عليك في أقرب وقت ممكن.",
        'ru': "✅ Ваше сообщение отправлено в поддержку. Мы ответим вам в ближайшее время."
    },
    'support_new_ticket': {
        'en': "📬 New Support Ticket from {name} (`{user_id}`):\n\n💬 `{message}`",
        'ar': "📬 تذكرة دعم جديدة من {name} (`{user_id}`):\n\n💬 `{message}`",
        'ru': "📬 Новое обращение от {name} (`{user_id}`):\n\n💬 `{message}`"
    },
    'support_reply_delivered': {
        'en': "🎧 *Support reply:* {reply}",
        'ar': "🎧 *رد الدعم:* {reply}",
        'ru': "🎧 *Ответ поддержки:* {reply}"
    },
    'referral_msg': {
        'en': "🔗 *Referral System*\n\nShare your referral link with friends. When they top up their balance, you receive *{bonus}%* of their charge amount!\n\n👥 *Your Referrals:* `{count}`\n💰 *Total Earned:* `${earned:.2f} USD`\n\n📋 *Your Link:* `{link}`",
        'ar': "🔗 *نظام الإحالات*\n\nشارك رابط الإحالة الخاص بك مع أصدقائك. عندما يقومون بشحن رصيدهم، ستحصل على *{bonus}%* من قيمة شحنهم!\n\n👥 *عدد إحالاتك:* `{count}`\n💰 *إجمالي الأرباح:* `${earned:.2f} USD`\n\n📋 *رابطك:* `{link}`",
        'ru': "🔗 *Реферальная система*\n\nПоделитесь своей реферальной ссылкой. Когда ваши рефералы пополняют баланс, вы получаете *{bonus}%* от суммы их пополнения!\n\n👥 *Ваши рефералы:* `{count}`\n💰 *Всего заработано:* `${earned:.2f} USD`\n\n📋 *Ваша ссылка:* `{link}`"
    },
    'referral_new_user_joined': {
        'en': "🎉 *New Referral!*\n\nUser *{name}* has joined the bot using your referral link! You will earn a bonus when they top up their balance.",
        'ar': "🎉 *إحالة جديدة!*\n\nانضم المستخدم *{name}* إلى البوت عن طريق رابط الإحالة الخاص بك! ستحصل على مكافأة عندما يقوم بشحن رصيده.",
        'ru': "🎉 *Новый реферал!*\n\nПользователь *{name}* присоединился к боту по вашей реферальной ссылке! Вы получите бонус, когда он пополнит свой баланс."
    },
    'my_orders_title': {
        'en': "📦 *Your Purchase History:*",
        'ar': "📦 *سجل مشترياتك:*",
        'ru': "📦 *История ваших покупок:*"
    },
    'my_orders_empty': {
        'en': "📭 You haven't made any purchases yet.",
        'ar': "📭 لم تقم بأي عمليات شراء بعد.",
        'ru': "📭 Вы еще не совершали покупок."
    },
    'order_item': {
        'en': "🆔 *Order #{id}*\n🛍️ *Product:* {name}\n💵 *Paid:* `${price:.2f} USD`\n📅 *Date:* {date}\n📦 *Data delivered:* \n`{data}`\n\n" + ("=" * 20),
        'ar': "🆔 *طلب #{id}*\n🛍️ *المنتج:* {name}\n💵 *المدفوع:* `${price:.2f} USD`\n📅 *التاريخ:* {date}\n📦 *البيانات المرسلة:* \n`{data}`\n\n" + ("=" * 20),
        'ru': "🆔 *Заказ #{id}*\n🛍️ *Товар:* {name}\n💵 *Оплачено:* `${price:.2f} USD`\n📅 *Дата:* {date}\n📦 *Доставленные данные:* \n`{data}`\n\n" + ("=" * 20)
    },
    'shop_title': {
        'en': "🛍️ *Store Products*\nSelect a product to view details and purchase:",
        'ar': "🛍️ *منتجات المتجر*\nاختر منتجاً لعرض التفاصيل والشراء:",
        'ru': "🛍️ *Товары магазина*\nВыберите товар для просмотра деталей и покупки:"
    },
    'shop_empty': {
        'en': "📭 No products available right now.",
        'ar': "📭 لا توجد منتجات متوفرة حالياً.",
        'ru': "📭 В данный момент товаров нет."
    },
    'product_details': {
        'en': "🛍️ *Product:* {name}\n\n📝 *Description:* {desc}\n\n💵 *Price:* {price}\n📦 *Stock:* `{stock}` available",
        'ar': "🛍️ *المنتج:* {name}\n\n📝 *الوصف:* {desc}\n\n💵 *السعر:* {price}\n📦 *المخزون:* `{stock}` متوفر",
        'ru': "🛍️ *Товар:* {name}\n\n📝 *Описание:* {desc}\n\n💵 *Цена:* {price}\n📦 *В наличии:* `{stock}` шт."
    },
    'btn_buy': {
        'en': "🛒 Buy Now",
        'ar': "🛒 شراء الآن",
        'ru': "🛒 Купить сейчас"
    },
    'btn_back': {
        'en': "🔙 Back",
        'ar': "🔙 عودة",
        'ru': "🔙 Назад"
    },
    'out_of_stock': {
        'en': "❌ Sorry, this product is out of stock.",
        'ar': "❌ عذراً، هذا المنتج غير متوفر في المخزون حالياً.",
        'ru': "❌ К сожалению, товара нет в наличии."
    },
    'buy_quantity_prompt': {
        'en': "🛒 *Buying:* {name}\n📦 *Available Stock:* {stock}\n\n✏️ Please enter the quantity you want to buy (1 - {stock}):",
        'ar': "🛒 *شراء:* {name}\n📦 *المخزون المتوفر:* {stock}\n\n✏️ يرجى إدخال الكمية التي ترغب في شرائها (1 - {stock}):",
        'ru': "🛒 *Покупка:* {name}\n📦 *Доступный остаток:* {stock}\n\n✏️ Пожалуйста, введите количество, которое хотите купить (1 - {stock}):"
    },
    'invalid_quantity': {
        'en': "❌ Invalid quantity. Please enter a number between 1 and {max_stock}:",
        'ar': "❌ كمية غير صالحة. يرجى إدخال رقم بين 1 و {max_stock}:",
        'ru': "❌ Неверное количество. Пожалуйста, введите число от 1 до {max_stock}:"
    },
    'insufficient_balance': {
        'en': "❌ Insufficient balance. Please charge your balance first. Your balance is `${balance:.2f} USD` but the product costs `${price:.2f} USD`.",
        'ar': "❌ الرصيد غير كافٍ. يرجى شحن رصيدك أولاً. رصيدك الحالي هو `${balance:.2f} USD` وسعر المنتج هو `${price:.2f} USD`.",
        'ru': "❌ Недостаточно средств. Пожалуйста, пополните баланс. Ваш баланс `${balance:.2f} USD`, стоимость товара `${price:.2f} USD`."
    },
    'purchase_success': {
        'en': "🎉 *Purchase Successful!*\n\n🛍️ *Product:* {name}\n💵 *Paid:* `${price:.2f} USD`\n📦 *Your Item/Credentials:* \n\n`{data}`\n\nThank you for shopping with us! ❤️",
        'ar': "🎉 *تمت عملية الشراء بنجاح!*\n\n🛍️ *المنتج:* {name}\n💵 *المدفوع:* `${price:.2f} USD`\n📦 *بيانات المنتج:* \n\n`{data}`\n\nشكراً لشرائك من متجرنا! ❤️",
        'ru': "🎉 *Покупка успешно совершена!*\n\n🛍️ *Товар:* {name}\n💵 *Оплачено:* `${price:.2f} USD`\n📦 *Ваши данные:* \n\n`{data}`\n\nСпасибо за покупку! ❤️"
    },
    'purchase_success_continued': {
        'en': "📦 *Your Item/Credentials (Continued):* \n\n`{data}`",
        'ar': "📦 *بيانات المنتج (تابع):* \n\n`{data}`",
        'ru': "📦 *Ваши данные (Продолжение):* \n\n`{data}`"
    },
    'checkout_payment_prompt': {
        'en': "🛒 *Checkout* ({name} x{qty})\n💵 *Total Price:* `${price:.2f} USD`\n\n👇 Choose your preferred payment method below to complete the purchase:",
        'ar': "🛒 *الدفع لشراء:* {name} (الكمية {qty})\n💵 *السعر الإجمالي:* `${price:.2f} USD`\n\n👇 اختر طريقة الدفع المفضلة لديك لإتمام عملية الشراء:",
        'ru': "🛒 *Оплата заказа* ({name} x{qty})\n💵 *Итого:* `${price:.2f} USD`\n\n👇 Выберите способ оплаты для завершения покупки:"
    },
    'btn_pay_balance': {
        'en': "💰 Pay with Wallet Balance (${balance:.2f})",
        'ar': "💰 الدفع من رصيد المحفظة (${balance:.2f})",
        'ru': "💰 Оплатить с баланса кошелька (${balance:.2f})"
    },
    'btn_pay_binance': {
        'en': "🔶 Pay with Binance Pay (Instant)",
        'ar': "🔶 الدفع عبر Binance Pay (فوري)",
        'ru': "🔶 Оплатить через Binance Pay"
    },
    'checkout_binance_created': {
        'en': "🔶 *Binance Pay Order Created!*\n\n💵 *Total Amount:* `${price:.2f} USD`\n\n1. Click the button below to pay via Binance Pay.\n2. Once paid, click **Check Payment Status** to receive your product.",
        'ar': "🔶 *تم إنشاء طلب الدفع عبر Binance Pay!*\n\n💵 *المبلغ الإجمالي:* `${price:.2f} USD`\n\n1. اضغط على الزر أدناه للدفع عبر تطبيق بايننس.\n2. بعد إتمام الدفع، اضغط على **التحقق من حالة الدفع** لاستلام منتجك فوراً.",
        'ru': "🔶 *Счет в Binance Pay создан!*\n\n💵 *Сумма:* `${price:.2f} USD`\n\n1. Нажмите кнопку ниже для оплаты через Binance Pay.\n2. После оплаты нажмите **Проверить статус платежа**, чтобы получить товар."
    },
    'checkout_binance_paid': {
        'en': "✅ *Payment Confirmed!* Processing your delivery...",
        'ar': "✅ *تم تأكيد الدفع بنجاح!* جاري تسليم منتجك...",
        'ru': "✅ *Оплата подтверждена!* Доставка товара..."
    },
    'checkout_binance_failed': {
        'en': "❌ *Payment not found or still pending.* Please pay first and then click verify.",
        'ar': "❌ *لم يتم العثور على الدفع أو لا يزال قيد الانتظار.* يرجى إتمام الدفع أولاً ثم الضغط على التحقق.",
        'ru': "❌ *Платеж не найден или ожидает оплаты.* Пожалуйста, оплатите счет и нажмите кнопку проверки."
    },
    'charge_title': {
        'en': "💳 *Charge Balance*\n\nChoose your preferred payment method below. Your current balance is `${balance:.2f} USD`.",
        'ar': "💳 *شحن الرصيد*\n\nاختر طريقة الدفع المفضلة لديك أدناه. رصيدك الحالي هو `${balance:.2f} USD`.",
        'ru': "💳 *Пополнение баланса*\n\nВыберите предпочтительный способ оплаты. Ваш текущий баланс: `${balance:.2f} USD`."
    },
    'btn_binance_pay': {
        'en': "🔸 Binance Pay (USDT)",
        'ar': "🔸 بايننس باي (USDT)",
        'ru': "🔸 Binance Pay (USDT)"
    },
    'btn_stars': {
        'en': "⭐️ Telegram Stars",
        'ar': "⭐️ نجوم تلغرام",
        'ru': "⭐️ Telegram Stars"
    },
    'btn_cryptobot': {
        'en': "🤖 Crypto Bot (USDT/TON/BTC)",
        'ar': "🤖 كريبتو بوت (USDT/TON/BTC)",
        'ru': "🤖 Crypto Bot (USDT/TON/BTC)"
    },
    'btn_cryptotransfer': {
        'en': "🪙 Crypto Transfer (Manual)",
        'ar': "🪙 تحويل العملات الرقمية (يدوي)",
        'ru': "🪙 Крипто-перевод (Вручную)"
    },
    'crypto_select_coin': {
        'en': "🌍 Select cryptocurrency / اختر العملة الرقمية / Выберите криптовалюту:",
        'ar': "🌍 Select cryptocurrency / اختر العملة الرقمية / Выберите криптовалюту:",
        'ru': "🌍 Select cryptocurrency / اختر العملة الرقمية / Выберите криптовалюту:"
    },
    'crypto_instructions': {
        'en': "🪙 *Crypto Transfer*\n\nSend your payment to the address below:\n\n*Coin:* `{coin}`\n*Address:* `{address}`\n\n⚠️ *IMPORTANT:* You must send the payment *AFTER* opening this menu and seeing this address. If you pay first and then request a deposit, the system will NOT verify it automatically.\n\nAfter sending, reply with the amount you sent in USD (Minimum $1.00):",
        'ar': "🪙 *تحويل العملات الرقمية*\n\nقم بإرسال المبلغ إلى العنوان التالي:\n\n*العملة:* `{coin}`\n*العنوان:* `{address}`\n\n⚠️ *تنبيه هام:* يجب عليك إرسال الأموال *بَعْدَ* فتح هذه القائمة ورؤية هذا العنوان. إذا قمت بالتحويل أولاً ثم طلبت الشحن، فلن يتم قبول العملية تلقائياً.\n\nبعد الإرسال، أرسل المبلغ الذي قمت بتحويله بالدولار (الحد الأدنى $1.00):",
        'ru': "🪙 *Крипто-перевод*\n\nОтправьте оплату на адрес ниже:\n\n*Монета:* `{coin}`\n*Адрес:* `{address}`\n\n⚠️ *ВАЖНО:* Отправляйте платеж только *ПОСЛЕ* открытия этого меню. Если вы оплатите сначала, а потом создадите запрос, система не сможет подтвердить его автоматически.\n\nПосле отправки введите отправленную сумму в USD (Минимум $1.00):"
    },
    'crypto_enter_txid': {
        'en': "✍️ Now enter the Transaction ID (TxID / Hash) to verify payment:",
        'ar': "✍️ الآن أرسل معرف المعاملة (TxID / Hash) للتحقق من الدفع:",
        'ru': "✍️ Теперь введите ID транзакции (TxID / Hash) для проверки:"
    },
    'crypto_deposit_submitted': {
        'en': "✅ *Deposit Submitted!*\n\nYour transaction has been submitted to admins for review. Your balance will be updated once confirmed.",
        'ar': "✅ *تم إرسال الطلب!*\n\nتم تقديم معاملتك للمشرفين للمراجعة. سيتم تحديث رصيدك فور تأكيد المعاملة.",
        'ru': "✅ *Запрос отправлен!*\n\nВаша транзакция отправлена администраторам на проверку. Баланс обновится после подтверждения."
    },
    'crypto_deposit_submitted_auto': {
        'en': "⏳ *Transaction Submitted!*\n\nWe are verifying your deposit automatically on the blockchain. This usually takes a few minutes. Your balance will update automatically.",
        'ar': "⏳ *تم إرسال المعاملة!*\n\nجاري التحقق من عملية الإيداع تلقائياً على الشبكة. يستغرق ذلك عادةً بضع دقائق، وسيتم تحديث رصيدك تلقائياً.",
        'ru': "⏳ *Транзакция отправлена!*\n\nМы проверяем ваш перевод автоматически на блокчейне. Обычно это занимает несколько минут. Ваш баланс обновится автоматически."
    },
    'crypto_already_processed': {
        'en': "❌ This transaction has already been processed or rejected.",
        'ar': "❌ تم معالجة هذه المعاملة أو رفضها بالفعل.",
        'ru': "❌ Эта транзакция уже была обработана или отклонена."
    },
    'crypto_tx_too_old': {
        'en': "❌ *Transaction Rejected!*\n\nThis transaction is older than {hours} hours and cannot be accepted. Please send a new payment and submit the new TxID.",
        'ar': "❌ *تم رفض المعاملة!*\n\nهذه المعاملة أقدم من {hours} ساعة ولا يمكن قبولها. يرجى إرسال دفعة جديدة وإرسال TxID الجديد.",
        'ru': "❌ *Транзакция отклонена!*\n\nЭта транзакция старше {hours} часов и не может быть принята. Отправьте новый платеж и укажите новый TxID."
    },
    'enter_amount_usd': {
        'en': "💵 *Deposit Amount Request*\n\n⚠️ *IMPORTANT:* Please enter the amount you want to deposit in USD (Minimum $1.00) *BEFORE* making any transfer or sending payment.\n\n✍️ Enter the USD amount now:",
        'ar': "💵 *طلب تحديد مبلغ الشحن*\n\n⚠️ *تنبيه هام:* يرجى إدخال وتحديد المبلغ الذي تريد شحنه بالدولار (الحد الأدنى $1.00) *قَبْلَ* القيام بأي عملية تحويل أو إرسال أموال.\n\n✍️ أدخل قيمة المبلغ بالدولار الآن:",
        'ru': "💵 *Сумма пополнения баланса*\n\n⚠️ *ВАЖНО:* Пожалуйста, укажите сумму, которую хотите внести в USD (Минимум $1.00) *ДО* совершения платежа или перевода.\n\n✍️ Введите сумму в USD сейчас:"
    },
    'invalid_amount': {
        'en': "❌ Invalid amount. Please enter a positive number greater than or equal to 1.",
        'ar': "❌ مبلغ غير صالح. يرجى إدخال رقم موجب أكبر من أو يساوي 1.",
        'ru': "❌ Неверная сумма. Введите положительное число не меньше 1."
    },
    'binance_instructions': {
        'en': "🔸 *Binance Pay Deposit*\n\n💰 *Amount:* `${amount:.2f} USD`\n\nClick the button below to pay via Binance. After paying, click the status button below to check and confirm your payment.",
        'ar': "🔸 *الدفع عبر Binance Pay*\n\n💰 *المبلغ:* `${amount:.2f} USD`\n\nاضغط على الزر أدناه لإتمام الدفع عبر بايننس. بعد الدفع، اضغط على زر التحقق أدناه لتأكيد شحنتك.",
        'ru': "🔸 *Пополнение через Binance Pay*\n\n💰 *Сумма:* `${amount:.2f} USD`\n\nНажмите кнопку ниже для оплаты. После оплаты нажмите кнопку проверки, чтобы подтвердить платеж."
    },
    'binance_id_instructions': {
        'en': "🔸 *Binance Pay / ID Transfer*\n\nSend USDT to the Binance Pay ID or Email below:\n\n*Binance ID/Pay/Email:* `{address}`\n\n⚠️ *IMPORTANT:* You must send the payment *AFTER* opening this menu and seeing this address. If you pay first and then request a deposit, the system will NOT verify it automatically.\n\nAfter sending, reply with the amount you sent in USD (Minimum $1.00):",
        'ar': "🔸 *تحويل عبر معرف بايننس / Binance Pay*\n\nأرسل USDT إلى معرف بايننس أو البريد الإلكتروني التالي:\n\n*معرف بايننس/البريد:* `{address}`\n\n⚠️ *تنبيه هام:* يجب عليك إرسال الأموال *بَعْدَ* فتح هذه القائمة ورؤية هذا العنوان. إذا قمت بالتحويل أولاً ثم طلبت الشحن، فلن يتم قبول العملية تلقائياً.\n\nبعد الإرسال، أرسل المبلغ الذي قمت بتحويله بالدولار (الحد الأدنى $1.00):",
        'ru': "🔸 *Перевод через Binance ID / Pay*\n\nОтправьте USDT на Binance Pay ID или Email ниже:\n\n*Binance ID/Pay/Email:* `{address}`\n\n⚠️ *ВАЖНО:* Отправляйте платеж только *ПОСЛЕ* открытия этого меню. Если вы оплатите сначала, а потом создадите запрос, система не сможет подтвердить его автоматически.\n\nПосле отправки введите отправленную сумму в USD (Минимум $1.00):"
    },
    'binance_enter_txid': {
        'en': "✍️ Now enter the Binance Transaction ID / Pay ID / Order ID to verify payment:",
        'ar': "✍️ الآن أرسل معرف المعاملة / معرف الدفع (Pay ID / Transaction ID) للتحقق من الدفع:",
        'ru': "✍️ Теперь введите ID транзакции / Pay ID / Order ID для проверки:"
    },
    'cryptobot_instructions': {
        'en': "🪙 *Crypto Bot Deposit*\n\n💰 *Amount:* `${amount:.2f} USD`\n\nClick the button below to pay via Crypto Bot (USDT). After paying, click the status button below to check and confirm your payment.",
        'ar': "🪙 *شحن عبر كريبتو بوت*\n\n💰 *المبلغ:* `${amount:.2f} USD`\n\nاضغط على الزر أدناه للدفع عبر كريبتو بوت (USDT). بعد إتمام الدفع، اضغط على زر التحقق أدناه لتأكيد شحنتك.",
        'ru': "🪙 *Пополнение через Crypto Bot*\n\n💰 *Сумма:* `${amount:.2f} USD`\n\nНажмите кнопку ниже для оплаты через Crypto Bot (USDT). После оплаты нажмите кнопку проверки, чтобы подтвердить платеж."
    },
    'btn_pay_now': {
        'en': "🔗 Pay Now",
        'ar': "🔗 ادفع الآن",
        'ru': "🔗 Оплатить сейчас"
    },
    'btn_check_payment': {
        'en': "🔄 Check Payment Status",
        'ar': "🔄 تحقق من حالة الدفع",
        'ru': "🔄 Проверить статус платежа"
    },
    'payment_pending_check': {
        'en': "⏳ Checking payment status... please wait.",
        'ar': "⏳ جاري التحقق من حالة الدفع... يرجى الانتظار.",
        'ru': "⏳ Проверка статуса платежа... пожалуйста, подождите."
    },
    'payment_not_found_or_pending': {
        'en': "❌ We couldn't find a completed payment for this transaction yet. Please make sure you paid first.",
        'ar': "❌ لم نجد دفعة مكتملة لهذه المعاملة بعد. يرجى التأكد من الدفع أولاً.",
        'ru': "❌ Мы еще не обнаружили оплату для этой транзакции. Убедитесь, что оплатили её."
    },
    'payment_success': {
        'en': "✅ *Deposit Successful!*\n\n💰 `${amount:.2f} USD` has been added to your balance. Your new balance is `${new_balance:.2f} USD`.",
        'ar': "✅ *تم الشحن بنجاح!*\n\n💰 تم إضافة `${amount:.2f} USD` لرصيدك. رصيدك الجديد هو `${new_balance:.2f} USD`.",
        'ru': "✅ *Баланс успешно пополнен!*\n\n💰 `${amount:.2f} USD` зачислено на ваш счет. Ваш новый баланс: `${new_balance:.2f} USD`."
    },
    'stars_invoice_title': {
        'en': "Deposit ${amount:.2f} USD",
        'ar': "شحن ${amount:.2f} USD",
        'ru': "Пополнение на ${amount:.2f} USD"
    },
    'stars_invoice_desc': {
        'en': "Top up your shop balance with ${amount:.2f} USD via Telegram Stars.",
        'ar': "شحن رصيد المتجر بقيمة ${amount:.2f} USD عبر نجوم التلغرام.",
        'ru': "Пополнение баланса магазина на ${amount:.2f} USD через Telegram Stars."
    },
    'force_join_msg': {
        'en': "📢 *Subscription Required*\n\nYou must join our official channel(s) to use this bot.\n\nPlease click the channel button(s) below to join, then press **✅ Verify Subscription** when done.",
        'ar': "📢 *اشتراك إجباري في القنوات*\n\nعذراً، يجب عليك الانضمام إلى قنواتنا الرسمية لاستخدام البوت.\n\nيرجى الضغط على أزرار القنوات أدناه للانضمام، ثم الضغط على **✅ تحقق من الاشتراك** بعد الانضمام.",
        'ru': "📢 *Обязательная подписка*\n\nВы должны подписаться на наши официальные каналы, чтобы использовать этого бота.\n\nПожалуйста, нажмите кнопки каналов ниже, чтобы подписаться, а затем нажмите **✅ Проверить подписку**."
    },
    'admin_panel': {
        'en': "⚙️ *Admin Panel*\nChoose an action:",
        'ar': "⚙️ *لوحة التحكم للمشرف*\nاختر إجراءً للقيام به:",
        'ru': "⚙️ *Админ-панель*\nВыберите действие:"
    },
    'payment_rejected': {
        'en': "❌ *Deposit Rejected!*\n\nYour transaction of `${amount:.2f} USD` has been rejected by the admin. Please make sure the TxID and amount are correct.",
        'ar': "❌ *تم رفض الشحن!*\n\nتم رفض معاملتك بقيمة `${amount:.2f} USD` من قبل المشرف. يرجى التأكد من صحة معرف المعاملة (TxID) والمبلغ.",
        'ru': "❌ *Пополнение отклонено!*\n\nВаш платеж на сумму `${amount:.2f} USD` был отклонен администратором. Пожалуйста, убедитесь в правильности ID транзакции (TxID) и суммы."
    },
    'btn_notify_stock': {
        'en': "🔔 Notify Me When Available",
        'ar': "🔔 أبلغني عند التوفر",
        'ru': "🔔 Уведомить о наличии"
    },
    'btn_cancel_notify_stock': {
        'en': "🔕 Cancel Notification",
        'ar': "🔕 إلغاء الإشعار",
        'ru': "🔕 Отменить уведомление"
    },
    'notify_stock_subscribed': {
        'en': "🔔 You will be notified when *{name}* is back in stock!",
        'ar': "🔔 سيتم إشعارك عند توفر *{name}* مجدداً!",
        'ru': "🔔 Вы получите уведомление, когда *{name}* появится в наличии!"
    },
    'notify_stock_unsubscribed': {
        'en': "🔕 Notification cancelled for *{name}*.",
        'ar': "🔕 تم إلغاء الإشعار لمنتج *{name}*.",
        'ru': "🔕 Уведомление отменено для *{name}*."
    },
    'notify_stock_available': {
        'en': "🔔 *Product Available!*\n\n🛍 *{name}* is back in stock!\n📦 *Available:* `{stock}` items\n💵 *Price:* `${price:.2f} USD`\n\nHurry up before it runs out! 🏃",
        'ar': "🔔 *المنتج متوفر!*\n\n🛍 *{name}* عاد للمخزون!\n📦 *المتوفر:* `{stock}` قطعة\n💵 *السعر:* `${price:.2f} USD`\n\nأسرع قبل النفاذ! 🏃",
        'ru': "🔔 *Товар в наличии!*\n\n🛍 *{name}* снова в наличии!\n📦 *Доступно:* `{stock}` шт.\n💵 *Цена:* `${price:.2f} USD`\n\nУспейте купить! 🏃"
    },
    'btn_generate_api_key': {
        'en': "➕ Generate API Key",
        'ar': "➕ إنشاء مفتاح API",
        'ru': "➕ Создать API ключ"
    },
    'btn_regenerate_api_key': {
        'en': "🔄 Regenerate API Key",
        'ar': "🔄 تجديد مفتاح API",
        'ru': "🔄 Обновить API ключ"
    },
    'btn_revoke_api_key': {
        'en': "❌ Delete API Key",
        'ar': "❌ حذف مفتاح API",
        'ru': "❌ Удалить API ключ"
    },
    'btn_download_api_doc': {
        'en': "📄 Download API Documentation",
        'ar': "📄 تحميل ملف توثيق API",
        'ru': "📄 Скачать документацию API"
    },
    'reseller_api_info_no_key': {
        'en': "🔑 *Reseller API*\n\nResellers can use our HTTP API to integrate our products into their own bots and sell them automatically.\n\n⚠️ You don't have an API Key generated yet. Click the button below to generate one.",
        'ar': "🔑 *بوابة الموزعين (API)*\n\nيمكن للموزعين استخدام الـ API لربط متجرنا ببوتاتهم الخاصة وبيع المنتجات تلقائياً.\n\n⚠️ ليس لديك مفتاح API حالياً. اضغط على الزر أدناه لإنشاء مفتاحك الخاص.",
        'ru': "🔑 *API для реселлеров*\n\nРеселлеры могут использовать наше API для интеграции продуктов в свои боты.\n\n⚠️ У вас еще нет API-ключа. Нажмите кнопку ниже, чтобы создать его."
    },
    'reseller_api_info_has_key': {
        'en': "🔑 *Reseller API*\n\nYour API Key:\n`{api_key}`\n\n🌐 *API Base URL*:\n`{api_base_url}`\n\n📌 *API Endpoints*:\n• `GET` `/api/products` - Product list\n• `POST` `/api/buy` - Purchase product\n\n⚠️ *Do not share this key with anyone!*",
        'ar': "🔑 *بوابة الموزعين (API)*\n\nمفتاح الـ API الخاص بك:\n`{api_key}`\n\n🌐 *رابط الـ API الأساسي*:\n`{api_base_url}`\n\n📌 *المسارات (Endpoints)*:\n• `GET` `/api/products` - عرض المنتجات والمخزون\n• `POST` `/api/buy` - شراء منتج تلقائياً\n\n⚠️ *لا تشارك هذا المفتاح مع أي شخص!*",
        'ru': "🔑 *API для реселлеров*\n\nВаш API-ключ:\n`{api_key}`\n\n🌐 *Базовый URL-адрес API*:\n`{api_base_url}`\n\n📌 *Пути (Endpoints)*:\n• `GET` `/api/products` - Список товаров\n• `POST` `/api/buy` - Покупка товара\n\n⚠️ *Никому не передавайте этот ключ!*"
    },
    'btn_admin_pull_external_product': {
        'en': "🔌 Pull External Product",
        'ar': "🔌 سحب منتج خارجي",
        'ru': "🔌 Импорт внешнего товара"
    },
    'prov_url_prompt': {
        'en': "🔌 Enter the Provider Bot's Base URL (e.g. `https://other-bot.up.railway.app`):",
        'ar': "🔌 أدخل رابط البوت الخارجي (مثال: `https://other-bot.up.railway.app`):",
        'ru': "🔌 Введите базовый URL-адрес внешнего бота:"
    },
    'prov_key_prompt': {
        'en': "🔑 Enter your Reseller API Key for this provider:",
        'ar': "🔑 أدخل مفتاح API الخاص بك لهذا الموزع:",
        'ru': "🔑 Введите ваш API-ключ реселлера:"
    },
    'prov_select_product': {
        'en': "📦 Select a product to pull/import:",
        'ar': "📦 اختر المنتج الذي تريد سحبه/استيراده:",
        'ru': "📦 Выберите товар для импорта:"
    },
    'prov_price_prompt': {
        'en': "💵 Enter the price you want to sell this product for locally (Provider Price: `{price:.2f}`):",
        'ar': "💵 أدخل السعر الذي تريد بيع هذا المنتج به محلياً (سعر المصدر: `{price:.2f}`):",
        'ru': "💵 Введите локальную цену продажи (Цена источника: `{price:.2f}`):"
    },
    'prov_invalid_price': {
        'en': "❌ Invalid price. Please enter a valid positive number:",
        'ar': "❌ سعر غير صالح. يرجى إدخال رقم موجب صالح:",
        'ru': "❌ Неверная цена. Пожалуйста, введите положительное число:"
    },
    'prov_import_success': {
        'en': "✅ Product *{name}* successfully imported! Local Price: `{price:.2f}`",
        'ar': "✅ تم سحب واستيراد المنتج *{name}* بنجاح! السعر المحلي: `{price:.2f}`",
        'ru': "✅ Товар *{name}* успешно импортирован! Локальная цена: `{price:.2f}`"
    },
    'prov_use_saved': {
        'en': "🔌 Saved Provider bot found: `{url}`\n\nDo you want to use the saved provider or set up a new one?",
        'ar': "🔌 تم العثور على موزع محفوظ: `{url}`\n\nهل تريد استخدامه أم إعداد موزع جديد؟",
        'ru': "🔌 Найден сохраненный провайдер: `{url}`\n\nИспользовать его или настроить новый?"
    },
    'btn_use_saved': {
        'en': "🔄 Use Saved Provider",
        'ar': "🔄 استخدام الموزع المحفوظ",
        'ru': "🔄 إستخدام المحفوظ"
    },
    'btn_setup_new_prov': {
        'en': "⚙️ Setup New Provider",
        'ar': "⚙️ إعداد موزع جديد",
        'ru': "⚙️ إعداد جديد"
    }
}

def get_text(key, lang='en', **kwargs):
    if key not in LOCALIZATION:
        return f"[{key}]"
    text = LOCALIZATION[key].get(lang, LOCALIZATION[key].get('en', f"[{key}]"))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
