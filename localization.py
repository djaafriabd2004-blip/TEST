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
    'btn_other_payment_methods': {
        'en': "💳 Other Payment Methods",
        'ar': "💳 طرق دفع أخرى",
        'ru': "💳 Другие способы оплаты"
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
    'btn_my_preorders': {
        'en': "⏳ My Pre-orders",
        'ar': "⏳ حجوزاتي",
        'ru': "⏳ Мои предзаказы"
    },
    'btn_preorder': {
        'en': "⏳ Reserve / Pre-order",
        'ar': "⏳ حجز المنتج مسبقاً",
        'ru': "⏳ Забронировать"
    },
    'preorder_title': {
        'en': "⏳ *Pre-order Reservation*\n\n🛒 *Product:* {name}\n💵 *Price per item:* `${price:.2f} USD`\n\nThis product is currently out of stock. You can reserve it now, and the bot will automatically buy and deliver it to you as soon as new stock is added!\n\n✍️ Enter quantity you want to reserve:",
        'ar': "⏳ *حجز المنتج مسبقاً*\n\n🛒 *المنتج:* {name}\n💵 *سعر القطعة:* `${price:.2f} USD`\n\nهذا المنتج غير متوفر حالياً. يمكنك حجزه الآن وسيقوم البوت تلقائياً بشرائه وتسليمه لك فور توفر مخزون جديد!\n\n✍️ أرسل الكمية التي ترغب في حجزها:",
        'ru': "⏳ *Предзаказ товара*\n\n🛒 *Товар:* {name}\n💵 *Цена за шт:* `${price:.2f} USD`\n\nЭтого товара сейчас нет в наличии. Вы можете забронировать его, и бот автоматически выдаст его вам при пополнении!\n\n✍️ Введите количество для бронирования:"
    },
    'preorder_success': {
        'en': "✅ *Product Reserved Successfully!*\n\n💰 **`${amount:.2f} USD`** has been locked from your balance. The bot will deliver the items immediately upon restock.\n\n💡 You can view or cancel your reservation in the **My Pre-orders** section.",
        'ar': "✅ *تم حجز المنتج بنجاح!*\n\n💰 تم تعليق مبلغ **`${amount:.2f} USD`** من رصيدك. وسيقوم البوت بتسليم المنتجات لك فور توفرها بالمخزون تلقائياً.\n\n💡 يمكنك استعراض حجزك أو إلغاؤه واستعادة الرصيد من قائمة **حجوزاتي**.",
        'ru': "✅ *Товар успешно забронирован!*\n\n💰 Сумма **`${amount:.2f} USD`** была заблокирована на вашем балансе. Бот выдаст товар сразу после пополнения.\n\n💡 Вы можете отменить предзаказ в меню **Мои предзаказы**."
    },
    'my_preorders_title': {
        'en': "⏳ *Your Active Pre-orders:*",
        'ar': "⏳ *حجوزاتك النشطة المعلقة:*",
        'ru': "⏳ *Ваши активные предзаказы:*"
    },
    'my_preorders_empty': {
        'en': "📭 You don't have any active pre-orders.",
        'ar': "📭 ليس لديك أي حجوزات نشطة حالياً.",
        'ru': "📭 У вас нет активных предзаказов."
    },
    'preorder_item': {
        'en': "⏳ *Pre-order #{id}*\n🛍️ *Product:* {name}\n📦 *Quantity:* `{qty}`\n💰 *Locked Amount:* `${price:.2f} USD`\n📅 *Date:* {date}\n\n",
        'ar': "⏳ *حجز #{id}*\n🛍️ *المنتج:* {name}\n📦 *الكمية:* `{qty}`\n💰 *المبلغ المعلق:* `${price:.2f} USD`\n📅 *التاريخ:* {date}\n\n",
        'ru': "⏳ *Предзаказ #{id}*\n🛍️ *Товар:* {name}\n📦 *Количество:* `{qty}`\n💰 *Заблокировано:* `${price:.2f} USD`\n📅 *Дата:* {date}\n\n"
    },
    'btn_cancel_preorder': {
        'en': "❌ Cancel Reservation & Refund",
        'ar': "❌ إلغاء الحجز واسترداد الرصيد",
        'ru': "❌ Отменить бронь и вернуть"
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
        'en': "🔗 *Referral System*\n\nShare your referral link with friends. You will receive a fixed reward of **`${bonus} USD`** in your balance once your invited friend makes their first purchase inside the bot!\n\n👥 *Your Referrals:* `{count}`\n💰 *Total Earned:* `${earned:.2f} USD`\n\n📋 *Your Link:* `{link}`",
        'ar': "🔗 *نظام الإحالات*\n\nشارك رابط الإحالة الخاص بك مع أصدقائك. ستحصل على مكافأة ثابتة بقيمة **`{bonus} USD`** في محفظتك مباشرة بمجرد قيام الصديق الذي قمت بدعوته بإجراء أول عملية شراء له داخل البوت!\n\n👥 *عدد إحالاتك:* `{count}`\n💰 *إجمالي الأرباح:* `${earned:.2f} USD`\n\n📋 *رابطك:* `{link}`",
        'ru': "🔗 *Реферальная система*\n\nПоделитесь своей реферальной ссылкой. Вы получите фиксированное вознаграждение в размере **`${bonus} USD`** на свой баланс, как только приглашенный вами друг совершит свою первую покупку в боте!\n\n👥 *Ваши рефералы:* `{count}`\n💰 *Всего заработано:* `${earned:.2f} USD`\n\n📋 *Ваша ссылка:* `{link}`"
    },
    'referral_new_user_joined': {
        'en': "🎉 *Referral First Purchase Reward!*\n\nUser *{name}* whom you invited has made their first purchase! A fixed bonus of **`${bonus} USD`** has been successfully credited to your wallet balance.",
        'ar': "🎉 *مكافأة أول شراء للإحالة!*\n\nقام المستخدم *{name}* (الذي قمت بدعوته) بإجراء أول عملية شراء له بالبوت! تم بنجاح إضافة مكافأة ثابتة بقيمة **`{bonus} USD`** إلى محفظتك بالبوت.",
        'ru': "🎉 *Бонус за первую покупку реферала!*\n\nПриглашенный вами пользователь *{name}* совершил свою первую покупку! Фиксированный бонус в размере **`${bonus} USD`** успешно зачислен на баланс вашего кошелька."
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
        'en': "🔶 *Binance Pay Order Created!*\n\n1. Click the button below to pay via Binance Pay.\n2. Once paid, click **Check Payment Status** to receive your product.",
        'ar': "🔶 *تم إنشاء طلب الدفع عبر Binance Pay!*\n\n1. اضغط على الزر أدناه للدفع عبر تطبيق بايننس.\n2. بعد إتمام الدفع، اضغط على **التحقق من حالة الدفع** لاستلام منتجك فوراً.",
        'ru': "🔶 *Счет в Binance Pay создан!*\n\n1. Нажмите кнопку ниже для оплаты через Binance Pay.\n2. После оплаты нажмите **Проверить статус платежа**, чтобы получить товар."
    },
    'checkout_binance_id_instructions': {
        'en': "🔶 *Binance Pay / ID Purchase*\n\n🛒 *Product:* {name} (x{qty})\n💵 *Total Price:* `${price:.2f} USD`\n\nSend payment to our Binance Pay ID or Email below:\n\n*Binance ID/Pay/Email:* `{address}`\n\n⚠️ *IMPORTANT:* Send the payment *AFTER* opening this menu. If you pay first and then click buy, verification may fail.\n\n👉 Press **Done / Verify** below to enter your transaction ID and claim your product:",
        'ar': "🔶 *شراء مباشر عبر معرف بايننس / Binance ID*\n\n🛒 *المنتج:* {name} (الكمية {qty})\n💵 *السعر الإجمالي:* `${price:.2f} USD`\n\nأرسل المبلغ المطلوب إلى معرف بايننس أو البريد التالي:\n\n*معرف بايننس/البريد:* `{address}`\n\n⚠️ *تنبيه هام:* يجب عليك إرسال الأموال *بَعْدَ* فتح هذه القائمة. إذا قمت بالتحويل أولاً ثم طلبت الشراء، فقد تفشل العملية تلقائياً.\n\n👉 اضغط على **تم التحويل / التحقق** أدناه لإدخال معرف المعاملة واستلام منتجك:",
        'ru': "🔶 *Покупка через Binance ID / Pay*\n\n🛒 *Товар:* {name} (x{qty})\n💵 *Итого:* `${price:.2f} USD`\n\nОтправьте USDT на Binance Pay ID или Email ниже:\n\n*Binance ID/Pay/Email:* `{address}`\n\n⚠️ *ВАЖНО:* Отправляйте платеж только *ПОСЛЕ* открытия этого меню.\n\n👉 Нажмите кнопку ниже, чтобы ввести ID транзакции:"
    },
    'checkout_binance_enter_txid': {
        'en': "✍️ Please enter the Binance Transaction ID / Pay ID / Order ID for this purchase:",
        'ar': "✍️ يرجى إدخال معرف المعاملة / معرف الدفع (Pay ID / Transaction ID) الخاص بهذه العملية:",
        'ru': "✍️ Пожалуйста, введите ID транзакции / Pay ID / Order ID для этой покупки:"
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
    'checkout_refund_out_of_stock': {
        'en': "❌ *Product Out of Stock!*\n\nWe apologize, but this product went out of stock right during payment processing. To secure your money, **`${amount:.2f} USD`** has been automatically credited to your wallet balance.",
        'ar': "❌ *نفد المنتج من المخزون!*\n\nنعتذر منك، لقد نفد هذا المنتج تماماً أثناء معالجة الدفع. وحفاظاً على أموالك، تم تلقائياً شحن وإيداع مبلغ **`${amount:.2f} USD`** في رصيد محفظتك بالبوت للاستخدام لاحقاً.",
        'ru': "❌ *Товара нет в наличии!*\n\nПриносим извинения, товар закончился во время обработки платежа. Для безопасности ваших средств **`${amount:.2f} USD`** автоматически зачислены на баланс вашего кошелька."
    },
    'checkout_partial_delivery_refund': {
        'en': "⚠️ *Partial Delivery & Refund*\n\n🛒 *Fitted:* {actual} of {qty} items delivered.\n📦 *Out of Stock:* {diff} items are unavailable.\n\n💰 **`${refund:.2f} USD`** has been refunded and added to your wallet balance for the missing items.",
        'ar': "⚠️ *تسليم جزئي وتعويض الرصيد المتبقي*\n\n🛒 *المُسلّم:* تم تسليم {actual} من أصل {qty} قطع متوفرة.\n📦 *غير متوفر:* {diff} قطع لم تكن متاحة في المخزون.\n\n💰 تم إرجاع قيمة القطع الناقصة **`${refund:.2f} USD`** وتلقائياً إيداعها في رصيد محفظتك بالبوت.",
        'ru': "⚠️ *Частичная доставка и возврат средств*\n\n🛒 *Доставлено:* {actual} из {qty} шт.\n📦 *Нет в наличии:* {diff} шт. недоступны.\n\n💰 **`${refund:.2f} USD`** были возвращены и добавлены на баланс вашего кошелька за недостающие товары."
    },
    'provider_insufficient_balance': {
        'en': "❌ *Delivery Error!*\n\nWe apologize, but we are currently facing a technical issue delivering this product. Please contact the administrator at @{admin_username} to receive your product manually.",
        'ar': "❌ *خطأ في تسليم المنتج!*\n\nنعتذر منك، نواجه حالياً مشكلة تقنية في تسليم هذا المنتج. يرجى التواصل مع إدارة البوت عبر الحساب التالي: @{admin_username} ليتم تسليمك منتجك يدوياً فوراً.",
        'ru': "❌ *Ошибка доставки!*\n\nПриносим извинения, возникла техническая проблема с выдачей товара. Пожалуйста, свяжитесь с администратором @{admin_username} для ручной выдачи."
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
    'btn_admin_pricing_strategy': {
        'en': "🏷️ Pricing & Margin Strategy",
        'ar': "🏷️ استراتيجية التسعير والربح",
        'ru': "🏷️ Стратегия цен и маржи"
    },
    'btn_pricing_type_fixed': {
        'en': "💵 Fixed Price (Legacy)",
        'ar': "💵 سعر بيع ثابت (النظام القديم)",
        'ru': "💵 Фиксированная цена"
    },
    'btn_pricing_type_margin_fixed': {
        'en': "📈 Fixed Profit Margin ($ USD)",
        'ar': "📈 هامش ربح ثابت بالدولار ($)",
        'ru': "📈 Наценка в $ (USD)"
    },
    'btn_pricing_type_margin_percent': {
        'en': "📊 Percentage Margin (% Markup)",
        'ar': "📊 هامش ربح بنسبة مئوية (%)",
        'ru': "📊 Наценка в процентах (%)"
    },
    'pricing_select_strategy_title': {
        'en': "🏷️ *Choose Pricing Strategy for Product:*\n\n📦 *Product:* `{name}`\n💵 *Provider Wholesale Cost:* `${cost:.2f} USD`\n\n1️⃣ **Fixed Price:** Sells at a constant price.\n2️⃣ **Fixed Margin ($):** Automatically adds a fixed markup on top of provider cost.\n3️⃣ **Percentage Margin (%):** Automatically adds a % markup with floor protection.",
        'ar': "🏷️ *اختر طريقة التسعير لهذا المنتج:*\n\n📦 *المنتج:* `{name}`\n💵 *سعر التكلفة من المزود:* `${cost:.2f} USD`\n\n1️⃣ **سعر بيع ثابت:** تحدد سعراً ثابتاً ومستقراً للمنتج.\n2️⃣ **هامش ربح بالدولار ($):** يضاف مبلغ ربح ثابت فوق تكلفة المزود تلقائياً.\n3️⃣ **هامش ربح بنسبة (%):** تضاف نسبة ربح مئوية فوق تكلفة المزود مع حد أدنى محمي.",
        'ru': "🏷️ *Выберите стратегию ценообразования:*\n\n📦 *Товар:* `{name}`\n💵 *Оптовая цена поставщика:* `${cost:.2f} USD`"
    },
    'pricing_prompt_fixed': {
        'en': "💵 *Enter the fixed selling price (in USD):*\n(Example: `5.00` or `7.50`)",
        'ar': "💵 *أدخل سعر البيع الثابت للمنتج (بالدولار):*\n(مثال: `5.00` أو `7.50`)",
        'ru': "💵 *Введите фиксированную цену продажи (в USD):*\n(Пример: `5.00` или `7.50`)"
    },
    'pricing_prompt_margin_fixed': {
        'en': "📈 *Enter the fixed profit margin ($ USD) to add on top of provider cost:*\n\n💵 Current provider cost: `${cost:.2f}`\n(Example: If you enter `1.50` and provider cost is `$5.00`, selling price will be `$6.50`)",
        'ar': "📈 *أدخل قيمة هامش الربح بالدولار ($) الذي سيضاف فوق تكلفة المزود:*\n\n💵 تكلفة المزود الحالية: `${cost:.2f}`\n(مثال: إذا أدخلت `1.50` وكان سعر المزود `$5.00`، سيصبح سعر البيع `$6.50`)",
        'ru': "📈 *Введите сумму наценки ($ USD), которая будет добавлена к стоимости поставщика:*\n(Пример: `1.50`)"
    },
    'pricing_prompt_margin_percent': {
        'en': "📊 *Enter the profit margin percentage (%) to add on top of provider cost:*\n\n💵 Current provider cost: `${cost:.2f}`\n(Example: If you enter `20` and provider cost is `$5.00`, selling price will be `$6.00`)",
        'ar': "📊 *أدخل نسبة هامش الربح المئوية (%) التي ستضاف فوق تكلفة المزود:*\n\n💵 تكلفة المزود الحالية: `${cost:.2f}`\n(مثال: إذا أدخلت `20` وكان سعر المزود `$5.00`، سيصبح سعر البيع `$6.00`)",
        'ru': "📊 *Введите процент наценки (%), который будет добавлен к стоимости поставщика:*\n(Пример: `20`)"
    },
    'pricing_prompt_min_price': {
        'en': "🛡️ *Enter the Minimum Protected Floor Price (in USD):*\n\n📌 *Protection:* Ensures the selling price never drops below this number even if the provider lowers their cost.\n(Send `0` or click Skip if you do not want an additional floor price, or enter e.g. `{suggested:.2f}`):",
        'ar': "🛡️ *أدخل الحد الأدنى المحمي للسعر (Minimum Protected Floor Price):*\n\n📌 **الفائدة:** يضمن ألا ينزل سعر البيع في البوت عن هذا الرقم أبداً حتى لو انخفض سعر المزود.\n(أرسل `0` أو اضغط تخطي إذا كنت لا تريد حداً أدنى إضافياً، أو أدخل مبلغاً مثل `{suggested:.2f}`):",
        'ru': "🛡️ *Введите минимальную защищенную цену (в USD):*\n(Отправьте `0` или нажмите пропустить, или введите `{suggested:.2f}`):"
    },
    'btn_skip_floor_price': {
        'en': "⏭️ Skip Floor Price (Use 0.00)",
        'ar': "⏭️ تخطي (بدون حد أدنى)",
        'ru': "⏭️ Пропустить"
    },
    'pricing_strategy_updated': {
        'en': "✅ *Pricing strategy updated successfully!*\n\n📦 *Product:* `{name}`\n🏷️ *Strategy:* `{type_name}`\n💵 *Calculated Selling Price:* `${price:.2f} USD`",
        'ar': "✅ *تم تحديث استراتيجية التسعير للمنتج بنجاح!*\n\n📦 *المنتج:* `{name}`\n🏷️ *الاستراتيجية:* `{type_name}`\n💵 *سعر البيع المحسوب:* `${price:.2f} USD`",
        'ru': "✅ *Стратегия ценообразования успешно обновлена!*\n\n📦 *Товар:* `{name}`\n🏷️ *Стратегия:* `{type_name}`\n💵 *Рассчитанная цена:* `${price:.2f} USD`"
    },
    'prov_import_success': {
        'en': "✅ Product *{name}* successfully imported! Local Price: `${price:.2f} USD`",
        'ar': "✅ تم سحب واستيراد المنتج *{name}* بنجاح! سعر البيع: `${price:.2f} USD`",
        'ru': "✅ Товар *{name}* успешно импортирован! Цена: `${price:.2f} USD`"
    },
    'prov_list_title': {
        'en': "🔌 *API Providers Management*\n\nSelect a provider from the list to pull products or delete them, or configure a new provider bot:",
        'ar': "🔌 *إدارة موزعي الـ API*\n\nاختر أحد الموزعين من القائمة لسحب المنتجات أو حذفه، أو قم بإعداد بوت موزع جديد:",
        'ru': "🔌 *Управление API провайдерами*\n\nВыберите провайдера для импорта или удаления, или настройте нового:"
    },
    'prov_manage_title': {
        'en': "🔌 *Manage Provider:* `{url}`\n\nChoose an action below for this provider bot:",
        'ar': "🔌 *إدارة الموزع:* `{url}`\n\nاختر أحد الإجراءات لهذا الموزع:",
        'ru': "🔌 *Управление провайдером:* `{url}`\n\nВыберите действие:"
    },
    'prov_use_saved': {
        'en': "🔌 Saved Provider bot found: `{url}`\n\nDo you want to use the saved provider or set up a new one?",
        'ar': "🔌 تم العثور على موزع محفوظ: `{url}`\n\nهل تريد استخدامه أم إعداد موزع جديد؟",
        'ru': "🔌 Найден сохраненный провайдер: `{url}`\n\nИспользовать его или настроить новый?"
    },
    'btn_use_saved': {
        'en': "🔄 Use Saved Provider",
        'ar': "🔄 استخدام الموزع المحفوظ",
        'ru': "🔄 Использовать сохраненного"
    },
    'btn_setup_new_prov': {
        'en': "⚙️ Setup New Provider",
        'ar': "⚙️ إعداد موزع جديد",
        'ru': "⚙️ Настроить нового"
    },
    # Admin Reply Keyboards
    'btn_admin_stats': {
        'en': "📊 Statistics",
        'ar': "📊 الإحصائيات",
        'ru': "📊 Статистика"
    },
    'btn_admin_inspect_user': {
        'en': "🔍 Inspect User",
        'ar': "🔍 فحص مستخدم",
        'ru': "🔍 Проверка пользователя"
    },
    'btn_admin_manage_products': {
        'en': "📦 Manage Products",
        'ar': "📦 إدارة المنتجات",
        'ru': "📦 Управление товарами"
    },
    'btn_admin_add_stock': {
        'en': "📥 Add Stock",
        'ar': "📥 إضافة ستوك",
        'ru': "📥 Добавить сток"
    },
    'btn_admin_bulk_stock': {
        'en': "📦 Bulk Add Stock",
        'ar': "📦 إضافة ستوك جماعي",
        'ru': "📦 Массовое добавление"
    },
    'btn_admin_pending_deposits': {
        'en': "⏳ Pending Deposits",
        'ar': "⏳ الإيداعات المعلقة",
        'ru': "⏳ Ожидающие платежи"
    },
    'btn_admin_manage_preorders': {
        'en': "⏳ Manage Pre-orders",
        'ar': "⏳ إدارة الحجوزات",
        'ru': "⏳ Управление предзаказами"
    },
    'btn_admin_channels': {
        'en': "📢 Channels Settings",
        'ar': "📢 إعدادات القنوات",
        'ru': "📢 Настройки каналов"
    },
    'btn_admin_support': {
        'en': "🎧 Support Settings",
        'ar': "🎧 إعدادات الدعم",
        'ru': "🎧 Настройки поддержки"
    },
    'btn_admin_charge': {
        'en': "💳 Charge Section",
        'ar': "💳 إعدادات الدفع",
        'ru': "💳 Настройки оплаты"
    },
    'btn_admin_referral': {
        'en': "👥 Referral System",
        'ar': "👥 نظام الإحالة",
        'ru': "👥 Реферальная система"
    },
    'btn_admin_api_keys': {
        'en': "🔑 API Keys Settings",
        'ar': "🔑 إعدادات مفاتيح API",
        'ru': "🔑 Настройки API ключей"
    },
    'btn_admin_manage_users': {
        'en': "👥 Manage Users",
        'ar': "👥 إدارة المستخدمين",
        'ru': "👥 Управление пользователями"
    },
    'btn_admin_ban_system': {
        'en': "🚫 Ban / Unban System",
        'ar': "🚫 نظام الحظر / فك الحظر",
        'ru': "🚫 Система банов"
    },
    'btn_admin_broadcast': {
        'en': "📣 Broadcast",
        'ar': "📣 رسالة جماعية",
        'ru': "📣 Рассылка"
    },
    'btn_admin_edit_store_name': {
        'en': "✏️ Edit Store Name",
        'ar': "✏️ تعديل اسم المتجر",
        'ru': "✏️ Изменить имя магазина"
    },
    'btn_admin_button_emojis': {
        'en': "🎨 Button Emojis",
        'ar': "🎨 إيموجيات الأزرار",
        'ru': "🎨 Эмодзи кнопок"
    },
    'btn_admin_pull_external': {
        'en': "🔌 Pull External Product",
        'ar': "🔌 سحب منتج خارجي",
        'ru': "🔌 Импорт товара"
    },
    'btn_admin_back_to_menu': {
        'en': "🔙 Back to Main Menu",
        'ar': "🔙 العودة للقائمة الرئيسية",
        'ru': "🔙 Главное меню"
    },
    # Admin User Management Submenus
    'btn_admin_custom_prices': {
        'en': "🎯 Custom Product Prices",
        'ar': "🎯 تخصيص أسعار المنتجات",
        'ru': "🎯 Индивидуальные цены"
    },
    'btn_admin_user_discounts': {
        'en': "👥 User Discounts",
        'ar': "👥 خصومات المستخدمين",
        'ru': "👥 Скидки пользователей"
    },
    'btn_admin_edit_balances': {
        'en': "💰 Edit Balances",
        'ar': "💰 تعديل الأرصدة",
        'ru': "💰 Изменить баланс"
    },
    'btn_admin_show_balances': {
        'en': "👥 Show Balances",
        'ar': "👥 عرض الأرصدة",
        'ru': "👥 Показать балансы"
    },
    'btn_admin_add_custom_price': {
        'en': "➕ Set Custom Price",
        'ar': "➕ تخصيص سعر لمنتج",
        'ru': "➕ Установить спеццену"
    },
    'btn_admin_add_discount': {
        'en': "➕ Add Discount",
        'ar': "➕ إضافة خصم جديد",
        'ru': "➕ Добавить скидку"
    },
    'btn_admin_back_to_panel': {
        'en': "🔙 Back to Admin Menu",
        'ar': "🔙 العودة للوحة الإدارة",
        'ru': "🔙 В админ-панель"
    },
    'btn_admin_back': {
        'en': "🔙 Back",
        'ar': "🔙 رجوع",
        'ru': "🔙 Назад"
    },
    'btn_admin_delete': {
        'en': "🗑️ Delete",
        'ar': "🗑️ حذف",
        'ru': "🗑️ Удалить"
    },
    # Custom Product Prices Texts
    'admin_custom_prices_title': {
        'en': "🎯 *Custom Product Prices Configuration*\n\nHere you can set custom fixed prices for specific users on specific products. When configured, the user will pay this exact custom price instead of the standard price.",
        'ar': "🎯 *إدارة الأسعار المخصصة للمستخدمين*\n\nهنا يمكنك تحديد سعر مخصص وثابت لمستخدم معين على منتج محدد. سيتم محاسبة هذا المستخدم بالسعر المخصص له بدلاً من السعر العام للمنتج.",
        'ru': "🎯 *Настройка индивидуальных цен*\n\nЗдесь вы можете установить специальную цену на конкретный товар для выбранного пользователя. При покупке пользователю будет рассчитана указанная цена."
    },
    'admin_custom_price_user_prompt': {
        'en': "🎯 *Set Custom Price:*\n\nPlease send the **User ID** (e.g. `123456789`) of the user you want to set a custom price for:",
        'ar': "🎯 *تخصيص سعر لمستخدم:*\n\nيرجى إرسال **معرف المستخدم (User ID)** (مثال: `123456789`):",
        'ru': "🎯 *Установка спеццены:*\n\nОтправьте **ID пользователя** (например, `123456789`):"
    },
    'admin_custom_price_select_prod': {
        'en': "📦 *Select the Product* to set custom price for user `{user_id}` ({user_name}):",
        'ar': "📦 *اختر المنتج* لضبط السعر المخصص للمستخدم `{user_id}` ({user_name}):",
        'ru': "📦 *Выберите товар* для спеццены пользователю `{user_id}` ({user_name}):"
    },
    'admin_custom_price_val_prompt': {
        'en': "💵 Product: *{product_name}*\n📊 Original Price: `${original_price:.2f} USD`\n👤 User: `{user_id}`\n\n✍️ Enter the **new custom price** in USD (e.g. `4.50`):",
        'ar': "💵 المنتج: *{product_name}*\n📊 السعر الأصلي: `${original_price:.2f} USD`\n👤 المستخدم: `{user_id}`\n\n✍️ أدخل **السعر المخصص الجديد** بالدولار (مثال: `4.50`):",
        'ru': "💵 Товар: *{product_name}*\n📊 Обычная цена: `${original_price:.2f} USD`\n👤 Пользователь: `{user_id}`\n\n✍️ Введите **новую спеццену** в USD (например, `4.50`):"
    },
    'admin_custom_price_success': {
        'en': "✅ Custom price set successfully!\n\n👤 User: `{user_id}` ({user_name})\n🛍️ Product: *{product_name}*\n💵 Custom Price: `${custom_price:.2f} USD` (Original: `${original_price:.2f} USD`)",
        'ar': "✅ تم تخصيص السعر بنجاح!\n\n👤 المستخدم: `{user_id}` ({user_name})\n🛍️ المنتج: *{product_name}*\n💵 السعر المخصص: `${custom_price:.2f} USD` (السعر الأصلي: `${original_price:.2f} USD`)",
        'ru': "✅ Спеццена успешно установлена!\n\n👤 Пользователь: `{user_id}` ({user_name})\n🛍️ Товар: *{product_name}*\n💵 Спеццена: `${custom_price:.2f} USD` (Обычная: `${original_price:.2f} USD`)"
    },
    'admin_custom_price_deleted': {
        'en': "✅ Custom price deleted successfully for product *{product_name}* (User: `{user_id}`).",
        'ar': "✅ تم حذف السعر المخصص بنجاح للمنتج *{product_name}* (المستخدم: `{user_id}`).",
        'ru': "✅ Спеццена успешно удалена для товара *{product_name}* (Пользователь: `{user_id}`)."
    },
    'admin_custom_price_no_items': {
        'en': "📭 No custom product prices set yet. Click below to add one.",
        'ar': "📭 لا توجد أسعار مخصصة مضافة حالياً. اضغط على الزر أدناه لإضافة سعر مخصص.",
        'ru': "📭 Индивидуальные цены пока не установлены. Нажмите кнопку ниже для добавления."
    },
    'admin_discounts_title': {
        'en': "👥 *User Discounts Configuration*\n\nHere you can manage custom percentage discounts for specific users. A user with a discount will automatically get the corresponding price deduction at checkout.",
        'ar': "👥 *إدارة خصومات المستخدمين النسبية*\n\nهنا يمكنك تعيين نسبة مئوية مخصصة للخصم لمستخدم معين. سيتم تطبيق الخصم تلقائياً عند الدفع.",
        'ru': "👥 *Настройка скидок пользователей*\n\nЗдесь вы можете управлять процентными скидками для пользователей. Скидка применяется автоматически при покупке."
    },
    'admin_manage_users_title': {
        'en': "👥 *User Management*\n\nSelect an option below to manage discounts, custom pricing, balances, or user bans:",
        'ar': "👥 *إدارة المستخدمين*\n\nاختر أحد الخيارات أدناه لإدارة الخصومات، الأسعار المخصصة، الأرصدة، أو الحظر:",
        'ru': "👥 *Управление пользователями*\n\nВыберите опцию для управления скидками, спецценами, балансами или банами:"
    },
    # Admin Product Management
    'admin_prod_mgmt_title': {
        'en': "📦 *Product Management*\nSelect a product to edit/delete or add a new one:",
        'ar': "📦 *إدارة المنتجات*\nاختر منتجاً لتعديله/حذفه أو أضف منتجاً جديداً:",
        'ru': "📦 *Управление товарами*\nВыберите товар для редактирования/удаления или добавьте новый:"
    },
    'admin_prod_add_name_prompt': {
        'en': "✏️ Enter Product Name:",
        'ar': "✏️ أدخل اسم المنتج:",
        'ru': "✏️ Введите название товара:"
    },
    'admin_prod_add_desc_prompt': {
        'en': "✏️ Enter Product Description:",
        'ar': "✏️ أدخل وصف المنتج:",
        'ru': "✏️ Введите описание товара:"
    },
    'admin_prod_add_price_prompt': {
        'en': "✏️ Enter Product Price in *USD* (e.g. 5.50):",
        'ar': "✏️ أدخل سعر المنتج بـ *USD* (مثال: 5.50):",
        'ru': "✏️ Введите цену товара в *USD* (например: 5.50):"
    },
    'admin_prod_add_emoji_prompt': {
        'en': "🎨 Now, send an animated Premium Custom Emoji for this product's icon, or type /skip to use no emoji.",
        'ar': "🎨 أرسل الآن إيموجي مميز (Premium Custom Emoji) كأيقونة للمنتج، أو أرسل /skip لتخطي ذلك.",
        'ru': "🎨 Отправьте анимированный кастомный эмодзи для иконки товара или отправьте /skip для пропуска."
    },
    'admin_prod_add_success': {
        'en': "✅ Product added successfully!",
        'ar': "✅ تم إضافة المنتج بنجاح!",
        'ru': "✅ Товар успешно добавлен!"
    },
    'admin_prod_del_success': {
        'en': "✅ Product deleted successfully!",
        'ar': "✅ تم حذف المنتج بنجاح!",
        'ru': "✅ Товар успешно удален!"
    },
    'admin_prod_edit_fields_title': {
        'en': "✏️ *Editing Product:* {name}\nSelect which field you want to edit:",
        'ar': "✏️ *تعديل المنتج:* {name}\nاختر الحقل الذي ترغب في تعديله:",
        'ru': "✏️ *Редактирование товара:* {name}\nВыберите поле для изменения:"
    },
    'admin_prod_edit_val_prompt': {
        'en': "✏️ Enter the new value for *{field}*:",
        'ar': "✏️ أدخل القيمة الجديدة لـ *{field}*:",
        'ru': "✏️ Введите новое значение для *{field}*:"
    },
    'admin_prod_edit_success': {
        'en': "✅ Product *{field}* updated successfully!",
        'ar': "✅ تم تحديث *{field}* المنتج بنجاح!",
        'ru': "✅ Поле *{field}* успешно обновлено!"
    },
    'admin_prod_edit_emoji_prompt': {
        'en': "🎨 Send the new animated Premium Custom Emoji for *{name}*, or send `remove` to delete the emoji:",
        'ar': "🎨 أرسل الإيموجي المميز الجديد للمنتج *{name}*، أو أرسل `remove` لإزالة الإيموجي:",
        'ru': "🎨 Отправьте новый кастомный эмодзи для *{name}* или отправьте `remove` для удаления эмодзи:"
    },
    'admin_prod_edit_emoji_success': {
        'en': "✅ Product emoji updated successfully!",
        'ar': "✅ تم تحديث إيموجي المنتج بنجاح!",
        'ru': "✅ Эмодзи товара успешно обновлен!"
    },
    
    # Tier Prices
    'admin_tier_prices_title': {
        'en': "🏷️ *Bulk Quantity Prices (Tier Prices)*\nProduct: *{name}*\nBase Price: `${price:.2f}`\n\n{tiers_text}\nManage quantity price discounts below:",
        'ar': "🏷️ *أسعار الجملة والكميات (Tier Prices)*\nالمنتج: *{name}*\nالسعر الأساسي: `${price:.2f}`\n\n{tiers_text}\nتحكم في أسعار الخصم للكميات أدناه:",
        'ru': "🏷️ *Оптовые цены (Tier Prices)*\nТовар: *{name}*\nБазовая цена: `${price:.2f}`\n\n{tiers_text}\nУправление оптовыми ценами ниже:"
    },
    'admin_tier_min_qty_prompt': {
        'en': "🔢 Enter the **Minimum Quantity** for this tier (e.g. `5` for 5+ items):",
        'ar': "🔢 أدخل **الحد الأدنى للكمية** لهذا السعر (مثال: `5` لطلب 5 قطع أو أكثر):",
        'ru': "🔢 Введите **минимальное количество** для скидки (например: `5`):"
    },
    'admin_tier_unit_price_prompt': {
        'en': "💵 Enter the **Unit Price in USD** for quantity {qty}+ (e.g. `4.20`):",
        'ar': "💵 أدخل **سعر الحبة بالدولار** للكمية {qty}+ (مثال: `4.20`):",
        'ru': "💵 Введите **цену за штуку в USD** при заказе от {qty}+ (например: `4.20`):"
    },
    'admin_tier_add_success': {
        'en': "✅ Tier price added: {qty}+ ➔ `${unit_price:.2f} USD` each.",
        'ar': "✅ تمت إضافة سعر الكمية: {qty}+ ⬅️ `${unit_price:.2f} USD` لكل حبة.",
        'ru': "✅ Оптовая цена добавлена: от {qty}+ ➔ `${unit_price:.2f} USD` за шт."
    },
    'admin_tier_clear_success': {
        'en': "✅ All tier prices cleared for this product.",
        'ar': "✅ تم مسح جميع أسعار الجملة لهذا المنتج.",
        'ru': "✅ Все оптовые цены для этого товара удалены."
    },

    # Admin Stock
    'admin_stock_select_prod_prompt': {
        'en': "📥 *Select Product for Stock adding*:",
        'ar': "📥 *اختر المنتج لإضافة المخزون*:",
        'ru': "📥 *Выберите товар для добавления стока*:"
    },
    'admin_stock_data_prompt': {
        'en': "📥 Send the stock data for *{name}* (single item or accounts):",
        'ar': "📥 أرسل بيانات المخزون للمنتج *{name}*:",
        'ru': "📥 Отправьте данные стока для товара *{name}*:"
    },
    'admin_bulk_stock_prompt': {
        'en': "📦 Send the bulk stock data for *{name}* (one account/key per line):",
        'ar': "📦 أرسل المخزون الجماعي للمنتج *{name}* (كل حساب أو كود في سطر مستقل):",
        'ru': "📦 Отправьте данные массового стока для *{name}* (по одной строке на товар):"
    },
    'admin_stock_add_success': {
        'en': "✅ Stock item added successfully for *{name}*!\nTotal stock: `{stock}`",
        'ar': "✅ تم إضافة عنصر المخزون بنجاح للمنتج *{name}*!\nإجمالي المتوفر: `{stock}`",
        'ru': "✅ Сток успешно добавлен для товара *{name}*!\nВсего в наличии: `{stock}`"
    },
    'admin_bulk_stock_add_success': {
        'en': "✅ Bulk stock added successfully!\nAdded `{count}` items for *{name}*.\nTotal stock: `{stock}`",
        'ar': "✅ تم إضافة المخزون الجماعي بنجاح!\nتمت إضافة `{count}` عنصر للمنتج *{name}*.\nإجمالي المتوفر: `{stock}`",
        'ru': "✅ Массовый сток успешно добавлен!\nДобавлено `{count}` шт. для *{name}*.\nВсего в наличии: `{stock}`"
    },

    # User Inspection
    'admin_inspect_prompt': {
        'en': "🔍 Enter the **User ID** to inspect:",
        'ar': "🔍 أدخل **معرف المستخدم (User ID)** لفحصه:",
        'ru': "🔍 Введите **ID пользователя** для проверки:"
    },
    'admin_inspect_invalid_id': {
        'en': "❌ Invalid User ID. Please enter a valid numeric User ID:",
        'ar': "❌ معرف مستخدم غير صالح. يرجى إدخال أرقام فقط:",
        'ru': "❌ Неверный ID пользователя. Введите числовой ID:"
    },
    'admin_inspect_not_found': {
        'en': "❌ User not found in the database.",
        'ar': "❌ المستخدم غير موجود في قاعدة البيانات.",
        'ru': "❌ Пользователь не найден в базе данных."
    },
    
    # Balances
    'admin_user_bal_prompt': {
        'en': "💰 Enter the **User ID** to edit balance:",
        'ar': "💰 أدخل **معرف المستخدم (User ID)** لتعديل رصيده:",
        'ru': "💰 Введите **ID пользователя** для изменения баланса:"
    },
    'admin_user_new_bal_prompt': {
        'en': "👤 User: *{name}* (`{user_id}`)\nCurrent Balance: `${current_balance:.2f} USD`\n\n✍️ Enter the **new balance** in USD (e.g. `10.50`):",
        'ar': "👤 المستخدم: *{name}* (`{user_id}`)\nالرصيد الحالي: `${current_balance:.2f} USD`\n\n✍️ أدخل **الرصيد الجديد** بالدولار (مثال: `10.50`):",
        'ru': "👤 Пользователь: *{name}* (`{user_id}`)\nТекущий баланс: `${current_balance:.2f} USD`\n\n✍️ Введите **новый баланс** в USD (например: `10.50`):"
    },
    'admin_user_bal_updated': {
        'en': "✅ Balance updated successfully for *{name}*!\nNew Balance: `${balance:.2f} USD`",
        'ar': "✅ تم تحديث الرصيد بنجاح للمستخدم *{name}*!\nالرصيد الجديد: `${balance:.2f} USD`",
        'ru': "✅ Баланс успешно обновлен для *{name}*!\nНовый баланс: `${balance:.2f} USD`"
    },

    # Broadcast
    'admin_broadcast_prompt': {
        'en': "📣 Send the message you want to broadcast to *all users* (can contain formatting, photos, or media):",
        'ar': "📣 أرسل الرسالة التي ترغب في نشرها لجميع المستخدمين (يمكن أن تحتوي على نصوص، صور، أو وسائط):",
        'ru': "📣 Отправьте сообщение для рассылки всем пользователям (поддерживаются текст, фото и медиа):"
    },
    'admin_broadcast_started': {
        'en': "🚀 Broadcast started... sending to users in background.",
        'ar': "🚀 بدأت عملية الإرسال الجماعي... جاري الإرسال للمستخدمين في الخلفية.",
        'ru': "🚀 Рассылка запущена... отправка сообщений в фоновом режиме."
    },
    'admin_broadcast_finished': {
        'en': "✅ Broadcast completed!\n\n📬 Successfully Sent: `{sent}`\n❌ Failed: `{failed}`\n👥 Total Users: `{total}`",
        'ar': "✅ اكتملت عملية الإرسال الجماعي!\n\n📬 تم الإرسال بنجاح إلى: `{sent}`\n❌ فشل الإرسال إلى: `{failed}`\n👥 إجمالي المستخدمين: `{total}`",
        'ru': "✅ Рассылка завершена!\n\n📬 Успешно доставлено: `{sent}`\n❌ Ошибок: `{failed}`\n👥 Всего пользователей: `{total}`"
    },

    # Store Name
    'admin_store_name_current': {
        'en': "🏫 *Current Store Name:* `{name}`\n\n✍️ Please enter the new name for the store:",
        'ar': "🏫 *اسم المتجر الحالي:* `{name}`\n\n✍️ يرجى إدخال الاسم الجديد للمتجر:",
        'ru': "🏫 *Текущее название магазина:* `{name}`\n\n✍️ Введите новое название магазина:"
    },
    'admin_store_name_success': {
        'en': "✅ Store name successfully updated to: `{name}`",
        'ar': "✅ تم تحديث اسم المتجر بنجاح إلى: `{name}`",
        'ru': "✅ Название магазина успешно обновлено на: `{name}`"
    },

    # Buttons
    'btn_admin_add_product': {
        'en': "➕ Add Product",
        'ar': "➕ إضافة منتج جديد",
        'ru': "➕ Добавить товар"
    },
    'btn_admin_edit_details': {
        'en': "📝 Edit Details",
        'ar': "📝 تعديل البيانات",
        'ru': "📝 Изменить данные"
    },
    'btn_admin_tier_prices_btn': {
        'en': "🏷️ Tier Prices (Bulk)",
        'ar': "🏷️ أسعار الجملة والكميات",
        'ru': "🏷️ Оптовые цены"
    },
    'btn_admin_edit_emoji_btn': {
        'en': "🎨 Edit Emoji",
        'ar': "🎨 تعديل الإيموجي",
        'ru': "🎨 Изменить эмодзи"
    },
    'btn_admin_delete_product_btn': {
        'en': "🗑️ Delete Product",
        'ar': "🗑️ حذف المنتج",
        'ru': "🗑️ Удалить товар"
    },
    'btn_admin_add_tier_btn': {
        'en': "➕ Add Quantity Tier Price",
        'ar': "➕ إضافة سعر كمية جديد",
        'ru': "➕ Добавить оптовую цену"
    },
    'btn_admin_clear_tiers_btn': {
        'en': "🗑️ Clear All Tier Prices",
        'ar': "🗑️ مسح جميع أسعار الجملة",
        'ru': "🗑️ Очистить все оптовые цены"
    },
    'btn_admin_reply_ticket_btn': {
        'en': "✍️ Reply to User",
        'ar': "✍️ الرد على المستخدم",
        'ru': "✍️ Ответить пользователю"
    },
    'btn_admin_approve': {
        'en': "✅ Approve",
        'ar': "✅ قبول الإيداع",
        'ru': "✅ Одобрить"
    },
    'btn_admin_reject': {
        'en': "❌ Reject",
        'ar': "❌ رفض الإيداع",
        'ru': "❌ Отклонить"
    },
    'btn_admin_cancel_refund_btn': {
        'en': "❌ Cancel & Refund",
        'ar': "❌ إلغاء وإرجاع الرصيد",
        'ru': "❌ Отменить и вернуть средства"
    },
    'btn_admin_edit_bal_btn': {
        'en': "✏️ Edit Balance",
        'ar': "✏️ تعديل الرصيد",
        'ru': "✏️ Изменить баланс"
    },
    'btn_admin_gen_api_key': {
        'en': "➕ Generate API Key",
        'ar': "➕ إنشاء مفتاح API",
        'ru': "➕ Создать API ключ"
    },
    'btn_admin_rev_api_key': {
        'en': "❌ Revoke API Key",
        'ar': "❌ إلغاء مفتاح API",
        'ru': "❌ Отозвать API ключ"
    },
    'btn_admin_ban_user_btn': {
        'en': "🔴 Ban User",
        'ar': "🔴 حظر مستخدم",
        'ru': "🔴 Заблокировать"
    },
    'btn_admin_unban_user_btn': {
        'en': "🟢 Unban User",
        'ar': "🟢 فك حظر مستخدم",
        'ru': "🟢 Разблокировать"
    },
    'btn_admin_show_banned_btn': {
        'en': "📋 Show Banned Users",
        'ar': "📋 عرض المحظورين",
        'ru': "📋 Список заблокированных"
    },
    'btn_admin_skip_reason_btn': {
        'en': "⏭️ Skip Reason",
        'ar': "⏭️ تخطي السبب",
        'ru': "⏭️ Пропустить причину"
    },
    'btn_admin_field_name': {
        'en': "✏️ Name",
        'ar': "✏️ الاسم",
        'ru': "✏️ Название"
    },
    'btn_admin_field_desc': {
        'en': "✏️ Description",
        'ar': "✏️ الوصف",
        'ru': "✏️ Описание"
    },
    'btn_admin_field_price': {
        'en': "✏️ Price",
        'ar': "✏️ السعر",
        'ru': "✏️ Цена"
    },
    'admin_invalid_price': {
        'en': "❌ Invalid price. Enter a positive decimal number:",
        'ar': "❌ سعر غير صالح. يرجى إدخال رقم عشري موجب:",
        'ru': "❌ Неверная цена. Введите положительное число:"
    },
    'admin_stats_title': {
        'en': "📊 *{store_name} — Statistics*\n━━━━━━━━━━━━━━━━━━━━\n\n👥 *Users*\n├ Total: `{total_users}`\n└ Joined Today: `{users_today}`\n\n💰 *Deposits*\n├ Total: `{total_deposit_count}` — `${total_deposits:.2f}`\n└ Today: `${deposits_today:.2f}`\n\n🛍 *Orders (Sales)*\n├ Total: `{total_orders}` — `${total_order_revenue:.2f}`\n└ Today: `{orders_today}` — `${order_revenue_today:.2f}`\n\n⏳ *Pending Deposits:* `{pending_count}`\n━━━━━━━━━━━━━━━━━━━━",
        'ar': "📊 *{store_name} — الإحصائيات*\n━━━━━━━━━━━━━━━━━━━━\n\n👥 *المستخدمين*\n├ الإجمالي: `{total_users}`\n└ المنضمين اليوم: `{users_today}`\n\n💰 *الإيداعات*\n├ الإجمالي: `{total_deposit_count}` — `${total_deposits:.2f}`\n└ اليوم: `${deposits_today:.2f}`\n\n🛍 *الطلبات (المبيعات)*\n├ الإجمالي: `{total_orders}` — `${total_order_revenue:.2f}`\n└ اليوم: `{orders_today}` — `${order_revenue_today:.2f}`\n\n⏳ *الإيداعات المعلقة:* `{pending_count}`\n━━━━━━━━━━━━━━━━━━━━",
        'ru': "📊 *{store_name} — Статистика*\n━━━━━━━━━━━━━━━━━━━━\n\n👥 *Пользователи*\n├ Всего: `{total_users}`\n└ Сегодня: `{users_today}`\n\n💰 *Пополнения*\n├ Всего: `{total_deposit_count}` — `${total_deposits:.2f}`\n└ Сегодня: `${deposits_today:.2f}`\n\n🛍 *Заказы (Продажи)*\n├ Всего: `{total_orders}` — `${total_order_revenue:.2f}`\n└ Сегодня: `{orders_today}` — `${order_revenue_today:.2f}`\n\n⏳ *Ожидающие депозиты:* `{pending_count}`\n━━━━━━━━━━━━━━━━━━━━"
    },
    'admin_user_report_title': {
        'en': "🔍 *User Inspection Report*\n━━━━━━━━━━━━━━━━━━━━\n\n👤 *Profile*\n├ Name: {name}\n├ Username: {username}\n├ ID: `{user_id}`\n├ Status: {ban_status}\n├ Balance: `${balance:.2f} USD`\n├ Discount: `{discount:.0f}%`\n├ Language: `{language}`\n└ Joined: `{joined}`\n\n💰 *Deposits*\n├ Completed: `{deposits_count}` — `${deposits_total:.2f}`\n└ Pending: `{pending_count}` — `${pending_total:.2f}`\n\n🛍 *Purchases*\n├ Total Orders: `{orders_count}`\n└ Total Spent: `${orders_total:.2f}`\n\n👥 *Referrals*\n├ Referred by: {referred_by}\n├ Referrals count: `{referral_count}`\n└ Referral earnings: `${ref_earnings:.2f}`",
        'ar': "🔍 *تقرير فحص المستخدم*\n━━━━━━━━━━━━━━━━━━━━\n\n👤 *الملف الشخصي*\n├ الاسم: {name}\n├ المعرف: {username}\n├ ID: `{user_id}`\n├ الحالة: {ban_status}\n├ الرصيد: `${balance:.2f} USD`\n├ الخصم: `{discount:.0f}%`\n├ اللغة: `{language}`\n└ تاريخ الانضمام: `{joined}`\n\n💰 *الإيداعات*\n├ المكتملة: `{deposits_count}` — `${deposits_total:.2f}`\n└ المعلقة: `{pending_count}` — `${pending_total:.2f}`\n\n🛍 *المشتريات*\n├ إجمالي الطلبات: `{orders_count}`\n└ إجمالي المشتريات: `${orders_total:.2f}`\n\n👥 *الإحالات*\n├ أحاله: {referred_by}\n├ عدد الإحالات: `{referral_count}`\n└ أرباح الإحالات: `${ref_earnings:.2f}`",
        'ru': "🔍 *Отчет проверки пользователя*\n━━━━━━━━━━━━━━━━━━━━\n\n👤 *Профиль*\n├ Имя: {name}\n├ Юзернейм: {username}\n├ ID: `{user_id}`\n├ Статус: {ban_status}\n├ Баланс: `${balance:.2f} USD`\n├ Скидка: `{discount:.0f}%`\n├ Язык: `{language}`\n└ Регистрация: `{joined}`\n\n💰 *Пополнения*\n├ Завершенные: `{deposits_count}` — `${deposits_total:.2f}`\n└ Ожидающие: `{pending_count}` — `${pending_total:.2f}`\n\n🛍 *Покупки*\n├ Всего заказов: `{orders_count}`\n└ Всего потрачено: `${orders_total:.2f}`\n\n👥 *Рефералы*\n├ Пригласил: {referred_by}\n├ Количество рефералов: `{referral_count}`\n└ Доход с рефералов: `${ref_earnings:.2f}`"
    },
    'admin_discount_user_prompt': {
        'en': "👥 Please enter the **User ID** of the user you want to grant a discount to:",
        'ar': "👥 الرجاء إدخال **معرف المستخدم (User ID)** لمنحه الخصم:",
        'ru': "👥 Введите **ID пользователя**, которому хотите выдать скидку:"
    },
    'admin_discount_pct_prompt': {
        'en': "👤 Found User: *{name}* (`{user_id}`)\n\nNow, enter the Discount Percentage (e.g. `15` for 15%):",
        'ar': "👤 تم العثور على المستخدم: *{name}* (`{user_id}`)\n\nأدخل الآن نسبة الخصم المئوية (مثال: `15` لـ 15%):",
        'ru': "👤 Пользователь: *{name}* (`{user_id}`)\n\nВведите процент скидки (например `15` для 15%):"
    },
    'admin_discount_success': {
        'en': "✅ Successfully set discount of **{percent}%** for *{name}*!",
        'ar': "✅ تم تعيين خصم بنسبة **{percent}%** بنجاح للمستخدم *{name}*!",
        'ru': "✅ Скидка **{percent}%** успешно установлена для *{name}*!"
    },
    'admin_discount_deleted': {
        'en': "✅ Discount deleted successfully!",
        'ar': "✅ تم حذف الخصم بنجاح!",
        'ru': "✅ Скидка успешно удалена!"
    },
    'admin_ban_menu_title': {
        'en': "🚫 *Ban / Unban Management System*\nSelect an option below to manage user bans:",
        'ar': "🚫 *نظام إدارة حظر وفك حظر المستخدمين*\nاختر خياراً من الأسفل لإدارة الحظر:",
        'ru': "🚫 *Система управления банами*\nВыберите действие ниже:"
    },
    'admin_ban_user_prompt': {
        'en': "🔴 *Ban User*\n\nPlease enter the numeric **Telegram User ID** to ban:",
        'ar': "🔴 *حظر مستخدم*\n\nيرجى إدخال **معرف المستخدم الرقمي (User ID)** المراد حظره:",
        'ru': "🔴 *Блокировка пользователя*\n\nВведите числовой **ID пользователя** для бана:"
    },
    'admin_ban_reason_prompt': {
        'en': "📝 User `{user_id}` selected.\nPlease enter the **Ban Reason** (or send /skip):",
        'ar': "📝 تم اختيار المستخدم `{user_id}`.\nيرجى إدخال **سبب الحظر** (أو أرسل /skip للتخطي):",
        'ru': "📝 Выбран пользователь `{user_id}`.\nВведите **причину блокировки** (или отправьте /skip):"
    },
    'admin_ban_success': {
        'en': "🔴 *User banned successfully!*\n\n👤 ID: `{user_id}`\n💬 Reason: {reason}",
        'ar': "🔴 *تم حظر المستخدم بنجاح!*\n\n👤 المعرف: `{user_id}`\n💬 السبب: {reason}",
        'ru': "🔴 *Пользователь успешно заблокирован!*\n\n👤 ID: `{user_id}`\n💬 Причина: {reason}"
    },
    'admin_unban_user_prompt': {
        'en': "🟢 *Unban User*\n\nPlease enter the numeric **Telegram User ID** to unban:",
        'ar': "🟢 *فك حظر مستخدم*\n\nيرجى إدخال **معرف المستخدم الرقمي (User ID)** المراد فك حظره:",
        'ru': "🟢 *Разблокировка пользователя*\n\nВведите числовой **ID пользователя** для разбана:"
    },
    'admin_unban_success': {
        'en': "🟢 *User unbanned successfully!*\n\n👤 ID: `{user_id}`",
        'ar': "🟢 *تم إلغاء حظر المستخدم بنجاح!*\n\n👤 المعرف: `{user_id}`",
        'ru': "🟢 *Пользователь успешно разблокирован!*\n\n👤 ID: `{user_id}`"
    },
    'admin_no_banned_users': {
        'en': "✨ No banned users at the moment.",
        'ar': "✨ لا يوجد أي مستخدم محظور حالياً.",
        'ru': "✨ В данный момент нет заблокированных пользователей."
    },
    'admin_banned_list_title': {
        'en': "📋 *Currently Banned Users:*\n━━━━━━━━━━━━━━━━━━━━\n",
        'ar': "📋 *قائمة المستخدمين المحظورين حالياً:*\n━━━━━━━━━━━━━━━━━━━━\n",
        'ru': "📋 *Список заблокированных пользователей:*\n━━━━━━━━━━━━━━━━━━━━\n"
    },
    'admin_preorders_summary_title': {
        'en': "⏳ *Active Pre-orders Summary*\n\nHere you can see all products that users have reserved due to being out of stock. Select a product to view individual reservations or cancel them:",
        'ar': "⏳ *ملخص الحجوزات المسبقة النشطة*\n\nهنا يمكنك رؤية جميع المنتجات المحجوزة من قبل المستخدمين لعدم توفرها. اختر منتجاً لعرض الحجوزات أو إلغائها:",
        'ru': "⏳ *Сводка активных предзаказов*\n\nЗдесь показаны все товары, забронированные пользователями из-за отсутствия в наличии. Выберите товар для просмотра или отмены:"
    },
    'admin_preorders_no_active': {
        'en': "📭 No active pre-orders/reservations at the moment.",
        'ar': "📭 لا توجد أي حجوزات نشطة حالياً.",
        'ru': "📭 В данный момент нет активных предзаказов."
    },
    'admin_preorders_prod_title': {
        'en': "📦 *Reservations for:* `{name}`\nSelect a specific user's reservation to view actions:",
        'ar': "📦 *الحجوزات للمنتج:* `{name}`\nاختر حجز مستخدم معين لعرض الإجراءات:",
        'ru': "📦 *Предзаказы для:* `{name}`\nВыберите бронь пользователя для просмотра действий:"
    },
    'admin_preorder_detail_title': {
        'en': "⏳ *Pre-order Reservation Details*\n\n🆔 *Pre-order ID:* `{id}`\n📦 *Product:* `{name}`\n👤 *User:* {buyer} [ID: `{user_id}`]\n🔢 *Quantity:* `{qty}`\n💰 *Amount Locked:* `${price:.2f} USD`\n📅 *Created At:* `{date}`\n\n⚠️ *Admin Action:* You can cancel this reservation. Doing so will immediately delete the pre-order and refund the amount back to the user's wallet.",
        'ar': "⏳ *تفاصيل الحجز المسبق*\n\n🆔 *معرف الحجز:* `{id}`\n📦 *المنتج:* `{name}`\n👤 *المستخدم:* {buyer} [ID: `{user_id}`]\n🔢 *الكمية:* `{qty}`\n💰 *المبلغ المعلق:* `${price:.2f} USD`\n📅 *تاريخ الحجز:* `{date}`\n\n⚠️ *إجراء الإدارة:* يمكنك إلغاء هذا الحجز، وسيتم حذفه فوراً وإعادة المبلغ كاملاً إلى محفظة المستخدم.",
        'ru': "⏳ *Детали предзаказа*\n\n🆔 *ID предзаказа:* `{id}`\n📦 *Товар:* `{name}`\n👤 *Пользователь:* {buyer} [ID: `{user_id}`]\n🔢 *Количество:* `{qty}`\n💰 *Заблокировано:* `${price:.2f} USD`\n📅 *Создано:* `{date}`\n\n⚠️ *Действие админа:* Вы можете отменить бронь. Предзаказ будет удален, а средства возвращены на баланс пользователя."
    },
    'admin_pending_no_deposits': {
        'en': "📭 No pending deposits at the moment.",
        'ar': "📭 لا توجد أي إيداعات معلقة في الوقت الحالي.",
        'ru': "📭 В данный момент нет ожидающих депозитов."
    },
    'admin_pending_found': {
        'en': "⏳ Found {count} pending deposit request(s):",
        'ar': "⏳ تم العثور على {count} طلب إيداع معلق:",
        'ru': "⏳ Найдено {count} ожидающих запросов на депозит:"
    },
    'admin_settings_channels_title': {
        'en': "📢 *Channel Settings*\n\n🔗 *Compulsory Join Channels:*\n{channels_list}\n📣 *News Channel:* `{news_ch}`\n📢 *Auto Sales Proofs:* `{auto_proofs}`\n⏱️ *Proof Posting Interval:* `{proofs_min} - {proofs_max} minutes`\n\n💡 *Tip:* When adding channels, enter them separated by a comma (e.g. `@channel1, @channel2`)\nThe bot will check them and display each channel as an individual button to the user!",
        'ar': "📢 *إعدادات القنوات*\n\n🔗 *قنوات الاشتراك الإجباري:*\n{channels_list}\n📣 *قناة الأخبار/التحديثات:* `{news_ch}`\n📢 *نشر إثباتات المبيعات تلقائياً:* `{auto_proofs}`\n⏱️ *الفاصل الزمني للنشر:* `{proofs_min} - {proofs_max} دقيقة`\n\n💡 *ملاحظة:* عند إضافة القنوات، افصل بينها بفاصلة (مثال: `@channel1, @channel2`)\nسيقوم البوت بالتحقق منها وعرض كل قناة كزر منفصل للمستخدم!",
        'ru': "📢 *Настройки каналов*\n\n🔗 *Обязательные каналы для подписки:*\n{channels_list}\n📣 *Канал новостей:* `{news_ch}`\n📢 *Авто-публикация продаж:* `{auto_proofs}`\n⏱️ *Интервал публикаций:* `{proofs_min} - {proofs_max} минут`\n\n💡 *Совет:* При добавлении каналов вводите их через запятую (напр. `@channel1, @channel2`)."
    },
    'admin_settings_support_title': {
        'en': "🎧 *Support Settings*\n\n👤 *Support Handle:* `{support}`",
        'ar': "🎧 *إعدادات الدعم الفني*\n\n👤 *حساب الدعم:* `{support}`",
        'ru': "🎧 *Настройки поддержки*\n\n👤 *Контакт поддержки:* `{support}`"
    },
    'admin_settings_charge_title': {
        'en': "💳 *Deposit Settings*\n\n⭐️ *Telegram Stars:* {stars_status}\n💱 *Stars Exchange Rate:* 1 Star = `{stars_rate}` USD\n\n🤖 *Crypto Bot Gateway:* {cb_status}\n\n🪙 *Manual Crypto Transfer:* {ct_status}\n🪙 *USDT BEP20 Address:* `{usdt_addr}`\n🪙 *LTC Address:* `{ltc_addr}`\n🪙 *TON Address:* `{ton_addr}`\n🪙 *Binance Pay ID / Email / Phone:* `{binance_addr}`",
        'ar': "💳 *إعدادات شحن الرصيد*\n\n⭐️ *نجوم تيليجرام (Stars):* {stars_status}\n💱 *سعر صرف النجوم:* 1 نجمة = `{stars_rate}` دولار\n\n🤖 *بوابة Crypto Bot:* {cb_status}\n\n🪙 *التحويل اليدوي للعملات المشفرة:* {ct_status}\n🪙 *عنوان USDT BEP20:* `{usdt_addr}`\n🪙 *عنوان LTC:* `{ltc_addr}`\n🪙 *عنوان TON:* `{ton_addr}`\n🪙 *معرف / إيميل Binance Pay:* `{binance_addr}`",
        'ru': "💳 *Настройки пополнения баланса*\n\n⭐️ *Telegram Stars:* {stars_status}\n💱 *Курс Stars:* 1 Star = `{stars_rate}` USD\n\n🤖 *Шлюз Crypto Bot:* {cb_status}\n\n🪙 *Ручной перевод крипты:* {ct_status}\n🪙 *Адрес USDT BEP20:* `{usdt_addr}`\n🪙 *Адрес LTC:* `{ltc_addr}`\n🪙 *Адрес TON:* `{ton_addr}`\n🪙 *Binance Pay ID / Email / Phone:* `{binance_addr}`"
    },
    'admin_settings_referral_title': {
        'en': "👥 *Referral System Settings*\n\n💰 *Fixed Bonus Reward:* `${fixed_bonus} USD` immediately upon friend registration",
        'ar': "👥 *إعدادات نظام الإحالة*\n\n💰 *مكافأة الإحالة الثابتة:* `${fixed_bonus} USD` فور تسجيل الصديق بالبوت",
        'ru': "👥 *Настройки реферальной системы*\n\n💰 *Фиксированный бонус:* `${fixed_bonus} USD` сразу после регистрации друга"
    },
    'admin_settings_api_keys_title': {
        'en': "🔑 *API Keys & Proxy Configuration*\n\n🔸 *BscScan API Key:* `{bscscan_key}`\n🪙 *Blockcypher API Token:* `{blockcypher_key}`\n💎 *Toncenter API Key:* `{toncenter_key}`\n🤖 *Crypto Bot Token:* `{cryptobot_key}`\n⚙️ *Crypto Bot Environment:* `{cb_testnet_status}`\n━━━━━━━━━━━━━━━\n🔶 *Binance API Key:* `{b_api_display}`\n🔶 *Binance Secret Key:* `{b_secret_display}`\n🌐 *Binance Proxy:* `{binance_proxy}`",
        'ar': "🔑 *إعدادات مفاتيح API والبروكسي*\n\n🔸 *مفتاح BscScan API:* `{bscscan_key}`\n🪙 *توكن Blockcypher API:* `{blockcypher_key}`\n💎 *مفتاح Toncenter API:* `{toncenter_key}`\n🤖 *توكن Crypto Bot:* `{cryptobot_key}`\n⚙️ *بيئة عمل Crypto Bot:* `{cb_testnet_status}`\n━━━━━━━━━━━━━━━\n🔶 *مفتاح Binance API:* `{b_api_display}`\n🔶 *مفتاح Binance Secret:* `{b_secret_display}`\n🌐 *بروكسي بينانس:* `{binance_proxy}`",
        'ru': "🔑 *Настройки API ключей и прокси*\n\n🔸 *BscScan API Key:* `{bscscan_key}`\n🪙 *Blockcypher API Token:* `{blockcypher_key}`\n💎 *Toncenter API Key:* `{toncenter_key}`\n🤖 *Crypto Bot Token:* `{cryptobot_key}`\n⚙️ *Среда Crypto Bot:* `{cb_testnet_status}`\n━━━━━━━━━━━━━━━\n🔶 *Binance API Key:* `{b_api_display}`\n🔶 *Binance Secret Key:* `{b_secret_display}`\n🌐 *Binance Proxy:* `{binance_proxy}`"
    },
    'admin_settings_emoji_title': {
        'en': "🎨 *Emoji Settings*\n\nSelect an item to set its animated emoji:",
        'ar': "🎨 *إعدادات الإيموجي*\n\nاختر عنصراً لتعيين الإيموجي المتحرك الخاص به:",
        'ru': "🎨 *Настройки эмодзи*\n\nВыберите пункт для установки анимированного эмодзи:"
    },
    'btn_admin_set_force_join': {
        'en': "✍️ Set Force Join Channels",
        'ar': "✍️ تعيين قنوات الاشتراك الإجباري",
        'ru': "✍️ Задать обязательные каналы"
    },
    'btn_admin_set_news_ch': {
        'en': "✍️ Set News Channel",
        'ar': "✍️ تعيين قناة الأخبار",
        'ru': "✍️ Задать канал новостей"
    },
    'btn_admin_auto_proofs_toggle': {
        'en': "📢 Auto Proofs: {status}",
        'ar': "📢 نشر المبيعات: {status}",
        'ru': "📢 Публикация продаж: {status}"
    },
    'btn_admin_proofs_interval': {
        'en': "⏱️ Interval: {min_v}-{max_v} min",
        'ar': "⏱️ الفاصل الزمني: {min_v}-{max_v} دقيقة",
        'ru': "⏱️ Интервал: {min_v}-{max_v} мин"
    },
    'btn_admin_set_support': {
        'en': "✍️ Edit Support Handle",
        'ar': "✍️ تعديل حساب الدعم",
        'ru': "✍️ Изменить контакт поддержки"
    },
    'btn_admin_toggle_stars': {
        'en': "⭐️ Toggle Telegram Stars",
        'ar': "⭐️ تفعيل/تعطيل نجوم تيليجرام",
        'ru': "⭐️ Вкл/Выкл Telegram Stars"
    },
    'btn_admin_set_stars_rate': {
        'en': "💱 Set Stars Exchange Rate",
        'ar': "💱 تعيين سعر صرف النجوم",
        'ru': "💱 Задать курс Stars"
    },
    'btn_admin_toggle_cryptobot': {
        'en': "🤖 Toggle Crypto Bot",
        'ar': "🤖 تفعيل/تعطيل Crypto Bot",
        'ru': "🤖 Вкл/Выкл Crypto Bot"
    },
    'btn_admin_toggle_cryptotransfer': {
        'en': "🪙 Toggle Crypto Transfer",
        'ar': "🪙 تفعيل/تعطيل التحويل المشفر",
        'ru': "🪙 Вкл/Выкл ручной перевод крипты"
    },
    'btn_admin_set_usdt_addr': {
        'en': "✍️ Set USDT BEP20 Address",
        'ar': "✍️ تعيين عنوان USDT BEP20",
        'ru': "✍️ Задать адрес USDT BEP20"
    },
    'btn_admin_set_ltc_addr': {
        'en': "✍️ Set LTC Address",
        'ar': "✍️ تعيين عنوان LTC",
        'ru': "✍️ Задать адрес LTC"
    },
    'btn_admin_set_ton_addr': {
        'en': "✍️ Set TON Address",
        'ar': "✍️ تعيين عنوان TON",
        'ru': "✍️ Задать адрес TON"
    },
    'btn_admin_set_binance_addr': {
        'en': "✍️ Set Binance ID/Email/Phone",
        'ar': "✍️ تعيين معرف Binance / الإيميل",
        'ru': "✍️ Задать Binance ID/Email/Phone"
    },
    'btn_admin_set_ref_bonus': {
        'en': "✍️ Edit Fixed Bonus Reward",
        'ar': "✍️ تعديل مكافأة الإحالة الثابتة",
        'ru': "✍️ Изменить фиксированный бонус"
    },
    'btn_setup_new_prov': {
        'en': "➕ Add New Provider",
        'ar': "➕ إضافة مزود جديد",
        'ru': "➕ Добавить нового поставщика"
    },
    'btn_prov_editkey': {
        'en': "🔑 Update API Token",
        'ar': "🔑 تعديل مفتاح API",
        'ru': "🔑 Изменить токен API"
    },
    'btn_prov_pull': {
        'en': "📥 Pull/Import Products",
        'ar': "📥 سحب واستيراد المنتجات",
        'ru': "📥 Импортировать товары"
    },
    'btn_prov_delete': {
        'en': "❌ Delete Provider",
        'ar': "❌ حذف المزود",
        'ru': "❌ Удалить поставщика"
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
