"""
Product selection handler for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import ConversationState, CALLBACK_PRODUCT_PREFIX, CALLBACK_BACK
from utils.bot_utils import create_category_keyboard, track_message, clean_chat_history, handle_stale_callback

logger = logging.getLogger(__name__)


async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle product selection.
    
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
        # Go back to project selection
        sheet_service = context.bot_data.get('sheet_service')
        projects = await sheet_service.get_projects()
        
        # Create keyboard with project buttons
        keyboard = []
        for project in projects:
            project_id = project.get('project_id', '')
            project_name = project.get('project_name', '')
            if project_id and project_name:
                keyboard.append([
                    InlineKeyboardButton(project_name, callback_data=f"project:{project_id}")
                ])
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выберите проект:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_PROJECT
    
    # Extract product_id from callback data
    if not query.data.startswith(CALLBACK_PRODUCT_PREFIX):
        return await handle_stale_callback(update, context, "product_handler")
    
    product_id = query.data[len(CALLBACK_PRODUCT_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get product details
    current_report = context.user_data.get('current_report', {})
    project_id = current_report.get('project_id')
    
    if not project_id:
        logger.error("Project ID not found in user data")
        await query.edit_message_text(
            "Ошибка: данные о проекте не найдены. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    products = await sheet_service.get_products(project_id)
    # Convert both product_id values to string to ensure consistent comparison
    selected_product = next((p for p in products if str(p.get('product_id', '')) == str(product_id)), None)
    
    if not selected_product:
        logger.error(f"Product not found: {product_id}")
        await query.edit_message_text(
            "Ошибка: выбранное изделие не найдено. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store product info in current report
    current_report['product_id'] = product_id
    current_report['product_name'] = selected_product.get('product_name', '')
    context.user_data['current_report'] = current_report
    
    # Вместо удаления сообщения с запросом, просто редактируем его
    
    # Create keyboard with category buttons
    reply_markup = create_category_keyboard()
    
    # Редактируем существующее сообщение вместо отправки нового
    await query.edit_message_text(
        text=f"Проект: {current_report.get('project_name', '')}\n"
        f"Изделие: {selected_product.get('product_name', '')}\n\n"
        "Выберите категорию:",
        reply_markup=reply_markup
    )
    return ConversationState.CHOOSING_CATEGORY
