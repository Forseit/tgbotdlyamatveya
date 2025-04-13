import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler, 
    MessageHandler, 
    CallbackContext, 
    CallbackQueryHandler,
    filters
)
import asyncio
from googletrans import Translator
from datetime import datetime
import json
import os
from threading import Timer as ThreadTimer

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Пути к файлам для хранения данных
CARDS_FILE = 'memory_cards.json'
CALENDAR_FILE = 'calendar_events.json'
LINKS_FILE = 'useful_links.json'

# Загрузка данных из файлов
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Сохранение данных в файлы
def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Инициализация файлов данных, если они не существуют
if not os.path.exists(CARDS_FILE):
    save_data({}, CARDS_FILE)
if not os.path.exists(CALENDAR_FILE):
    save_data({}, CALENDAR_FILE)
if not os.path.exists(LINKS_FILE):
    save_data({}, LINKS_FILE)

# Инициализация переводчика
translator = Translator()

# Класс таймера для функции Pomodoro таймера
class PomodoroTimer:
    def __init__(self, context: CallbackContext, chat_id):
        self.context = context
        self.chat_id = chat_id
        self.timer = None
        self.loop = asyncio.get_event_loop()  # Получаем цикл событий

    def start(self, minutes):
        if self.timer is not None:
            self.timer.cancel()
        self.timer = ThreadTimer(minutes * 60, self.time_up)
        self.timer.start()
        asyncio.run_coroutine_threadsafe(
            self.context.bot.send_message(
                chat_id=self.chat_id,
                text=f"Таймер установлен на {minutes} минут. Я уведомлю вас, когда время выйдет!"
            ),
            self.loop  # Используем цикл событий здесь
        )

    def time_up(self):
        asyncio.run_coroutine_threadsafe(
            self.context.bot.send_message(
                chat_id=self.chat_id,
                text="⏰ Время вышло!"
            ),
            self.loop
        )
        self.timer = None
        # Удаляем из активных таймеров по завершении
        if self.chat_id in active_timers:
            del active_timers[self.chat_id]

    def cancel(self):
        if self.timer is not None:
            self.timer.cancel()
            asyncio.run_coroutine_threadsafe(
                self.context.bot.send_message(
                    chat_id=self.chat_id,
                    text="Таймер отменен."
                ),
                self.loop
            )
            self.timer = None
            # Удаляем из активных таймеров при отмене
            if self.chat_id in active_timers:
                del active_timers[self.chat_id]

# Словарь для хранения активных таймеров
active_timers = {}

