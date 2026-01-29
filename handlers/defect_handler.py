"""
Defect comment entry handler for Vibe Work Bot.
"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState,
    CALLBACK_BACK,
    CATEGORY_DEFECT
)
from utils.bot_utils import (
    create_category_keyboard,
    create_skip_keyboard,
    get_current_action
)

logger = logging.getLogger(__name__)


async def handle_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle defect category selection and prompt for comment.
    
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
        # Go back to category selection
        current_report = context.user_data.get('current_report', {})
        reply_markup = create_category_keyboard()
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n\n"
            "Выберите категорию:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_CATEGORY
    
    # Store defect category in current action
    current_action = get_current_action(context)
    current_action['category'] = CATEGORY_DEFECT
    current_action['subcategory'] = "Брак"
    current_action['subcategory_name'] = "Брак"
    current_action['type_name'] = "Брак"
    current_action['subcategory_id'] = ""
    current_action['quantity'] = ""
    current_action['unit'] = ""
    
    current_report = context.user_data.get('current_report', {})
    
    # Ask for comment
    keyboard = [
        [InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Проект: {current_report.get('project_name', '')}\n"
        f"Изделие: {current_report.get('product_name', '')}\n"
        f"Категория: Брак\n\n"
        "Введите описание брака:",
        reply_markup=reply_markup
    )
    return ConversationState.ENTERING_COMMENT
