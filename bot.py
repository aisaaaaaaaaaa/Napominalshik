from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application,
)
from apscheduler.schedulers.background import BackgroundScheduler
from db import init_db, add_task, get_tasks, delete_task
from datetime import datetime, timedelta
import asyncio
import re
import logging

logging.basicConfig(level=logging.INFO)
scheduler = BackgroundScheduler()
scheduler.start()

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-напоминальщик.\n\n"
        "Примеры:\n"
        "/add Покормить кошку в 18:00\n"
        "/add Позвонить брату 2025-07-13 14:00\n"
        "/add Прогулка завтра в 10:00\n"
        "/list – показать список задач\n"
        "/delete [ID] – удалить задачу"
    )

# Отправка уведомления
async def send_reminder(bot, user_id, text):
    try:
        await bot.send_message(chat_id=user_id, text=f"🔔 Напоминание: {text}")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# Планировка напоминания
def schedule_async_reminder(bot, user_id, text, time):
    scheduler.add_job(lambda: asyncio.run(send_reminder(bot, user_id, text)), 'date', run_date=time)

# Добавление напоминания
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    raw_text = ' '.join(context.args).replace('\xa0', ' ')

    if not raw_text:
        await update.message.reply_text("❗Напиши: /add [что напомнить] [время или дата]")
        return

    try:
        full_datetime = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})$', raw_text)
        tomorrow_time = re.search(r'завтра\s+в\s+(\d{1,2}:\d{2})$', raw_text, re.IGNORECASE)
        just_time = re.search(r'в\s+(\d{1,2}:\d{2})$', raw_text)

        if full_datetime:
            date_str, time_str = full_datetime.groups()
            remind_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            text = raw_text[:full_datetime.start()].strip()

        elif tomorrow_time:
            time_str = tomorrow_time.group(1)
            date = datetime.now().date() + timedelta(days=1)
            remind_time = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
            text = raw_text[:tomorrow_time.start()].strip()

        elif just_time:
            time_str = just_time.group(1)
            date = datetime.now().date()
            remind_time = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
            text = raw_text[:just_time.start()].strip()
        else:
            raise ValueError("Не распознано время")

        if remind_time <= datetime.now():
            await update.message.reply_text("❗Время уже прошло. Напоминание должно быть на будущее.")
            return

        task_id = add_task(user_id, text, remind_time)
        schedule_async_reminder(context.bot, user_id, text, remind_time)

        await update.message.reply_text(
            f"✅ Напоминание добавлено:\n📌 {text}\n🕒 {remind_time.strftime('%d.%m.%Y %H:%M')}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❗Не удалось распознать дату/время.\nПримеры:\n"
            "/add Погулять в 18:30\n"
            "/add Встреча 2025-07-15 10:00\n"
            "/add Подготовка к экзамену завтра в 12:00"
        )
        print(f"Ошибка в /add: {e}")

# Показать список задач
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)
    if not tasks:
        await update.message.reply_text("📭 У тебя нет активных напоминаний.")
    else:
        msg = "\n".join([
            f"🆔 {tid} — {t[0]} в {datetime.strptime(t[1], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')}"
            for tid, t in tasks.items()
        ])
        await update.message.reply_text(f"📋 Твои напоминания:\n{msg}")

# Удаление задачи
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Используй: /delete [ID]")
        return
    try:
        task_id = int(context.args[0])
        delete_task(task_id)
        await update.message.reply_text("🗑 Задача удалена.")
    except:
        await update.message.reply_text("❗ Ошибка. Укажи корректный ID.")

# Запуск бота
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token("7309...ТВОЙ_ТОКЕН...").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("delete", delete))

    print("Бот запущен...")
    app.run_polling()
