import datetime
import pytz
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ================= Configuration =================
BOT_TOKEN = "8982926059:AAFTcEstafP3_nOvfDD8IyrNxm79-YdGoMk"
GROUP_CHAT_ID = -1004307618131  # Target group chat ID
TIMEZONE = pytz.timezone("Asia/Phnom_Penh")

# Map of required members: {telegram_user_id: "Display Name or @username"}
REQUIRED_MEMBERS = {
    567936211: "@heanrithiya",
}

# In-memory tracker for users who submitted this week
submitted_members = set()
# =================================================


def is_pdf(document) -> bool:
    """Validate whether the uploaded document is a PDF."""
    if not document:
        return False
    if document.mime_type and document.mime_type.lower() == "application/pdf":
        return True
    if document.file_name and document.file_name.lower().endswith(".pdf"):
        return True
    return False


async def track_pdf_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detects uploaded PDF documents and logs the sender."""
    if not update.effective_chat or update.effective_chat.id != GROUP_CHAT_ID:
        return

    user = update.effective_user
    if not user or user.is_bot:
        return

    message = update.effective_message
    if not message or not message.document:
        return

    if is_pdf(message.document):
        submitted_members.add(user.id)
        file_name = message.document.file_name or "PDF Report"
        
        await message.reply_text(
            f"✅ Received <b>{file_name}</b> from {user.first_name}. Report logged!",
            parse_mode=ParseMode.HTML,
        )


async def check_and_remind(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks missing members and sends the reminder ping."""
    missing_user_ids = [uid for uid in REQUIRED_MEMBERS if uid not in submitted_members]

    if not missing_user_ids:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text="🎉 Great job everyone! All weekly PDF reports have been submitted.",
        )
        return

    # Format mentions
    mention_lines = []
    for uid in missing_user_ids:
        handle = REQUIRED_MEMBERS[uid]
        if handle.startswith("@"):
            mention_lines.append(handle)
        else:
            # Clickable mention fallback for users without a public @handle
            mention_lines.append(f'<a href="tg://user?id={uid}">{handle}</a>')

    mentions_str = " ".join(mention_lines)
    message = (
        f"⚠️ <b>Weekly Report Reminder</b>\n\n"
        f"Hi {mentions_str},\n\n"
        f"Our records show you have not uploaded your <b>PDF report</b> for this week yet. "
        f"Please upload your PDF file before the end of the day!"
    )

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=message,
        parse_mode=ParseMode.HTML,
    )


async def test_remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to manually trigger the reminder anytime: /testremind"""
    if not update.effective_chat or update.effective_chat.id != GROUP_CHAT_ID:
        return
    await check_and_remind(context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to inspect current week's submissions: /status"""
    if not update.effective_chat or update.effective_chat.id != GROUP_CHAT_ID:
        return

    submitted_list = [REQUIRED_MEMBERS[uid] for uid in submitted_members if uid in REQUIRED_MEMBERS]
    missing_list = [REQUIRED_MEMBERS[uid] for uid in REQUIRED_MEMBERS if uid not in submitted_members]

    sub_text = "\n".join([f"• {name}" for name in submitted_list]) if submitted_list else "<i>None</i>"
    mis_text = "\n".join([f"• {name}" for name in missing_list]) if missing_list else "<i>None</i>"

    status_msg = (
        f"📊 <b>Weekly Report Status</b>\n\n"
        f"<b>Submitted ({len(submitted_list)}):</b>\n{sub_text}\n\n"
        f"<b>Pending ({len(missing_list)}):</b>\n{mis_text}"
    )

    await update.effective_message.reply_text(status_msg, parse_mode=ParseMode.HTML)


async def reset_weekly_tracker(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears submission set every Monday at 00:00."""
    submitted_members.clear()
    print("PDF tracker reset for the new week.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 1. Listen for PDF uploads
    app.add_handler(
        MessageHandler(
            filters.Document.ALL & (~filters.COMMAND),
            track_pdf_reports,
        )
    )

    # 2. Manual testing commands
    app.add_handler(CommandHandler("testremind", test_remind_command))
    app.add_handler(CommandHandler("status", status_command))

    # 3. Scheduled Jobs
    job_queue = app.job_queue

    # Saturday at 17:00 (5:00 PM) reminder
    # In python-telegram-bot: 0 = Sun, 1 = Mon, ..., 6 = Sat
    job_queue.run_daily(
        check_and_remind,
        time=datetime.time(hour=17, minute=0, tzinfo=TIMEZONE),
        days=(6,),
    )

    # Monday at 00:00 tracker reset
    job_queue.run_daily(
        reset_weekly_tracker,
        time=datetime.time(hour=0, minute=0, tzinfo=TIMEZONE),
        days=(1,),
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
