import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class OrderStates(StatesGroup):
    waiting_for_transaction_type = State()  # Новое состояние для выбора типа операции
    waiting_for_payment_type = State()
    waiting_for_order_details = State()
    waiting_for_confirmation = State()
    # Новые состояния для расхода
    waiting_for_expense_method = State()
    waiting_for_expense_details = State()
    waiting_for_expense_confirmation = State()

TRANSACTION_TYPES = ["Приход", "Расход"]

PAYMENT_TYPES = [
    "ИП Цацура Е.Е.",
    "ИП Цацура Д.Е.", 
    "Наличные",
    "ООО «Самурай 24»",
    "ООО «ГУАРДДО»"
]

EXPENSE_METHODS = [
    "ИП Цацура Е.Е.",
    "ИП Цацура Д.Е.", 
    "Наличные",
    "ООО «Самурай 24»",
    "ООО «ГУАРДДО»",
    "Крипта",
    "Европейская компания (доллары или евро)"
]

def get_transaction_type_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=transaction_type)] for transaction_type in TRANSACTION_TYPES],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_payment_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=payment_type)] for payment_type in PAYMENT_TYPES],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_expense_method_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=expense_method)] for expense_method in EXPENSE_METHODS],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# Создаем клавиатуру для подтверждения
def get_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_send"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_order")
        ]
    ])
    return keyboard

# Создаем клавиатуру для подтверждения расхода
def get_expense_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_expense_send"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_expense")
        ]
    ])
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(OrderStates.waiting_for_transaction_type)
    await message.answer(
        "Выберите тип операции:",
        reply_markup=get_transaction_type_keyboard()
    )

# Обработчик выбора типа операции
@dp.message(OrderStates.waiting_for_transaction_type)
async def process_transaction_type_selection(message: types.Message, state: FSMContext):
    if message.text == "Приход":
        await state.update_data(transaction_type="Приход")
        await state.set_state(OrderStates.waiting_for_payment_type)
        await message.answer(
            "Добро пожаловать! Выберите тип оплаты:",
            reply_markup=get_payment_keyboard()
        )
    elif message.text == "Расход":
        await state.update_data(transaction_type="Расход")
        await state.set_state(OrderStates.waiting_for_expense_method)
        await message.answer(
            "Каким образом был осуществлен расход:",
            reply_markup=get_expense_method_keyboard()
        )
    else:
        await message.answer("Пожалуйста, выберите один из предложенных типов операции")

