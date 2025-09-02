"""
Category selection handler for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState, 
    CALLBACK_CATEGORY_PREFIX, 
    CALLBACK_BACK,
    CATEGORY_LABOUR,
    CATEGORY_PAINT,
    CATEGORY_MATERIALS,
    CATEGORY_DEFECT
)
from utils.bot_utils import (
    create_products_keyboard,
    create_labour_types_keyboard,
    create_paint_types_keyboard,
    create_material_types_keyboard,
    get_current_action
)

logger = logging.getLogger(__name__)


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle category selection.
    
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
        # Go back to product selection
        sheet_service = context.bot_data.get('sheet_service')
        current_report = context.user_data.get('current_report', {})
        project_id = current_report.get('project_id')
        
        if not project_id:
            logger.error("Project ID not found in user data")
            await query.edit_message_text(
                "Ошибка: данные о проекте не найдены. Пожалуйста, начните снова."
            )
            return ConversationHandler.END
        
        products = await sheet_service.get_products(project_id)
        
        # Create keyboard with product buttons
        reply_markup = create_products_keyboard(products)
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n\n"
            "Выберите изделие:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_PRODUCT
    
    # Extract category from callback data
    if not query.data.startswith(CALLBACK_CATEGORY_PREFIX):
        logger.error(f"Invalid callback data: {query.data}")
        await query.edit_message_text("Ошибка: неверный формат данных. Пожалуйста, начните снова.")
        return ConversationHandler.END
    
    category = query.data[len(CALLBACK_CATEGORY_PREFIX):]
    
    # Initialize current action
    current_action = get_current_action(context)
    current_action['category'] = category
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    current_report = context.user_data.get('current_report', {})
    
    # Handle different categories
    if category == CATEGORY_LABOUR:
        # Load labour types
        labour_types = await sheet_service.get_labour_types()
        if not labour_types:
            await query.edit_message_text(
                "Не найдено типов работ. Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Create keyboard with labour type buttons
        reply_markup = create_labour_types_keyboard(labour_types)
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Работы\n\n"
            "Выберите вид работы:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_LABOUR_TYPE
        
    elif category == CATEGORY_PAINT:
        # Load paint material types
        paint_types = await sheet_service.get_paint_material_types()
        if not paint_types:
            await query.edit_message_text(
                "Не найдено типов материалов для малярки. Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Create keyboard with paint type buttons
        reply_markup = create_paint_types_keyboard(paint_types)
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: ЛКМ\n\n"
            "Выберите тип материала:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_PAINT_TYPE
        
    elif category == CATEGORY_MATERIALS:
        # Load material types
        material_types = await sheet_service.get_material_types()
        if not material_types:
            await query.edit_message_text(
                "Не найдено групп материалов. Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Create keyboard with material type buttons
        reply_markup = create_material_types_keyboard(material_types)
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Плита\n\n"
            "Выберите группу материалов:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_MATERIAL_TYPE
        
    elif category == CATEGORY_DEFECT:
        # For defects, go directly to comment entry
        keyboard = [
            [InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Брак\n\n"
            "Введите описание брака/дефекта:",
            reply_markup=reply_markup
        )
        return ConversationState.ENTERING_COMMENT
    
    else:
        logger.error(f"Unknown category: {category}")
        await query.edit_message_text(
            "Ошибка: неизвестная категория. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
