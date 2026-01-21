"""
Project selection handler for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import ConversationState, CALLBACK_PROJECT_PREFIX, CALLBACK_BACK
from utils.bot_utils import create_products_keyboard, track_message, clean_chat_history, handle_stale_callback

logger = logging.getLogger(__name__)


async def select_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle project selection.
    
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
        # Go back to start by ending the conversation
        # The user can restart with /start command
        await query.edit_message_text(
            "Создание отчёта отменено. Используйте /start для создания нового отчёта."
        )
        return ConversationHandler.END
    
    # Handle cancel button
    if query.data == "cancel":
        # Go back to start by ending the conversation
        # The user can restart with /start command
        await query.edit_message_text(
            "Создание отчёта отменено. Используйте /start для создания нового отчёта."
        )
        return ConversationHandler.END
    
    # Extract project_id from callback data
    if not query.data.startswith(CALLBACK_PROJECT_PREFIX):
        return await handle_stale_callback(update, context, "project_handler")
    
    project_id = query.data[len(CALLBACK_PROJECT_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        # Вместо редактирования сообщения отправляем новое
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get project details
    projects = await sheet_service.get_projects()
    # Convert project_id to string for comparison since callback data is always string
    selected_project = next((p for p in projects if str(p.get('project_id', '')) == str(project_id)), None)
    
    if not selected_project:
        logger.error(f"Project not found: {project_id}")
        await query.edit_message_text(
            "Ошибка: выбранный проект не найден. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store project info in current report
    current_report = context.user_data.get('current_report', {})
    current_report['project_id'] = project_id
    current_report['project_name'] = selected_project.get('project_name', '')
    context.user_data['current_report'] = current_report
    
    # Load products for this project
    try:
        products = await sheet_service.get_products(project_id)
        if not products:
            # Вместо редактирования сообщения отправляем новое
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Для проекта \"{selected_project.get('project_name', '')}\" не найдено изделий. "
                "Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Вместо удаления сообщения с запросом, просто редактируем его
        
        # Create keyboard with product buttons
        reply_markup = create_products_keyboard(products)
        
        # Редактируем существующее сообщение вместо отправки нового
        await query.edit_message_text(
            text=f"Проект: {selected_project.get('project_name', '')}\n\n"
            "Выберите изделие:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_PRODUCT
        
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        await query.edit_message_text(
            "Ошибка: не удалось загрузить список изделий. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