# Обработчики команд
async def start(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение при команде /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я многофункциональный бот. Вот что я умею:\n\n"
        "🔢 /calculator - Простой калькулятор\n"
        "📚 /cards - Карточки для запоминания\n"
        "🌍 /translate - Переводчик (русский → английский/немецкий/китайский)\n"
        "📅 /calendar - Напоминания о событиях\n"
        "⏱️ /timer - Установить таймер (20 или 40 минут)\n"
        "🔗 /links - Полезные ссылки для студентов\n"
        "ℹ️ /help - Показать это сообщение"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение при команде /help."""
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "🔢 /calculator - Простой калькулятор\n"
        "📚 /cards - Карточки для запоминания\n"
        "🌍 /translate - Переводчик (русский → английский/немецкий/китайский)\n"
        "📅 /calendar - Напоминания о событиях\n"
        "⏱️ /timer - Установить таймер (20 или 40 минут)\n"
        "🔗 /links - Полезные ссылки для студентов\n"
        "ℹ️ /help - Показать это сообщение"
    )

async def calculator(update: Update, context: CallbackContext) -> None:
    """Обработчик команды калькулятора."""
    keyboard = [
        [
            InlineKeyboardButton("7", callback_data='7'),
            InlineKeyboardButton("8", callback_data='8'),
            InlineKeyboardButton("9", callback_data='9'),
            InlineKeyboardButton("/", callback_data='/'),
        ],
        [
            InlineKeyboardButton("4", callback_data='4'),
            InlineKeyboardButton("5", callback_data='5'),
            InlineKeyboardButton("6", callback_data='6'),
            InlineKeyboardButton("*", callback_data='*'),
        ],
        [
            InlineKeyboardButton("1", callback_data='1'),
            InlineKeyboardButton("2", callback_data='2'),
            InlineKeyboardButton("3", callback_data='3'),
            InlineKeyboardButton("-", callback_data='-'),
        ],
        [
            InlineKeyboardButton("0", callback_data='0'),
            InlineKeyboardButton(".", callback_data='.'),
            InlineKeyboardButton("=", callback_data='='),
            InlineKeyboardButton("+", callback_data='+'),
        ],
        [
            InlineKeyboardButton("C", callback_data='C'),
            InlineKeyboardButton("⌫", callback_data='⌫'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Калькулятор:\n0', reply_markup=reply_markup)

async def calculator_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback'ов калькулятора."""
    query = update.callback_query
    await query.answer()

    current_text = query.message.text.split('\n')[-1]
    button_data = query.data

    if button_data == 'C':
        new_text = '0'
    elif button_data == '⌫':
        new_text = current_text[:-1] if len(current_text) > 1 else '0'
    elif button_data == '=':
        try:
            new_text = str(eval(current_text))
        except:
            new_text = 'Ошибка'
    else:
        new_text = current_text + button_data if current_text != '0' else button_data

    await query.edit_message_text(text=f"Калькулятор:\n{new_text}", reply_markup=query.message.reply_markup)

async def cards_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды карточек."""
    keyboard = [
        [InlineKeyboardButton("Добавить карточку", callback_data='add_card')],
        [InlineKeyboardButton("Просмотреть карточки", callback_data='view_cards')],
        [InlineKeyboardButton("Удалить карточку", callback_data='delete_card')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Меню карточек:', reply_markup=reply_markup)

async def cards_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback'ов карточек."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    cards_data = load_data(CARDS_FILE)

    if query.data == 'add_card':
        context.user_data['awaiting_card'] = True
        await query.edit_message_text(text="Отправьте мне информацию для карточки в формате:\n\nПеред: [вопрос]\nЗад: [ответ]")
    elif query.data == 'view_cards':
        if user_id in cards_data and cards_data[user_id]:
            cards_list = "\n\n".join([f"Перед: {card['front']}\nЗад: {card['back']}" for card in cards_data[user_id]])
            await query.edit_message_text(text=f"Ваши карточки:\n\n{cards_list}")
        else:
            await query.edit_message_text(text="У вас пока нет карточек.")
    elif query.data == 'delete_card':
        if user_id in cards_data and cards_data[user_id]:
            keyboard = [[InlineKeyboardButton(card['front'], callback_data=f"delete_{idx}")] 
                       for idx, card in enumerate(cards_data[user_id])]
            keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel_delete')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Выберите карточку для удаления:", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="У вас нет карточек для удаления.")
    elif query.data.startswith('delete_'):
        idx = int(query.data.split('_')[1])
        del cards_data[user_id][idx]
        save_data(cards_data, CARDS_FILE)
        await query.edit_message_text(text="Карточка успешно удалена!")
    elif query.data == 'cancel_delete':
        await query.edit_message_text(text="Удаление отменено.")

async def handle_card_text(update: Update, context: CallbackContext) -> None:
    """Обработчик текстового ввода для карточек."""
    if 'awaiting_card' in context.user_data and context.user_data['awaiting_card']:
        user_id = str(update.message.from_user.id)
        text = update.message.text

        # Парсим данные карточки
        try:
            front = text.split('Перед:')[1].split('Зад:')[0].strip()
            back = text.split('Зад:')[1].strip()
        except:
            await update.message.reply_text("Неверный формат. Пожалуйста, используйте:\n\nПеред: [вопрос]\nЗад: [ответ]")
            return

        # Сохраняем карточку
        cards_data = load_data(CARDS_FILE)
        if user_id not in cards_data:
            cards_data[user_id] = []

        cards_data[user_id].append({
            'front': front,
            'back': back,
            'created_at': str(datetime.now())
        })

        save_data(cards_data, CARDS_FILE)
        await update.message.reply_text("Карточка успешно добавлена!")
        context.user_data['awaiting_card'] = False

async def translate_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды переводчика."""
    keyboard = [
        [InlineKeyboardButton("Русский → Английский", callback_data='ru_en')],
        [InlineKeyboardButton("Русский → Немецкий", callback_data='ru_de')],
        [InlineKeyboardButton("Русский → Китайский", callback_data='ru_zh')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите направление перевода:', reply_markup=reply_markup)

async def translate_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback'ов переводчика."""
    query = update.callback_query
    await query.answer()

    lang_map = {
        'ru_en': ('ru', 'en'),
        'ru_de': ('ru', 'de'),
        'ru_zh': ('ru', 'zh-cn')
    }

    src, dest = lang_map[query.data]
    context.user_data['translation_direction'] = (src, dest)
    await query.edit_message_text(text=f"Выбрано: {src.upper()} → {dest.upper()}\n\nОтправьте мне текст для перевода.")

async def handle_translation_text(update: Update, context: CallbackContext) -> None:
    """Обработчик текстового ввода для перевода."""
    if 'translation_direction' in context.user_data:
        src, dest = context.user_data['translation_direction']
        text = update.message.text

        try:
            translation = translator.translate(text, src=src, dest=dest)
            await update.message.reply_text(f"Перевод:\n\n{translation.text}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка перевода: {str(e)}")

        context.user_data.pop('translation_direction', None)

async def calendar_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды календаря."""
    keyboard = [
        [InlineKeyboardButton("Добавить событие", callback_data='add_event')],
        [InlineKeyboardButton("Просмотреть события", callback_data='view_events')],
        [InlineKeyboardButton("Удалить событие", callback_data='delete_event')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Меню календаря:', reply_markup=reply_markup)

async def calendar_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback'ов календаря."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    calendar_data = load_data(CALENDAR_FILE)

    if query.data == 'add_event':
        context.user_data['awaiting_event'] = True
        await query.edit_message_text(text="Отправьте мне детали события в формате:\n\nДата: ГГГГ-ММ-ДД\nСобытие: [описание]\n\nПример:\nДата: 2023-12-25\nСобытие: Рождество")
    elif query.data == 'view_events':
        if user_id in calendar_data and calendar_data[user_id]:
            events_list = "\n\n".join([f"Дата: {event['date']}\nСобытие: {event['description']}" for event in calendar_data[user_id]])
            await query.edit_message_text(text=f"Ваши события:\n\n{events_list}")
        else:
            await query.edit_message_text(text="У вас пока нет событий.")
    elif query.data == 'delete_event':
        if user_id in calendar_data and calendar_data[user_id]:
            keyboard = [[InlineKeyboardButton(f"{event['date']} - {event['description']}", callback_data=f"delete_event_{idx}")] 
                       for idx, event in enumerate(calendar_data[user_id])]
            keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel_delete_event')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Выберите событие для удаления:", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="У вас нет событий для удаления.")
    elif query.data.startswith('delete_event_'):
        idx = int(query.data.split('_')[2])
        del calendar_data[user_id][idx]
        save_data(calendar_data, CALENDAR_FILE)
        await query.edit_message_text(text="Событие успешно удалено!")
    elif query.data == 'cancel_delete_event':
        await query.edit_message_text(text="Удаление отменено.")

async def handle_event_text(update: Update, context: CallbackContext) -> None:
    """Обработчик текстового ввода для событий."""
    if 'awaiting_event' in context.user_data and context.user_data['awaiting_event']:
        user_id = str(update.message.from_user.id)
        text = update.message.text

        # Парсим данные события
        try:
            date_str = text.split('Дата:')[1].split('Событие:')[0].strip()
            description = text.split('Событие:')[1].strip()

            # Проверяем формат даты
            datetime.strptime(date_str, '%Y-%m-%d')
        except:
            await update.message.reply_text("Неверный формат. Пожалуйста, используйте:\n\nДата: ГГГГ-ММ-ДД\nСобытие: [описание]")
            return

        # Сохраняем событие
        calendar_data = load_data(CALENDAR_FILE)
        if user_id not in calendar_data:
            calendar_data[user_id] = []

        calendar_data[user_id].append({
            'date': date_str,
            'description': description,
            'created_at': str(datetime.now())
        })

        save_data(calendar_data, CALENDAR_FILE)
        await update.message.reply_text("Событие успешно добавлено!")
        context.user_data['awaiting_event'] = False

async def timer_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды таймера."""
    keyboard = [
        [InlineKeyboardButton("20 минут", callback_data='timer_20')],
        [InlineKeyboardButton("40 минут", callback_data='timer_40')],
        [InlineKeyboardButton("Отменить таймер", callback_data='cancel_timer')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Меню таймера:', reply_markup=reply_markup)

async def timer_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback'ов таймера."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == 'timer_20':
        if chat_id in active_timers:
            active_timers[chat_id].cancel()
        active_timers[chat_id] = PomodoroTimer(context, chat_id)
        active_timers[chat_id].start(20)
        await query.edit_message_text(text="20-минутный таймер запущен!")
    elif query.data == 'timer_40':
        if chat_id in active_timers:
            active_timers[chat_id].cancel()
        active_timers[chat_id] = PomodoroTimer(context, chat_id)
        active_timers[chat_id].start(40)
        await query.edit_message_text(text="40-минутный таймер запущен!")
    elif query.data == 'cancel_timer':
        if chat_id in active_timers:
            active_timers[chat_id].cancel()
            del active_timers[chat_id]
            await query.edit_message_text(text="Таймер отменен.")
        else:
            await query.edit_message_text(text="Нет активного таймера для отмены.")

async def links_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды полезных ссылок."""
    keyboard = [
        [InlineKeyboardButton("Добавить ссылку", callback_data='add_link')],
        [InlineKeyboardButton("Просмотреть ссылки", callback_data='view_links')],
        [InlineKeyboardButton("Удалить ссылку", callback_data='delete_link')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Меню полезных ссылок:', reply_markup=reply_markup)

async def links_callback(update: Update, context: CallbackContext) -> None:
    """Обработчик callback'ов ссылок."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    links_data = load_data(LINKS_FILE)

    if query.data == 'add_link':
        context.user_data['awaiting_link'] = True
        await query.edit_message_text(text="Отправьте мне детали ссылки в формате:\n\nНазвание: [имя]\nURL: [ссылка]\n\nПример:\nНазвание: Документация Python\nURL: https://docs.python.org")
    elif query.data == 'view_links':
        if user_id in links_data and links_data[user_id]:
            links_list = "\n\n".join([f"Название: {link['title']}\nURL: {link['url']}" for link in links_data[user_id]])
            await query.edit_message_text(text=f"Ваши сохраненные ссылки:\n\n{links_list}")
        else:
            await query.edit_message_text(text="У вас пока нет сохраненных ссылок.")
    elif query.data == 'delete_link':
        if user_id in links_data and links_data[user_id]:
            keyboard = [[InlineKeyboardButton(link['title'], callback_data=f"delete_link_{idx}")] 
                       for idx, link in enumerate(links_data[user_id])]
            keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel_delete_link')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Выберите ссылку для удаления:", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="У вас нет ссылок для удаления.")
    elif query.data.startswith('delete_link_'):
        idx = int(query.data.split('_')[2])
        del links_data[user_id][idx]
        save_data(links_data, LINKS_FILE)
        await query.edit_message_text(text="Ссылка успешно удалена!")
    elif query.data == 'cancel_delete_link':
        await query.edit_message_text(text="Удаление отменено.")

async def handle_link_text(update: Update, context: CallbackContext) -> None:
    """Обработчик текстового ввода для ссылок."""
    if 'awaiting_link' in context.user_data and context.user_data['awaiting_link']:
        user_id = str(update.message.from_user.id)
        text = update.message.text

        # Парсим данные ссылки
        try:
            title = text.split('Название:')[1].split('URL:')[0].strip()
            url = text.split('URL:')[1].strip()

            # Проверяем формат URL
            if not (url.startswith('http://') or url.startswith('https://')):
                raise ValueError("URL должен начинаться с http:// или https://")
        except Exception as e:
            await update.message.reply_text(f"Неверный формат или URL. Пожалуйста, используйте:\n\nНазвание: [имя]\nURL: [ссылка]\n\nОшибка: {str(e)}")
            return

        # Сохраняем ссылку
        links_data = load_data(LINKS_FILE)
        if user_id not in links_data:
            links_data[user_id] = []

        links_data[user_id].append({
            'title': title,
            'url': url,
            'created_at': str(datetime.now())
        })

        save_data(links_data, LINKS_FILE)
        await update.message.reply_text("Ссылка успешно добавлена!")
        context.user_data['awaiting_link'] = False

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Логирование ошибок."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text('Произошла ошибка. Пожалуйста, попробуйте снова.')

def main() -> None:
    """Запуск бота."""
    # Создаем Application и передаем токен бота
    application = ApplicationBuilder().token("7995131121:AAHmW6AteYi-jh4PfsUpDrNqilv2V1xHLvg").build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("calculator", calculator))
    application.add_handler(CommandHandler("cards", cards_command))
    application.add_handler(CommandHandler("translate", translate_command))
    application.add_handler(CommandHandler("calendar", calendar_command))
    application.add_handler(CommandHandler("timer", timer_command))
    application.add_handler(CommandHandler("links", links_command))

    # Регистрируем обработчики callback'ов
    application.add_handler(CallbackQueryHandler(calculator_callback, pattern='^[0-9+\\-*/.=C⌫]$'))
    application.add_handler(CallbackQueryHandler(cards_callback, pattern='^(add_card|view_cards|delete_card|delete_\\d+|cancel_delete)$'))
    application.add_handler(CallbackQueryHandler(translate_callback, pattern='^(ru_en|ru_de|ru_zh)$'))
    application.add_handler(CallbackQueryHandler(calendar_callback, pattern='^(add_event|view_events|delete_event|delete_event_\\d+|cancel_delete_event)$'))
    application.add_handler(CallbackQueryHandler(timer_callback, pattern='^(timer_20|timer_40|cancel_timer)$'))
    application.add_handler(CallbackQueryHandler(links_callback, pattern='^(add_link|view_links|delete_link|delete_link_\\d+|cancel_delete_link)$'))

    # Регистрируем обработчики текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_card_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link_text))

    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()