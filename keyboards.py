from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Добавить товар"), KeyboardButton(text="📤 Списать товар")],
            [KeyboardButton(text="📋 Остатки"), KeyboardButton(text="🔍 Найти товар")],
            [KeyboardButton(text="🗑 Удалить товар"), KeyboardButton(text="📜 История операций")]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/cancel")]],
        resize_keyboard=True
    )

def get_products_inline_keyboard(products, action_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardMarkup(inline_keyboard=[])
    for p in products:
        builder.inline_keyboard.append([
            InlineKeyboardButton(text=f"{p['display_name']} ({p['quantity']} шт.)", callback_data=f"{action_prefix}_{p['id']}")
        ])
    return builder

def get_confirm_delete_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"conf_del_{product_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_del")
        ]
    ])