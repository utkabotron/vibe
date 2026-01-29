"""
Исправленная функция start_report для обработки ошибок
"""
import logging
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import ConversationState
from utils.bot_utils import clean_chat_history

logger = logging.getLogger(__name__)

async def fixed_start_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start creating a new report with improved error handling.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    # Проверяем, вызвана ли функция через callback_query или напрямую
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = update.effective_chat.id
    else:
        chat_id = update.effective_chat.id
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        # Вместо редактирования сообщения отправляем новое
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Очищаем историю сообщений перед началом нового отчета
    try:
        await clean_chat_history(update, context) # Удаляем сообщения, но сохраняем отчеты
    except Exception as e:
        logger.error(f"Error cleaning chat history: {e}")
    
    # Initialize a new report
    employee = context.user_data.get('employee', {})
    context.user_data['current_report'] = {
        'timestamp': datetime.now().isoformat(),
        'employee_id': employee.get('id', ''),
        'employee_name': employee.get('name', ''),
        'actions': []
    }
    
    # Load projects
    try:
        projects = await sheet_service.get_projects()
        if not projects:
            # Вместо редактирования сообщения отправляем новое
            await context.bot.send_message(
                chat_id=chat_id,
                text="Не найдено активных проектов. Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
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
        
        # Отправляем новое сообщение вместо редактирования
        message = await context.bot.send_message(
            chat_id=chat_id,
            text="Выберите проект:",
            reply_markup=reply_markup
        )
        
        # Отслеживаем сообщение для последующего удаления
        try:
            if 'messages_to_delete' not in context.user_data:
                context.user_data['messages_to_delete'] = []
            context.user_data['messages_to_delete'].append(message.message_id)
        except Exception as e:
            logger.error(f"Error tracking message: {e}")
            
        return ConversationState.CHOOSING_PROJECT
        
    except Exception as e:
        logger.error(f"Error loading projects: {e}")
        # Вместо редактирования сообщения отправляем новое
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка: не удалось загрузить список проектов. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
