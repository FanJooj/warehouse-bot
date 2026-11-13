from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database
from keyboards import get_main_menu, get_cancel_keyboard, get_products_inline_keyboard, get_confirm_delete_keyboard
from config import ALLOWED_USERS

router = Router()

class WarehouseStates(StatesGroup):
    waiting_for_add_name = State()
    waiting_for_add_quantity = State()
    waiting_for_remove_quantity = State()
    waiting_for_search_query = State()
    waiting_for_delete_confirm = State()


@router.message.middleware()
async def access_middleware(handler, event, data):
    user_id = event.from_user.id
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        await event.answer("У вас нет доступа.")
        return
    return await handler(event, data)

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Это бот для складского учёта.\nВыберите действие на клавиатуре:",
        reply_markup=get_main_menu()
    )

@router.message(F.text == "/cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


@router.message(F.text == "📦 Добавить товар")
async def start_add(message: Message, state: FSMContext):
    await state.set_state(WarehouseStates.waiting_for_add_name)
    await message.answer("Введите вид (название) товара:", reply_markup=get_cancel_keyboard())

@router.message(WarehouseStates.waiting_for_add_name)
async def process_add_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст.")
        return
    name = message.text.strip()
    if not (2 <= len(name) <= 100):
        await message.answer("Название должно быть от 2 до 100 символов. Попробуйте снова:")
        return
    
    await state.update_data(product_name=name)
    await state.set_state(WarehouseStates.waiting_for_add_quantity)
    await message.answer("Введите количество:")

@router.message(WarehouseStates.waiting_for_add_quantity)
async def process_add_quantity(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Введите целое число больше 0:")
        return
    
    qty = int(message.text)
    if qty <= 0 or qty > 1_000_000:
        await message.answer("Количество должно быть от 1 до 1 000 000. Введите целое число:")
        return
    
    data = await state.get_data()
    product_name = data.get("product_name")
    
    user_name = message.from_user.full_name or "Unknown"
    try:
        success, response_text = database.add_product(product_name, qty, message.from_user.id, user_name)
        await state.clear()
        await message.answer(response_text, reply_markup=get_main_menu())
    except Exception:
        await state.clear()
        await message.answer("Что-то пошло не так, попробуйте ещё раз", reply_markup=get_main_menu())


@router.message(F.text == "📤 Списать товар")
async def start_remove(message: Message):
    products = database.get_all_products()
    if not products:
        await message.answer("Склад пуст, списывать нечего.", reply_markup=get_main_menu())
        return
    
    keyboard = get_products_inline_keyboard(products, action_prefix="rem")
    await message.answer("Выберите товар для списания:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("rem_"))
async def process_remove_selection(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    product = database.get_product_by_id(product_id)
    if not product:
        await callback.message.edit_text("Товар не найден.")
        return
    
    await state.update_data(remove_product_id=product_id)
    await state.set_state(WarehouseStates.waiting_for_remove_quantity)
    await callback.message.edit_text(f"Выбран товар: <b>{product['display_name']}</b> (на складе: {product['quantity']} шт.)\nВведите количество для списания:")

@router.message(WarehouseStates.waiting_for_remove_quantity)
async def process_remove_quantity(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Введите целое число больше 0:")
        return
    
    qty = int(message.text)
    if qty <= 0:
        await message.answer("Количество должно быть больше 0:")
        return
    
    data = await state.get_data()
    product_id = data.get("remove_product_id")
    
    user_name = message.from_user.full_name or "Unknown"
    success, response_text = database.update_quantity(product_id, -qty, "remove", message.from_user.id, user_name)
    
    if not success:
        await message.answer(f"{response_text} Введите корректное количество:")
        return
    
    await state.clear()
    await message.answer(f"Списано {qty} шт. {response_text}", reply_markup=get_main_menu())


@router.message(F.text == "📋 Остатки")
async def show_stock(message: Message):
    products = database.get_all_products()
    if not products:
        await message.answer("Склад пуст. Добавьте первый товар.", reply_markup=get_main_menu())
        return
    
    lines = ["<b>Остатки на складе:</b>"]
    total_units = 0
    for idx, p in enumerate(products, 1):
        lines.append(f"{idx}. {p['display_name']} — {p['quantity']} шт.")
        total_units += p['quantity']
        
    lines.append(f"\nВсего позиций: {len(products)} · Всего единиц: {total_units}")
    
    text = "\n".join(lines)
   
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await message.answer(text[x:x+4000])
        await message.answer("Главное меню:", reply_markup=get_main_menu())
    else:
        await message.answer(text, reply_markup=get_main_menu())


@router.message(F.text == "🔍 Найти товар")
async def start_search(message: Message, state: FSMContext):
    await state.set_state(WarehouseStates.waiting_for_search_query)
    await message.answer("Введите часть названия товара для поиска:", reply_markup=get_cancel_keyboard())

@router.message(WarehouseStates.waiting_for_search_query)
async def process_search(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст.")
        return
    
    query = message.text.strip()
    products = database.search_products(query)
    await state.clear()
    
    if not products:
        await message.answer("Ничего не найдено.", reply_markup=get_main_menu())
        return
    
    lines = ["<b>Результаты поиска:</b>"]
    for p in products:
        lines.append(f"• {p['display_name']} — {p['quantity']} шт.")
        
    await message.answer("\n".join(lines), reply_markup=get_main_menu())


@router.message(F.text == "🗑 Удалить товар")
async def start_delete(message: Message):
    products = database.get_all_products()
    if not products:
        await message.answer("Склад пуст, удалять нечего.", reply_markup=get_main_menu())
        return
    
    keyboard = get_products_inline_keyboard(products, action_prefix="del")
    await message.answer("Выберите товар для удаления:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("del_"))
async def process_delete_selection(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    product = database.get_product_by_id(product_id)
    if not product:
        await callback.message.edit_text("Товар не найден.")
        return
    
    await state.update_data(delete_product_id=product_id)
    await callback.message.edit_text(
        f"Вы уверены, что хотите полностью удалить товар <b>{product['display_name']}</b>?",
        reply_markup=get_confirm_delete_keyboard(product_id)
    )

@router.callback_query(F.data.startswith("conf_del_"))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    user_name = callback.from_user.full_name or "Unknown"
    
    database.delete_product(product_id, callback.from_user.id, user_name)
    await state.clear()
    await callback.message.edit_text("Товар удалён.")
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())

@router.callback_query(F.data == "cancel_del")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Удаление отменено.")
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())


@router.message(F.text == "📜 История операций")
async def show_history(message: Message):
    operations = database.get_last_operations(20)
    if not operations:
        await message.answer("История операций пуста.", reply_markup=get_main_menu())
        return
    
    lines = ["<b>Последние операции:</b>"]
    for op in operations:
        
        try:
             dt_part = op['created_at'].split()
             date_s = "".join(reversed(dt_part[0].split("-"))) 
             time_s = dt_part[1][:5]
             formatted_date = f"{dt_part[0][8:10]}.{dt_part[0][5:7]}.{dt_part[0][:4]} {time_s}"
        except:
            formatted_date = op['created_at']
            
        delta_str = f"+{op['delta']}" if op['delta'] > 0 else str(op['delta'])
        lines.append(f"{formatted_date} — {op['user_name']}: {delta_str} {op['product_name']}")
        
    await message.answer("\n".join(lines), reply_markup=get_main_menu())


@router.message()
async def unknown_message(message: Message):
    await message.answer("Используйте кнопки меню или команду /cancel для сброса диалога.", reply_markup=get_main_menu())