"""
Клавиатуры для Telegram бота
"""
from typing import Optional
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


class Keyboards:
    """Фабрика клавиатур"""
    
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """Главное меню для клиента (старое - для обратной совместимости)"""
        keyboard = [
            [KeyboardButton("🚖 Заказать такси")],
            [KeyboardButton("📍 Мой заказ"), KeyboardButton("🛣 Межгород")],
            [KeyboardButton("📋 Мои заказы"), KeyboardButton("💵 Тарифы")],
            [KeyboardButton("📜 Правила пользования"), KeyboardButton("ℹ️ Помощь")],
            [KeyboardButton("📞 Связаться")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def main_user() -> ReplyKeyboardMarkup:
        """Главное меню для клиента (новое - упрощённое)"""
        keyboard = [
            [KeyboardButton("🚖 Заказать такси")],
            [KeyboardButton("🧭 Межгород"), KeyboardButton("🧾 Мои поездки")],
            [KeyboardButton("ℹ️ Правила"), KeyboardButton("❌ Отмена")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def driver_menu() -> ReplyKeyboardMarkup:
        """Меню для водителя (старое - для обратной совместимости)"""
        keyboard = [
            [KeyboardButton("🟢 Я на линии"), KeyboardButton("🔴 Я оффлайн")],
            [KeyboardButton("📋 Мои заказы"), KeyboardButton("📊 Статистика")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def main_driver() -> ReplyKeyboardMarkup:
        """Главное меню для водителя (новое)"""
        keyboard = [
            [KeyboardButton("🟢 Я на линии"), KeyboardButton("🔴 В оффлайн")],
            [KeyboardButton("🧾 Мои поездки"), KeyboardButton("📊 Статистика")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def request_phone() -> ReplyKeyboardMarkup:
        """Запрос номера телефона"""
        keyboard = [
            [KeyboardButton("📱 Поделиться номером", request_contact=True)],
            [KeyboardButton("✍️ Ввести номер вручную")],
            [KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def manual_input_with_cancel(cancel_label: str = "❌ Отмена") -> ReplyKeyboardMarkup:
        """Клавиатура для ручного ввода с кнопкой отмены"""
        keyboard = [[KeyboardButton(cancel_label)]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def confirm_order(order_id: int) -> InlineKeyboardMarkup:
        """Подтверждение заказа"""
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_order:{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_order:{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def driver_order_action(order_id: int) -> InlineKeyboardMarkup:
        """Действия водителя с заказом"""
        keyboard = [
            [InlineKeyboardButton("✅ Принять заказ", callback_data=f"accept_order:{order_id}")],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_order:{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def order_status_actions(order_id: int, status: str) -> InlineKeyboardMarkup:
        """Действия в зависимости от статуса заказа"""
        keyboard = []
        
        if status == "accepted":
            keyboard.append([InlineKeyboardButton("🚗 Начать поездку", callback_data=f"start_order:{order_id}")])
        elif status == "in_progress":
            keyboard.append([InlineKeyboardButton("✅ Завершить поездку", callback_data=f"complete_order:{order_id}")])
        
        keyboard.append([InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order:{order_id}")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def rate_driver(order_id: int) -> InlineKeyboardMarkup:
        """Оценка водителя"""
        keyboard = [
            [
                InlineKeyboardButton("⭐", callback_data=f"rate:{order_id}:1"),
                InlineKeyboardButton("⭐⭐", callback_data=f"rate:{order_id}:2"),
                InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate:{order_id}:3"),
            ],
            [
                InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate:{order_id}:4"),
                InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate:{order_id}:5"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def cancel_action() -> ReplyKeyboardMarkup:
        """Кнопка отмены"""
        keyboard = [[KeyboardButton("❌ Отмена")]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def customer_cancel_order(order_id: int) -> InlineKeyboardMarkup:
        """Кнопка отмены заказа для клиента"""
        keyboard = [
            [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"customer_cancel:{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def select_district() -> ReplyKeyboardMarkup:
        """Выбор района для заказа"""
        keyboard = [
            [KeyboardButton("Старое Жуково"), KeyboardButton("Новое Жуково")],
            [KeyboardButton("Мысовцево"), KeyboardButton("Авдон")],
            [KeyboardButton("Дёма"), KeyboardButton("Уптино")],
            [KeyboardButton("Сергеевка"), KeyboardButton("Аэропорт")],
            [KeyboardButton("Ж/Д вокзал"), KeyboardButton("Уфа")],
            [KeyboardButton("По Жуково"), KeyboardButton("По Дёме")],
            [KeyboardButton("По Авдону"), KeyboardButton("По Сергеевке")],
            [KeyboardButton("Прочие направления"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_po_zhukovo_pickup() -> ReplyKeyboardMarkup:
        """Подменю выбора района Жуково"""
        keyboard = [
            [KeyboardButton("Новое Жуково"), KeyboardButton("Старое Жуково")],
            [KeyboardButton("🔙 Назад"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_ufa_pickup() -> ReplyKeyboardMarkup:
        """Подменю выбора района Уфы для отправления"""
        keyboard = [
            [KeyboardButton("Уфа-Центр"), KeyboardButton("Телецентр")],
            [KeyboardButton("Сипайлово"), KeyboardButton("Черниковка")],
            [KeyboardButton("Инорс"), KeyboardButton("Зелёная роща")],
            [KeyboardButton("Чесноковка"), KeyboardButton("Проспект Октября")],
            [KeyboardButton("🔙 Назад"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_prospekt_oktyabrya_submenu() -> ReplyKeyboardMarkup:
        """Подменю выбора точки на Проспекте Октября"""
        keyboard = [
            [KeyboardButton("Галле"), KeyboardButton("Горсовет")],
            [KeyboardButton("ГДК")],
            [KeyboardButton("⬅️ Назад"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_destination_zone() -> ReplyKeyboardMarkup:
        """Выбор района назначения (общий список - полная версия)"""
        keyboard = [
            [KeyboardButton("Уфа"), KeyboardButton("Аэропорт")],
            [KeyboardButton("Ж/Д вокзал"), KeyboardButton("Прочие направления")],
            [KeyboardButton("Старое Жуково"), KeyboardButton("Новое Жуково")],
            [KeyboardButton("Мысовцево"), KeyboardButton("Дёма")],
            [KeyboardButton("Авдон"), KeyboardButton("Уптино")],
            [KeyboardButton("Затон"), KeyboardButton("ТРЦ МЕГА")],
            [KeyboardButton("Вьетнамский рынок"), KeyboardButton("Яркий")],
            [KeyboardButton("🔙 Изменить район"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_destination_from_other() -> ReplyKeyboardMarkup:
        """Выбор назначения для 'Прочих направлений' - только 6 базовых зон"""
        keyboard = [
            [KeyboardButton("Старое Жуково"), KeyboardButton("Новое Жуково")],
            [KeyboardButton("Мысовцево"), KeyboardButton("Дёма")],
            [KeyboardButton("Авдон"), KeyboardButton("Уптино")],
            [KeyboardButton("🔙 Изменить район"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_ufa_destination() -> ReplyKeyboardMarkup:
        """Подменю выбора района Уфы для назначения"""
        keyboard = [
            [KeyboardButton("Уфа-Центр"), KeyboardButton("Телецентр")],
            [KeyboardButton("Сипайлово"), KeyboardButton("Черниковка")],
            [KeyboardButton("Инорс"), KeyboardButton("Зелёная роща")],
            [KeyboardButton("Чесноковка"), KeyboardButton("Проспект Октября")],
            [KeyboardButton("🔙 Назад"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    @staticmethod
    def select_airport_terminal() -> ReplyKeyboardMarkup:
        """Выбор терминала аэропорта"""
        keyboard = [
            [KeyboardButton("Терминал 1"), KeyboardButton("Терминал 2")],
            [KeyboardButton("🔙 Назад"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def select_other_destinations() -> ReplyKeyboardMarkup:
        """Подменю прочих направлений"""
        keyboard = [
            [KeyboardButton("Дмитриевка"), KeyboardButton("Михайловка")],
            [KeyboardButton("Миловский Парк"), KeyboardButton("Миловка")],
            [KeyboardButton("Николаевка"), KeyboardButton("Юматово")],
            [KeyboardButton("Алкино"), KeyboardButton("Кафе Отдых")],
            [KeyboardButton("Чесноковка"), KeyboardButton("Затон")],
            [KeyboardButton("Иглино"), KeyboardButton("Шакша")],
            [KeyboardButton("Акбердино"), KeyboardButton("Нагаево")],
            [KeyboardButton("Чишмы")],
            [KeyboardButton("🔙 Назад"), KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    @staticmethod
    def intercity_menu() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton("🚀 Заказать межгород")],
            [KeyboardButton("🔙 В главное меню")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    @staticmethod
    def intercity_origin_selector() -> ReplyKeyboardMarkup:
        keyboard = [
            [KeyboardButton("Дёма"), KeyboardButton("Жуково")],
            [KeyboardButton("Мысовцево")],
            [KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    @staticmethod
    def intercity_driver_actions(order_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("✉️ Откликнуться", callback_data=f"intercity_reply:{order_id}")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def intercity_proposal_actions(order_id: int, driver_id: int, driver_telegram_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton(
                    "💬 Связаться в Telegram",
                    url=f"tg://user?id={driver_telegram_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Выбрать водителя",
                    callback_data=f"intercity_select:{order_id}:{driver_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def intercity_driver_confirm(order_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить поездку", callback_data=f"intercity_confirm:{order_id}")],
            [InlineKeyboardButton("❌ Отменить предложение", callback_data=f"intercity_cancel:{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def driver_select_district() -> ReplyKeyboardMarkup:
        """Выбор района для водителя"""
        keyboard = [
            [KeyboardButton("📍 Новое Жуково"), KeyboardButton("📍 Старое Жуково")],
            [KeyboardButton("📍 Мысовцево"), KeyboardButton("📍 Дёма")],
            [KeyboardButton("📍 Авдон"), KeyboardButton("📍 Уптино")],
            [KeyboardButton("📍 Сергеевка")],
            [KeyboardButton("🔙 Назад")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def driver_after_accept(order_id: int, customer_phone: Optional[str] = None, customer_username: Optional[str] = None, customer_telegram_id: Optional[int] = None) -> InlineKeyboardMarkup:
        """Клавиатура для водителя после принятия заказа"""
        keyboard = [
            [InlineKeyboardButton("🚗 Подъехал", callback_data=f"trip:arrived:{order_id}")],
            [InlineKeyboardButton("⌛ Жду клиента", callback_data=f"trip:waiting:{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"trip:cancel:{order_id}")]
        ]
        
        # Добавляем контакты клиента, если есть
        contact_buttons = []
        if customer_phone:
            contact_buttons.append(InlineKeyboardButton("📞 Позвонить клиенту", url=f"tel:+7{customer_phone.replace('+7', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"))
        if customer_username:
            contact_buttons.append(InlineKeyboardButton("💬 Написать клиенту", url=f"https://t.me/{customer_username}"))
        elif customer_telegram_id:
            contact_buttons.append(InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={customer_telegram_id}"))
        
        if contact_buttons:
            keyboard.append(contact_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def driver_arrived(order_id: int, customer_phone: Optional[str] = None, customer_username: Optional[str] = None, customer_telegram_id: Optional[int] = None) -> InlineKeyboardMarkup:
        """Клавиатура для водителя после подъезда"""
        keyboard = [
            [InlineKeyboardButton("▶️ Поехали", callback_data=f"trip:start:{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"trip:cancel:{order_id}")]
        ]
        
        # Добавляем контакты клиента, если есть
        contact_buttons = []
        if customer_phone:
            contact_buttons.append(InlineKeyboardButton("📞 Позвонить клиенту", url=f"tel:+7{customer_phone.replace('+7', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"))
        if customer_username:
            contact_buttons.append(InlineKeyboardButton("💬 Написать клиенту", url=f"https://t.me/{customer_username}"))
        elif customer_telegram_id:
            contact_buttons.append(InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={customer_telegram_id}"))
        
        if contact_buttons:
            keyboard.append(contact_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def driver_onboard(order_id: int, customer_phone: Optional[str] = None, customer_username: Optional[str] = None, customer_telegram_id: Optional[int] = None) -> InlineKeyboardMarkup:
        """Клавиатура для водителя во время поездки"""
        keyboard = [
            [InlineKeyboardButton("🏁 Завершить поездку", callback_data=f"trip:finish:{order_id}")]
        ]
        
        # Добавляем контакты клиента, если есть
        contact_buttons = []
        if customer_phone:
            contact_buttons.append(InlineKeyboardButton("📞 Позвонить клиенту", url=f"tel:+7{customer_phone.replace('+7', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"))
        if customer_username:
            contact_buttons.append(InlineKeyboardButton("💬 Написать клиенту", url=f"https://t.me/{customer_username}"))
        elif customer_telegram_id:
            contact_buttons.append(InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={customer_telegram_id}"))
        
        if contact_buttons:
            keyboard.append(contact_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def client_rating(order_id: int) -> InlineKeyboardMarkup:
        """Клавиатура для оценки поездки клиентом"""
        keyboard = [
            [
                InlineKeyboardButton("⭐1", callback_data=f"rate:{order_id}:1"),
                InlineKeyboardButton("⭐2", callback_data=f"rate:{order_id}:2"),
                InlineKeyboardButton("⭐3", callback_data=f"rate:{order_id}:3"),
                InlineKeyboardButton("⭐4", callback_data=f"rate:{order_id}:4"),
                InlineKeyboardButton("⭐5", callback_data=f"rate:{order_id}:5"),
            ],
            [InlineKeyboardButton("✍️ Комментарий", callback_data=f"rate_comment:{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def contact_driver(username: Optional[str] = None, telegram_id: Optional[int] = None, phone: Optional[str] = None) -> Optional[InlineKeyboardMarkup]:
        """Клавиатура для связи с водителем"""
        keyboard = []
        
        # Кнопка "Написать водителю"
        if username:
            keyboard.append([InlineKeyboardButton("💬 Написать водителю", url=f"https://t.me/{username}")])
        elif telegram_id:
            keyboard.append([InlineKeyboardButton("💬 Написать водителю", url=f"tg://user?id={telegram_id}")])
        
        # Кнопка "Позвонить" (если есть телефон)
        if phone:
            # Очищаем номер от форматирования
            clean_phone = phone.replace('+7', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            keyboard.append([InlineKeyboardButton("📞 Позвонить", url=f"tel:+7{clean_phone}")])
        
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    
    @staticmethod
    def client_arrived_actions(order_id: int) -> InlineKeyboardMarkup:
        """Клавиатура для клиента когда водитель подъехал"""
        keyboard = [
            [InlineKeyboardButton("🚶 Выхожу", callback_data=f"client_coming:{order_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data=f"client_cancel_arrived:{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

