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
    waiting_for_payment_type = State()
    waiting_for_order_details = State()
    waiting_for_confirmation = State()

PAYMENT_TYPES = [
    "ИП Цацура Е.Е.",
    "ИП Цацура Д.Е.", 
    "Наличные",
    "ООО «Самурай 24»",
    "ООО «ГУАРДДО»"
]

def get_payment_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=payment_type)] for payment_type in PAYMENT_TYPES],
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

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(OrderStates.waiting_for_payment_type)
    await message.answer(
        "Добро пожаловать! Выберите тип оплаты:",
        reply_markup=get_payment_keyboard()
    )

# Обработчик выбора типа оплаты
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

# Обработчик ввода деталей заказа
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
@dp.callback_query(lambda c: c.data in ["confirm_send", "edit_order"])
async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_send":
        # Отправляем заказ администратору
        await send_order_to_admin(callback.message, state)
    elif callback.data == "edit_order":
        # Возвращаемся к редактированию
        await edit_order(callback.message, state)
    
    await callback.answer()

# Функция отправки заказа администратору
async def send_order_to_admin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    payment_type = data.get("payment_type")
    order_details = data.get("order_details")
    
    # Формируем финальное сообщение для администратора
    admin_message = f"�� Новый заказ!\n\n"
    admin_message += f"💰 Тип оплаты: {payment_type}\n"
    admin_message += f"📦 Детали заказа:\n{order_details}\n"
    admin_message += f"👤 Отправитель: @{message.from_user.username or 'Неизвестно'}"
    
    try:
        # Отправляем уведомление администратору по ID
        await bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)
        
        # Подтверждаем пользователю
        await message.answer(
            f"✅ Спасибо! Информация о заказе отправлена {ADMIN_USERNAME} в систему учёта.\n\n"
            "Для создания нового заказа используйте /start"
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке информации. Попробуйте позже или обратитесь к администратору."
        )

# Функция редактирования заказа
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

# Обработчик неизвестных сообщений
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(
        "Используйте /start для создания нового заказа"
    )

# Команда для получения ID пользователя
# @dp.message(Command("myid"))
# async def cmd_myid(message: types.Message):
#     user_id = message.from_user.id
#     username = message.from_user.username or "Неизвестно"
#     await message.answer(f"Ваш ID: {user_id}\nUsername: @{username}")

# Главная функция
async def main():
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())