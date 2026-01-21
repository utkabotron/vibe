"""
Utility functions for Vibe Work Bot.
"""
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.conversation_states import (
    CALLBACK_BACK,
    CALLBACK_PROJECT_PREFIX,
    CALLBACK_PRODUCT_PREFIX,
    CALLBACK_CATEGORY_PREFIX,
    CALLBACK_LABOUR_TYPE_PREFIX,
    CALLBACK_PAINT_TYPE_PREFIX,
    CALLBACK_PAINT_MATERIAL_PREFIX,
    CALLBACK_MATERIAL_TYPE_PREFIX,
    CALLBACK_MATERIAL_PREFIX,
    CALLBACK_SEND_REPORT,
    CALLBACK_ADD_COMMENT,
    CALLBACK_CONFIRM,
)

logger = logging.getLogger(__name__)


def build_menu(
    buttons: List[InlineKeyboardButton],
    n_cols: int = 1,
    header_buttons: Optional[List[InlineKeyboardButton]] = None,
    footer_buttons: Optional[List[InlineKeyboardButton]] = None
) -> List[List[InlineKeyboardButton]]:
    """
    Build a menu with a grid of buttons.
    
    Args:
        buttons: List of buttons to include in the menu
        n_cols: Number of columns in the grid
        header_buttons: Optional buttons to display in the header row
        footer_buttons: Optional buttons to display in the footer row
        
    Returns:
        List of button rows for an InlineKeyboardMarkup
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def create_back_button() -> InlineKeyboardButton:
    """Create a back button."""
    return InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)


def create_projects_keyboard(projects: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with project buttons.
    
    Args:
        projects: List of project dictionaries
        
    Returns:
        InlineKeyboardMarkup with project buttons
    """
    buttons = []
    for project in projects:
        project_id = project.get('project_id', '')
        project_name = project.get('project_name', '')
        if project_id and project_name:
            buttons.append(
                InlineKeyboardButton(
                    project_name,
                    callback_data=f"{CALLBACK_PROJECT_PREFIX}{project_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_products_keyboard(products: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with product buttons.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        InlineKeyboardMarkup with product buttons
    """
    buttons = []
    for product in products:
        product_id = product.get('product_id', '')
        product_name = product.get('product_name', '')
        if product_id and product_name:
            buttons.append(
                InlineKeyboardButton(
                    product_name,
                    callback_data=f"{CALLBACK_PRODUCT_PREFIX}{product_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_category_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with category buttons.
    
    Returns:
        InlineKeyboardMarkup with category buttons
    """
    buttons = [
        InlineKeyboardButton("Работы", callback_data=f"{CALLBACK_CATEGORY_PREFIX}Работы"),
        InlineKeyboardButton("ЛКМ", callback_data=f"{CALLBACK_CATEGORY_PREFIX}ЛКМ"),
        InlineKeyboardButton("Плита", callback_data=f"{CALLBACK_CATEGORY_PREFIX}Плита"),
        InlineKeyboardButton("Брак", callback_data=f"{CALLBACK_CATEGORY_PREFIX}Брак"),
    ]
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_labour_types_keyboard(labour_types: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with labour type buttons.
    
    Args:
        labour_types: List of labour type dictionaries
        
    Returns:
        InlineKeyboardMarkup with labour type buttons
    """
    buttons = []
    for labour_type in labour_types:
        # Поддержка как старых (work_id, work_name), так и новых (type_id, type_name) названий полей
        work_id = labour_type.get('work_id', labour_type.get('type_id', ''))
        work_name = labour_type.get('work_name', labour_type.get('type_name', ''))
        if work_id and work_name:
            buttons.append(
                InlineKeyboardButton(
                    work_name,
                    callback_data=f"{CALLBACK_LABOUR_TYPE_PREFIX}{work_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_paint_types_keyboard(paint_types: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with paint material type buttons.
    
    Args:
        paint_types: List of paint material type dictionaries
        
    Returns:
        InlineKeyboardMarkup with paint material type buttons
    """
    buttons = []
    for paint_type in paint_types:
        type_id = paint_type.get('type_id', '')
        type_name = paint_type.get('type_name', '')
        if type_id and type_name:
            buttons.append(
                InlineKeyboardButton(
                    type_name,
                    callback_data=f"{CALLBACK_PAINT_TYPE_PREFIX}{type_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_paint_materials_keyboard(paint_materials: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with paint material buttons.
    
    Args:
        paint_materials: List of paint material dictionaries
        
    Returns:
        InlineKeyboardMarkup with paint material buttons
    """
    buttons = []
    for material in paint_materials:
        material_id = material.get('material_id', '')
        material_name = material.get('material_name', '')
        if material_id and material_name:
            buttons.append(
                InlineKeyboardButton(
                    material_name,
                    callback_data=f"{CALLBACK_PAINT_MATERIAL_PREFIX}{material_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_material_types_keyboard(material_types: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with material type buttons.
    
    Args:
        material_types: List of material type dictionaries
        
    Returns:
        InlineKeyboardMarkup with material type buttons
    """
    buttons = []
    for material_type in material_types:
        type_id = material_type.get('type_id', '')
        type_name = material_type.get('type_name', '')
        if type_id and type_name:
            buttons.append(
                InlineKeyboardButton(
                    type_name,
                    callback_data=f"{CALLBACK_MATERIAL_TYPE_PREFIX}{type_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_materials_keyboard(materials: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Create a keyboard with material buttons.
    
    Args:
        materials: List of material dictionaries
        
    Returns:
        InlineKeyboardMarkup with material buttons
    """
    buttons = []
    for material in materials:
        material_id = material.get('material_id', '')
        material_name = material.get('material_name', '')
        if material_id and material_name:
            buttons.append(
                InlineKeyboardButton(
                    material_name,
                    callback_data=f"{CALLBACK_MATERIAL_PREFIX}{material_id}"
                )
            )
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """
    Create a keyboard with Yes/No buttons.
    
    Args:
        yes_data: Callback data for Yes button
        no_data: Callback data for No button
        
    Returns:
        InlineKeyboardMarkup with Yes/No buttons
    """
    buttons = [
        InlineKeyboardButton("Да", callback_data=yes_data),
        InlineKeyboardButton("Нет", callback_data=no_data),
    ]
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=2, footer_buttons=[create_back_button()]))


def create_skip_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with a Skip button.
    
    Returns:
        InlineKeyboardMarkup with Skip button
    """
    buttons = [
        InlineKeyboardButton("Пропустить", callback_data="skip"),
    ]
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def create_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with Confirm and Back buttons.
    
    Returns:
        InlineKeyboardMarkup with Confirm and Back buttons
    """
    buttons = [
        InlineKeyboardButton("Отправить", callback_data="confirm"),
    ]
    
    # Add back button in the footer
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1, footer_buttons=[create_back_button()]))


def parse_time_input(time_str: str) -> Optional[float]:
    """
    Parse time input in format hours:minutes or decimal hours.
    
    Args:
        time_str: Time string
        
    Returns:
        Hours as float or None if invalid format
    """
    # Try to parse as hours:minutes
    if ':' in time_str:
        try:
            hours, minutes = time_str.split(':', 1)
            return float(hours) + float(minutes) / 60
        except (ValueError, ZeroDivisionError):
            return None
    
    # Try to parse as decimal hours
    try:
        # Replace comma with dot for decimal point
        time_str = time_str.replace(',', '.')
        return float(time_str)
    except ValueError:
        return None


def format_time_as_hhmm(hours_float: Union[str, float]) -> str:
    """
    Format hours as HH:MM string.
    
    Args:
        hours_float: Hours as float or string representing float
        
    Returns:
        Formatted time string in HH:MM format
    """
    try:
        # Convert to float if it's a string
        if isinstance(hours_float, str):
            hours_float = float(hours_float.replace(',', '.'))
            
        # Calculate hours and minutes
        hours = int(hours_float)
        minutes = int((hours_float - hours) * 60)
        
        # Format as HH:MM
        return f"{hours}:{minutes:02d}"
    except (ValueError, TypeError):
        # Return original value if conversion fails
        return str(hours_float)


def format_report_summary(report_data: Dict[str, Any]) -> str:
    """
    Format report data as a summary string.
    
    Args:
        report_data: Report data dictionary
        
    Returns:
        Formatted summary string
    """
    timestamp = datetime.fromisoformat(report_data['timestamp'])
    formatted_date = timestamp.strftime("%d.%m.%Y")
    formatted_time = timestamp.strftime("%H:%M")
    
    summary = (
        f"📊 Отчёт – {formatted_date} {formatted_time}\n"
        f"👤 Сотрудник: {report_data['employee_name']}\n"
        f"🏗️ Проект: {report_data['project_name']}\n"
        f"📦 Изделие: {report_data['product_name']}\n"
        f"📋 Выполненные действия:\n"
    )
    
    for action in report_data['actions']:
        category = action['category']
        # Используем subcategory_name вместо subcategory для отображения имени
        subcategory = action.get('subcategory_name', action.get('subcategory', ''))
        quantity = action.get('quantity', '')
        unit = action.get('unit', '')
        comment = action.get('comment', '')
        
        if category == 'Работы':
            # Форматируем время в формате ЧЧ:ММ
            formatted_time = format_time_as_hhmm(quantity)
            summary += f"  • Работы: {subcategory}, {formatted_time} ч."
        elif category == 'ЛКМ':
            summary += f"  • ЛКМ: {subcategory}, {quantity} {unit}"
        elif category == 'Плита':
            if quantity:
                summary += f"  • Плита: {subcategory}, {quantity} {unit}"
            else:
                summary += f"  • Плита: {subcategory}"
        elif category == 'Брак':
            summary += f"  • Брак"
        
        if comment:
            summary += f" (Комментарий: {comment})"
        
        summary += "\n"
    
    return summary


def get_current_report(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    """
    Get the current report from user data.
    
    Args:
        context: CallbackContext
        
    Returns:
        Current report data
    """
    if 'current_report' not in context.user_data:
        context.user_data['current_report'] = {
            'actions': []
        }
    
    return context.user_data['current_report']


def clear_current_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clear the current report data.
    
    Args:
        context: CallbackContext
    """
    if 'current_report' in context.user_data:
        del context.user_data['current_report']
    
    if 'current_action' in context.user_data:
        del context.user_data['current_action']


def get_current_action(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    """
    Get the current action from user data.
    
    Args:
        context: CallbackContext
        
    Returns:
        Current action data
    """
    if 'current_action' not in context.user_data:
        context.user_data['current_action'] = {}
    
    return context.user_data['current_action']


def clear_current_action(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clear the current action data.
    
    Args:
        context: CallbackContext
    """
    if 'current_action' in context.user_data:
        del context.user_data['current_action']


def add_action_to_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Add the current action to the report.
    
    Args:
        context: CallbackContext
    """
    current_report = get_current_report(context)
    current_action = get_current_action(context)
    
    if current_action:
        current_report['actions'].append(current_action.copy())
        clear_current_action(context)


def create_action_summary_keyboard() -> InlineKeyboardMarkup:
    """
    Create a keyboard with three buttons: Send Report, Add Comment, and Back.
    
    Returns:
        InlineKeyboardMarkup with three buttons
    """
    buttons = [
        InlineKeyboardButton("Отправить отчет", callback_data=CALLBACK_SEND_REPORT),
        InlineKeyboardButton("Добавить комментарий", callback_data=CALLBACK_ADD_COMMENT),
        InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)
    ]
    
    return InlineKeyboardMarkup(build_menu(buttons, n_cols=1))


async def clean_chat_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Удаляет старые сообщения в чате для поддержания чистого интерфейса.
    Удаляет сообщения с командой /start и кнопкой "Создать отчет", но сохраняет отчеты.
    
    Args:
        update: Update object
        context: CallbackContext
    """
    try:
        # Получаем ID текущего сообщения
        chat_id = update.effective_chat.id
        
        # Получаем список ID сообщений для удаления из контекста пользователя
        message_ids_to_delete = context.user_data.get('message_ids_to_delete', [])
        
        # Получаем список ID сообщений с отчетами, которые не нужно удалять
        report_message_ids = context.user_data.get('report_message_ids', [])
        
        # Удаляем только отслеживаемые сообщения, кроме сообщений с отчетами
        for msg_id in message_ids_to_delete.copy():  # Используем copy() чтобы избежать ошибок при изменении списка
            # Пропускаем сообщения с отчетами
            if msg_id in report_message_ids:
                continue
                
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
        
        # Очищаем список ID сообщений для удаления, но сохраняем список отчетов
        context.user_data['message_ids_to_delete'] = []
        
        # Не удаляем сообщения автоматически, только те, которые отслеживаются
        # Это позволит сохранить отчеты в истории чата
        # Удаляем автоматическое удаление сообщений
        # if update.effective_message and update.effective_message.message_id:
        #     current_message_id = update.effective_message.message_id
        #     # Пытаемся удалить только последние 5 сообщений
        #     for i in range(1, 6):  # Уменьшаем с 10 до 5
        #         msg_id = current_message_id - i
        #         if msg_id > 0 and msg_id not in report_message_ids:
        #             try:
        #                 await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        #             except Exception:
        #                 # Игнорируем ошибки удаления
        #                 pass
        
    except Exception as e:
        logger.error(f"Ошибка при очистке истории чата: {e}")


async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None) -> None:
    """
    Добавляет ID сообщения в список для последующего удаления.
    
    Args:
        update: Update object
        context: CallbackContext
        message_id: ID сообщения для отслеживания (если None, используется ID текущего сообщения)
    """
    if not message_id:
        message_id = update.effective_message.message_id
    
    # Инициализируем список, если его нет
    if 'message_ids_to_delete' not in context.user_data:
        context.user_data['message_ids_to_delete'] = []
    
    # Добавляем ID сообщения в список
    context.user_data['message_ids_to_delete'].append(message_id)


async def mark_report_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None) -> None:
    """
    Отмечает сообщение с отчетом, чтобы оно не удалялось при очистке истории.
    
    Args:
        update: Update object
        context: CallbackContext
        message_id: ID сообщения с отчетом
    """
    if not message_id:
        message_id = update.effective_message.message_id
    
    # Инициализируем список сообщений с отчетами, если его нет
    if 'report_message_ids' not in context.user_data:
        context.user_data['report_message_ids'] = []
    
    # Добавляем ID сообщения в список отчетов
    context.user_data['report_message_ids'].append(message_id)
    
    # Удаляем из списка сообщений для удаления, если он там есть
    if 'message_ids_to_delete' in context.user_data and message_id in context.user_data['message_ids_to_delete']:
        context.user_data['message_ids_to_delete'].remove(message_id)


async def track_bot_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    """
    Автоматически отслеживает сообщения бота для последующего удаления.

    Args:
        update: Update object
        context: CallbackContext
        message_id: ID сообщения бота
    """
    # Инициализируем список, если его нет
    if 'message_ids_to_delete' not in context.user_data:
        context.user_data['message_ids_to_delete'] = []

    # Проверяем, что сообщение не является отчетом
    if 'report_message_ids' not in context.user_data or message_id not in context.user_data['report_message_ids']:
        # Добавляем ID сообщения в список для удаления
        if message_id not in context.user_data['message_ids_to_delete']:
            context.user_data['message_ids_to_delete'].append(message_id)


async def handle_stale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, handler_name: str) -> int:
    """
    Обрабатывает нажатие на устаревшую кнопку.
    Удаляет сообщение с устаревшими кнопками и предлагает начать заново.

    Args:
        update: Update object
        context: CallbackContext
        handler_name: Имя хэндлера для логирования

    Returns:
        ConversationHandler.END
    """
    from telegram.ext import ConversationHandler

    query = update.callback_query
    logger.warning(f"Stale callback data in {handler_name}: {query.data}")

    try:
        # Удаляем сообщение с устаревшими кнопками
        await query.message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить устаревшее сообщение: {e}")

    # Отправляем сообщение с предложением начать заново
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠️ Эта сессия устарела.\n\nНажмите /start чтобы начать новый отчёт."
    )

    # Очищаем данные пользователя
    context.user_data.clear()

    return ConversationHandler.END
