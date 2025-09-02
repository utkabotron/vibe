"""
Labour type and hours entry handlers for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState,
    CALLBACK_LABOUR_TYPE_PREFIX,
    CALLBACK_BACK,
    CALLBACK_SKIP,
    CATEGORY_LABOUR
)
from utils.bot_utils import (
    create_category_keyboard,
    create_skip_keyboard,
    create_action_summary_keyboard,
    get_current_action,
    parse_time_input,
    track_message
)

logger = logging.getLogger(__name__)


async def select_labour_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle labour type selection.
    
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
    
    # Extract labour_type_id from callback data
    if not query.data.startswith(CALLBACK_LABOUR_TYPE_PREFIX):
        logger.error(f"Invalid callback data: {query.data}")
        await query.edit_message_text("Ошибка: неверный формат данных. Пожалуйста, начните снова.")
        return ConversationHandler.END
    
    labour_type_id = query.data[len(CALLBACK_LABOUR_TYPE_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get labour type details
    labour_types = await sheet_service.get_labour_types()
    # Convert both work_id values to string to ensure consistent comparison
    # Поддержка как старых (work_id), так и новых (type_id) названий полей
    selected_labour_type = next((lt for lt in labour_types if 
                              str(lt.get('work_id', lt.get('type_id', ''))) == str(labour_type_id)), None)
    
    if not selected_labour_type:
        logger.error(f"Labour type not found: {labour_type_id}")
        await query.edit_message_text(
            "Ошибка: выбранный вид работы не найден. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store labour type info in current action
    current_action = get_current_action(context)
    # Сохраняем ID вида работы
    current_action['subcategory'] = selected_labour_type.get('work_id', selected_labour_type.get('type_id', ''))
    # Сохраняем название вида работы в subcategory_name - это будет отображаться в колонке name (J) в таблице
    current_action['subcategory_name'] = selected_labour_type.get('work_name', selected_labour_type.get('type_name', ''))
    # Устанавливаем тип категории как Работы
    current_action['type_name'] = 'Работы'  # Set type_name to Работы
    current_action['category'] = CATEGORY_LABOUR  # Set category to Работы
    current_action['unit'] = selected_labour_type.get('unit', 'ч')
    
    current_report = context.user_data.get('current_report', {})
    
    # Создаем кнопки со стандартными значениями времени
    keyboard = [
        # Первый ряд кнопок: 0:30, 1:00, 1:30, 2:00
        [
            InlineKeyboardButton("0:30", callback_data="time:0:30"),
            InlineKeyboardButton("1:00", callback_data="time:1:00"),
            InlineKeyboardButton("1:30", callback_data="time:1:30"),
            InlineKeyboardButton("2:00", callback_data="time:2:00")
        ],
        # Второй ряд кнопок: 2:30, 3:00, 3:30, 4:00
        [
            InlineKeyboardButton("2:30", callback_data="time:2:30"),
            InlineKeyboardButton("3:00", callback_data="time:3:00"),
            InlineKeyboardButton("3:30", callback_data="time:3:30"),
            InlineKeyboardButton("4:00", callback_data="time:4:00")
        ],
        # Третий ряд кнопок: 4:30, 5:00, 6:00, 7:00
        [
            InlineKeyboardButton("4:30", callback_data="time:4:30"),
            InlineKeyboardButton("5:00", callback_data="time:5:00"),
            InlineKeyboardButton("6:00", callback_data="time:6:00"),
            InlineKeyboardButton("7:00", callback_data="time:7:00")
        ],
        # Кнопка назад
        [InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Проект: {current_report.get('project_name', '')}\n"
        f"Изделие: {current_report.get('product_name', '')}\n"
        f"Категория: Работы\n"
        f"Вид работы: {selected_labour_type.get('work_name', selected_labour_type.get('type_name', ''))}\n\n"
        "Введите затраченное время в формате часы:минуты (например, 2:30) "
        "или как десятичное число (например, 2.5):",
        reply_markup=reply_markup
    )
    return ConversationState.ENTERING_HOURS


async def enter_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle hours entry.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    # Проверяем, является ли это нажатием на кнопку
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Проверяем, является ли это кнопкой "Назад"
        if query.data == CALLBACK_BACK:
            # Возвращаемся к выбору типа работы
            sheet_service = context.bot_data.get('sheet_service')
            labour_types = await sheet_service.get_labour_types()
            
            # Создаем клавиатуру с кнопками типов работ
            keyboard = []
            for labour_type in labour_types:
                work_id = labour_type.get('work_id', labour_type.get('type_id', ''))
                work_name = labour_type.get('work_name', labour_type.get('type_name', ''))
                if work_id and work_name:
                    keyboard.append([
                        InlineKeyboardButton(work_name, callback_data=f"labour_type:{work_id}")
                    ])
            
            # Добавляем кнопку назад
            keyboard.append([InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            current_report = context.user_data.get('current_report', {})
            
            await query.edit_message_text(
                f"Проект: {current_report.get('project_name', '')}\n"
                f"Изделие: {current_report.get('product_name', '')}\n"
                f"Категория: Работы\n\n"
                "Выберите вид работы:",
                reply_markup=reply_markup
            )
            return ConversationState.CHOOSING_LABOUR_TYPE
        
        # Проверяем, является ли это кнопкой выбора времени
        elif query.data.startswith("time:"):
            # Извлекаем выбранное время из callback_data
            time_str = query.data[5:]  # Удаляем префикс "time:"
            
            # Парсим время
            hours = parse_time_input(time_str)
            
            # Сохраняем введенное время в текущем действии
            current_action = get_current_action(context)
            current_action['quantity'] = hours
            
            # Переходим к экрану ввода комментария
            return await process_hours_input(update, context, hours)
    
    # Обработка ввода времени текстом
    time_str = update.message.text.strip()
    
    # Отслеживаем сообщение с введенным количеством часов для последующего удаления
    await track_message(update, context, update.message.message_id)
    
    hours = parse_time_input(time_str)
    
    if hours is None:
        # Отправляем сообщение об ошибке и отслеживаем его для последующего удаления
        error_message = await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате часы:минуты "
            "(например, 2:30) или как десятичное число (например, 2.5):"
        )
        
        # Отслеживаем сообщение об ошибке для последующего удаления
        await track_message(update, context, error_message.message_id)
        
        return ConversationState.ENTERING_HOURS
    
    # Если время введено корректно, переходим к обработке
    return await process_hours_input(update, context, hours)


async def process_hours_input(update: Update, context: ContextTypes.DEFAULT_TYPE, hours: float) -> int:
    """
    Process hours input and show action summary.
    
    Args:
        update: Update object
        context: CallbackContext
        hours: Parsed hours value
        
    Returns:
        Next conversation state
    """
    # Store hours in current action
    current_action = get_current_action(context)
    current_action['quantity'] = str(hours)
    current_action['unit'] = 'ч.'
    
    current_report = context.user_data.get('current_report', {})
    
    # Показываем саммари и три кнопки
    reply_markup = create_action_summary_keyboard()
    
    # Определяем, является ли update callback_query или message
    if update.callback_query:
        # Если это callback_query (нажатие на кнопку), редактируем текущее сообщение
        await update.callback_query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Работы\n"
            f"Вид работы: {current_action.get('subcategory_name', '')}\n"
            f"Время: {hours} ч.\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        # Если это message (ввод текста), отправляем новое сообщение
        message = await update.message.reply_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Работы\n"
            f"Вид работы: {current_action.get('subcategory_name', '')}\n"
            f"Время: {hours} ч.\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        # Отслеживаем сообщение для последующего удаления
        await track_message(update, context, message.message_id)
    
    return ConversationState.CONFIRM_ACTION