# Обработчик выбора способа расхода
@dp.message(OrderStates.waiting_for_expense_method)
async def process_expense_method_selection(message: types.Message, state: FSMContext):
    if message.text in EXPENSE_METHODS:
        await state.update_data(expense_method=message.text)
        await state.set_state(OrderStates.waiting_for_expense_details)
        await message.answer(
            "Напишите финальную сумму расхода с указанием на что осуществлена трата.\n\n"
            "Пример:\n"
            "700 000 рублей\n"
            "Отправка образцов\n"
            "ООО АНКОМ",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.answer("Пожалуйста, выберите один из предложенных способов расхода")

# Обработчик ввода деталей расхода
@dp.message(OrderStates.waiting_for_expense_details)
async def process_expense_details(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    expense_method = data.get("expense_method")
    expense_details = message.text
    
    # Сохраняем детали расхода
    await state.update_data(expense_details=expense_details)
    
    # Формируем финальное сообщение для проверки
    preview_message = f"📋 Проверьте информацию о расходе:\n\n"
    preview_message += f"💰 Способ расхода: {expense_method}\n"
    preview_message += f"📦 Детали расхода:\n{expense_details}\n"
    preview_message += f"👤 Отправитель: @{message.from_user.username or 'Неизвестно'}\n\n"
    preview_message += f"Всё верно? Выберите действие:"
    
    await state.set_state(OrderStates.waiting_for_expense_confirmation)
    await message.answer(
        preview_message,
        reply_markup=get_expense_confirmation_keyboard()
    )

# Обработчик выбора типа оплаты (для прихода)
@dp.message(OrderStates.waiting_for_payment_type)
async def process_payment_selection(message: types.Message, state: FSMContext):
    if message.text in PAYMENT_TYPES:
        await state.update_data(payment_type=message.text)
        await state.set_state(OrderStates.waiting_for_order_details)
        await message.answer(
            "Напишите количество проданных товаров и финальную сумму, с упоминанием скидки если есть.\n\n"
            "Пример:\n"
            "Флешка 64гб 2шт. - 48 000\n"
            "Мини диск 1ТБ 1шт. - 22 000\n\n"
            "70 000 рублей\n"
            "С учётом скидки 15%\n\n"
            "ООО АНКОМ",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.answer("Пожалуйста, выберите один из предложенных типов оплаты")

# Обработчик ввода деталей заказа (для прихода)
@dp.message(OrderStates.waiting_for_order_details)
async def process_order_details(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    payment_type = data.get("payment_type")
    order_details = message.text
    
    # Сохраняем детали заказа
    await state.update_data(order_details=order_details)
    
    # Формируем финальное сообщение для проверки
    preview_message = f"📋 Проверьте информацию о заказе:\n\n"
    preview_message += f"💰 Тип оплаты: {payment_type}\n"
    preview_message += f"📦 Детали заказа:\n{order_details}\n"
    preview_message += f"👤 Отправитель: @{message.from_user.username or 'Неизвестно'}\n\n"
    preview_message += f"Всё верно? Выберите действие:"
    
    await state.set_state(OrderStates.waiting_for_confirmation)
    await message.answer(
        preview_message,
        reply_markup=get_confirmation_keyboard()
    )

# Обработчик нажатий на кнопки подтверждения
@dp.callback_query(lambda c: c.data in ["confirm_send", "edit_order", "confirm_expense_send", "edit_expense"])
async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_send":
        # Отправляем заказ администратору
        await send_order_to_admin(callback.message, state)
    elif callback.data == "edit_order":
        # Возвращаемся к редактированию заказа
        await edit_order(callback.message, state)
    elif callback.data == "confirm_expense_send":
        # Отправляем расход администратору
        await send_expense_to_admin(callback.message, state)
    elif callback.data == "edit_expense":
        # Возвращаемся к редактированию расхода
        await edit_expense(callback.message, state)
    
    await callback.answer()

# Функция отправки заказа администратору (для прихода)
async def send_order_to_admin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    payment_type = data.get("payment_type")
    order_details = data.get("order_details")
    
    # Формируем финальное сообщение для администратора
    admin_message = f"💰 Новый приход!\n\n"
    admin_message += f"💳 Тип оплаты: {payment_type}\n"
    admin_message += f"📦 Детали заказа:\n{order_details}\n"
    admin_message += f"👤 Отправитель: @{message.from_user.username or 'Неизвестно'}"
    
    try:
        # Отправляем уведомление администратору по ID
        await bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)
        
        # Подтверждаем пользователю
        await message.answer(
            f"✅ Спасибо! Информация о приходе отправлена {ADMIN_USERNAME} в систему учёта.\n\n"
            "Для создания новой операции используйте /start"
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке информации. Попробуйте позже или обратитесь к администратору."
        )

# Функция отправки расхода администратору
async def send_expense_to_admin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    expense_method = data.get("expense_method")
    expense_details = data.get("expense_details")
    
    # Формируем финальное сообщение для администратора
    admin_message = f"💸 Новый расход!\n\n"
    admin_message += f"💳 Способ расхода: {expense_method}\n"
    admin_message += f"📦 Детали расхода:\n{expense_details}\n"
    admin_message += f"👤 Отправитель: @{message.from_user.username or 'Неизвестно'}"
    
    try:
        # Отправляем уведомление администратору по ID
        await bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)
        
        # Подтверждаем пользователю
        await message.answer(
            f"✅ Спасибо! Информация о расходе отправлена {ADMIN_USERNAME} в систему учёта.\n\n"
            "Для создания новой операции используйте /start"
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке информации. Попробуйте позже или обратитесь к администратору."
        )

# Функция редактирования заказа (для прихода)
async def edit_order(message: types.Message, state: FSMContext):
    # Возвращаемся к вводу деталей заказа
    await state.set_state(OrderStates.waiting_for_order_details)
    await message.answer(
        "Введите заново количество проданных товаров и финальную сумму, с упоминанием скидки если есть.\n\n"
        "Пример:\n"
        "Флешка 64гб 2шт. - 48 000\n"
        "Мини диск 1ТБ 1шт. - 22 000\n\n"
        "70 000 рублей\n"
        "С учётом скидки 15%\n\n"
        "ООО АНКОМ"
    )

# Функция редактирования расхода
async def edit_expense(message: types.Message, state: FSMContext):
    # Возвращаемся к вводу деталей расхода
    await state.set_state(OrderStates.waiting_for_expense_details)
    await message.answer(
        "Введите заново финальную сумму расхода с указанием на что осуществлена трата.\n\n"
        "Пример:\n"
        "700 000 рублей\n"
        "Отправка образцов\n"
        "ООО АНКОМ"
    )

# Обработчик неизвестных сообщений
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(
        "Используйте /start для создания новой операции"
    )

# Главная функция
async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())