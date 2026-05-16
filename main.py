"""
Telegram-бот, улучшающий промпты для ИИ.
Использует Google Gemini (бесплатный API).
"""
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import google.generativeai as genai


# === Настройки из переменных окружения ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError(
        "Не заданы переменные окружения TELEGRAM_TOKEN и/или GEMINI_API_KEY"
    )

# === Настройка Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# === Инструкция для ИИ: как улучшать промпты ===
SYSTEM_PROMPT = """Ты — эксперт по созданию промптов (prompt engineer) для искусственного интеллекта.

Твоя задача: взять текст пользователя и переписать его так, чтобы ИИ (ChatGPT, Claude, Gemini и т.п.) выполнил задачу максимально эффективно и точно.

Правила улучшения:
1. Сохрани исходный смысл и намерение пользователя — ничего не выдумывай и не добавляй того, что пользователь не имел в виду.
2. Чётко обозначь роль для ИИ, если это уместно (например: «Ты опытный копирайтер...»).
3. Структурируй промпт: контекст → задача → требования к ответу → формат вывода.
4. Добавь конкретику там, где у пользователя расплывчатые формулировки.
5. Если задача сложная — попроси ИИ думать пошагово.
6. Укажи желаемый стиль, тон, длину ответа, если это можно угадать из контекста.
7. Пиши на том же языке, на котором написал пользователь.

ВАЖНО: верни ТОЛЬКО улучшенный промпт. Без вступления, без объяснений, без комментариев, без markdown-разметки вроде "###" или "**". Просто готовый текст промпта, который пользователь сразу скопирует и вставит в ИИ."""


# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# === Обработчики команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    text = (
        "👋 Привет! Я улучшаю промпты для ИИ.\n\n"
        "Просто отправь мне любой текст, вопрос или задачу — "
        "и я превращу её в чёткий, структурированный промпт, "
        "с которым ChatGPT, Claude, Gemini и другие нейросети "
        "справятся гораздо лучше.\n\n"
        "📝 Попробуй прямо сейчас — напиши что-нибудь!"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "Просто отправь мне свой запрос или задачу обычным сообщением. "
        "Я переделаю его в эффективный промпт для ИИ."
    )


async def improve_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основная логика: улучшение промпта"""
    user_text = update.message.text

    # Уведомляем, что обрабатываем
    thinking_msg = await update.message.reply_text("⏳ Улучшаю промпт...")

    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\nТекст пользователя:\n{user_text}"
        response = model.generate_content(full_prompt)
        improved = response.text.strip()

        # Удаляем сообщение "Улучшаю промпт..." и шлём результат
        await thinking_msg.delete()
        await update.message.reply_text(
            f"✨ Готово! Вот улучшенный промпт:\n\n{improved}"
        )
    except Exception as e:
        logger.error("Ошибка при обращении к Gemini: %s", e)
        await thinking_msg.edit_text(
            f"❌ Произошла ошибка: {e}\n\nПопробуй ещё раз через минуту."
        )


# === Мини HTTP-сервер для UptimeRobot ===
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        return  # отключаем шумные логи


def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), PingHandler)
    logger.info("HTTP-сервер запущен на порту %s", PORT)
    server.serve_forever()


# === Главная функция ===
def main():
    # Запускаем HTTP-сервер в отдельном потоке (для пингов UptimeRobot)
    threading.Thread(target=run_http_server, daemon=True).start()

    # Запускаем Telegram-бота
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, improve_prompt))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
