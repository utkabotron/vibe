"""
Main entry point for Vibe Work Bot.

This module initializes the bot, sets up handlers, and starts the polling.
"""
# Force IPv4 connections - must be before any networking imports
# Some servers have IPv6 in DNS but can't reach IPv6 addresses, causing hangs
import socket
_original_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_ipv4_only(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET] or responses
socket.getaddrinfo = _getaddrinfo_ipv4_only

import asyncio
import logging

from gspread.exceptions import SpreadsheetNotFound, APIError

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from config.config import load_config, configure_logging
from services.sheet_service import SheetService
from handlers.conversation_states import ConversationState
from utils.bot_utils import format_report_summary, clear_current_report, clean_chat_history, track_message, track_bot_message
from handlers.start_handler import start, check_registration_code, register_name, confirm_registration, change_name
from fixed_start_report import fixed_start_report
from handlers.project_handler import select_project
from handlers.product_handler import select_product
from handlers.category_handler import select_category
from handlers.labour_handler import select_labour_type, enter_hours
from handlers.paint_handler import select_paint_type, select_paint_material, enter_paint_quantity
from handlers.materials_handler import (
    select_material_type, 
    select_material, 
    enter_material_quantity
)
from handlers.defect_handler import handle_defect
from handlers.comment_handler import enter_comment, confirm_action, add_another_action
from handlers.report_handler import confirm_report, new_report


logger = logging.getLogger(__name__)


async def cancel(update: Update, _) -> int:
    """Cancel and end the conversation."""
    user = update.effective_user
    logger.info(f"User {user.id} canceled the conversation.")
    
    if update.message:
        await update.message.reply_text(
            "Операция отменена. Используйте /start для начала новой."
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Операция отменена. Используйте /start для начала новой."
        )
    
    return ConversationHandler.END


async def error_handler(update, context):
    """Log errors caused by Updates and provide user feedback."""
    error = context.error
    logger.error(f"Update {update} caused error {error}")
    
    try:
        if update.effective_message:
            # Customize error message based on error type
            if isinstance(error, APIError):
                await update.effective_message.reply_text(
                    "Ошибка при обращении к Google Sheets API. Пожалуйста, попробуйте позже."
                )
            elif isinstance(error, SpreadsheetNotFound):
                await update.effective_message.reply_text(
                    "Не удалось найти таблицу Google Sheets. Пожалуйста, обратитесь к администратору."
                )
            elif isinstance(error, TimeoutError):
                await update.effective_message.reply_text(
                    "Превышено время ожидания ответа. Пожалуйста, проверьте подключение к интернету и попробуйте снова."
                )
            else:
                await update.effective_message.reply_text(
                    "Произошла ошибка. Пожалуйста, попробуйте снова или обратитесь к администратору."
                )
                
            # Suggest starting over
    except Exception as e:
        logger.error(f"Error in error handler: {e}")


async def track_sent_message(message, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track a sent message for later deletion.
    
    Args:
        message: The sent message object
        update: Update object
        context: CallbackContext
    """
    if message and hasattr(message, 'message_id'):
        await track_message(update, context, message.message_id)


async def post_init(app):
    """Initialize sheet service after application is ready."""
    config = app.bot_data.get('config')
    sheet_service = SheetService()

    # Initialize service and cache
    await sheet_service.initialize()

    # Store in bot_data for handlers to access
    app.bot_data['sheet_service'] = sheet_service

    # Start cache refresh task and store reference for cleanup
    refresh_task = asyncio.create_task(sheet_service._background_cache_refresh())
    app.bot_data['refresh_task'] = refresh_task

    logger.info("Sheet service initialized successfully")


async def post_shutdown(app):
    """Cleanup after application stops."""
    logger.info("Shutting down...")

    # Cancel cache refresh task
    refresh_task = app.bot_data.get('refresh_task')
    if refresh_task and not refresh_task.done():
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            logger.info("Cache refresh task cancelled")

    # Stop sheet service refresh task (backup)
    sheet_service = app.bot_data.get('sheet_service')
    if sheet_service:
        await sheet_service.stop_refresh_task()

    logger.info("Shutdown complete")


def main():
    """Start the bot."""
    # Load configuration
    config = load_config()

    # Configure logging
    configure_logging()

    # Уменьшаем уровень логирования для httpx, чтобы уменьшить количество сообщений
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Create the Application with post_init and post_shutdown callbacks
    application = (
        Application.builder()
        .token(config['telegram_token'])
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Store config in bot_data for handlers to access
    application.bot_data['config'] = config
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
        ],
        states={
            # Registration states
            ConversationState.ENTERING_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_registration_code),
            ],
            ConversationState.ENTERING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_name),
            ],
            ConversationState.REGISTRATION_CONFIRM: [
                CallbackQueryHandler(confirm_registration, pattern="^confirm_registration$"),
                CallbackQueryHandler(change_name, pattern="^change_name$"),
            ],
            ConversationState.CHOOSING_PROJECT: [
                CallbackQueryHandler(select_project),
            ],
            ConversationState.CHOOSING_PRODUCT: [
                CallbackQueryHandler(select_product),
            ],
            ConversationState.CHOOSING_CATEGORY: [
                CallbackQueryHandler(select_category),
            ],
            ConversationState.CHOOSING_LABOUR_TYPE: [
                CallbackQueryHandler(select_labour_type),
            ],
            ConversationState.ENTERING_HOURS: [
                CallbackQueryHandler(select_labour_type, pattern="^back$"),
                CallbackQueryHandler(enter_hours, pattern="^time:[0-9:]+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_hours),
            ],
            ConversationState.CHOOSING_PAINT_TYPE: [
                CallbackQueryHandler(select_paint_type),
            ],
            ConversationState.CHOOSING_PAINT_MATERIAL: [
                CallbackQueryHandler(select_paint_material),
            ],
            ConversationState.ENTERING_PAINT_QUANTITY: [
                CallbackQueryHandler(enter_paint_quantity, pattern="^(back|volume:.+)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_paint_quantity),
            ],
            ConversationState.CHOOSING_MATERIAL_TYPE: [
                CallbackQueryHandler(select_material_type),
            ],
            ConversationState.CHOOSING_MATERIAL: [
                CallbackQueryHandler(select_material),
            ],
            ConversationState.ENTERING_MATERIAL_QUANTITY: [
                CallbackQueryHandler(enter_material_quantity, pattern="^(volume:.+|back|skip_quantity)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_material_quantity),
            ],
            ConversationState.ENTERING_COMMENT: [
                CallbackQueryHandler(enter_comment),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_comment),
            ],
            ConversationState.CONFIRM_ACTION: [
                CallbackQueryHandler(confirm_action),
            ],
            ConversationState.ADD_ANOTHER_ACTION: [
                CallbackQueryHandler(add_another_action),
            ],
            ConversationState.CONFIRM_REPORT: [
                CallbackQueryHandler(confirm_report),
            ],
            # Убрали обработчик состояния REPORT_COMPLETED, так как убрали кнопку "Создать новый отчет"
            # Пользователь может использовать команду /start для создания нового отчета
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel$"),
        ],
        name="vibe_work_bot_conversation",
        persistent=False,
    )
    
    # Add conversation handler to application
    application.add_handler(conv_handler)

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the Bot - post_init and post_shutdown callbacks handle initialization and cleanup
    logger.info("Starting Vibe Work Bot...")
    application.run_polling()


if __name__ == '__main__':
    main()
