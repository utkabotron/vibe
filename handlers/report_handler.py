"""
Report confirmation and submission handlers for Vibe Work Bot.
"""
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState,
    CALLBACK_BACK,
    CALLBACK_CONFIRM,
    CALLBACK_NEW_REPORT
)
from utils.bot_utils import (
    get_current_report,
    clear_current_report,
    format_report_summary,
    clean_chat_history,
    track_message,
    mark_report_message,
    handle_stale_callback
)

logger = logging.getLogger(__name__)


async def confirm_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle report confirmation.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()
    
    # Handle back button
    if query.data == CALLBACK_BACK:
        # Go back to add another action
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить ещё действие", callback_data="add_more")],
            [InlineKeyboardButton("Завершить отчёт", callback_data="finish")]
        ])
        
        await query.edit_message_text(
            "Действие добавлено в отчёт. Хотите добавить ещё одно действие?",
            reply_markup=reply_markup
        )
        return ConversationState.ADD_ANOTHER_ACTION
    
    # Handle confirm button
    if query.data == CALLBACK_CONFIRM:
        # Get report data
        current_report = get_current_report(context)
        
        # Add timestamp
        current_report['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save report to Google Sheets
        sheet_service = context.bot_data.get('sheet_service')
        if not sheet_service:
            logger.error("Sheet service not initialized")
            await query.edit_message_text(
                "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
            )
            return ConversationHandler.END
        
        try:
            # Save report using the new save_report method
            success = await sheet_service.save_report(current_report)
            
            if not success:
                # Handle save failure
                logger.error("Failed to save report: save_report returned False")
                keyboard = [
                    [InlineKeyboardButton("Повторить", callback_data=CALLBACK_CONFIRM)],
                    [InlineKeyboardButton("Отмена", callback_data="cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "❌ Ошибка при сохранении отчёта. Пожалуйста, попробуйте ещё раз.",
                    reply_markup=reply_markup
                )
                return ConversationState.CONFIRM_REPORT
            
            # Убираем кнопку создания нового отчета, так как пользователь может использовать команду /start для создания нового отчета
            
            # Очищаем историю сообщений перед показом отчета
            await clean_chat_history(update, context)
            
            # Показываем карточку отчета
            report_summary = format_report_summary(current_report)
            report_card = await query.message.reply_text(
                f"📋 <b>Отчет отправлен</b>\n\n"
                f"{report_summary}",
                parse_mode='HTML'
            )
            
            # Отмечаем карточку отчета как сообщение, которое не нужно удалять
            await mark_report_message(update, context, report_card.message_id)
            
            # Убрали отправку сообщения с предложением создать новый отчет
            # Пользователь может использовать команду /start для создания нового отчета
            
            # Clear current report
            clear_current_report(context)
            
            # Не отслеживаем карточку отчета для удаления
            # await track_message(update, context, report_card.message_id)
            
            # Завершаем разговор, так как убрали кнопку "Создать новый отчет"
            # Пользователь может использовать команду /start для создания нового отчета
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            
            # Create retry button
            keyboard = [
                [InlineKeyboardButton("Повторить", callback_data=CALLBACK_CONFIRM)],
                [InlineKeyboardButton("Отмена", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ Ошибка при сохранении отчёта: {str(e)[:50]}...\nПожалуйста, попробуйте ещё раз.",
                reply_markup=reply_markup
            )
            return ConversationState.CONFIRM_REPORT
    
    return await handle_stale_callback(update, context, "confirm_report")


async def new_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle new report creation after completing a report.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == CALLBACK_NEW_REPORT:
        # Очищаем историю сообщений перед созданием нового отчета
        await clean_chat_history(update, context)
        
        # Start a new report
        from handlers.start_handler import start_report
        return await start_report(update, context)
    
    return await handle_stale_callback(update, context, "new_report")
