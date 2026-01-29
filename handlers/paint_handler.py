"""
Paint material type, material selection and quantity entry handlers for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState,
    CALLBACK_PAINT_TYPE_PREFIX,
    CALLBACK_PAINT_MATERIAL_PREFIX,
    CALLBACK_BACK,
    CALLBACK_SKIP,
    CATEGORY_PAINT
)
from utils.bot_utils import (
    create_category_keyboard,
    create_paint_types_keyboard,
    create_paint_materials_keyboard,
    create_skip_keyboard,
    create_action_summary_keyboard,
    get_current_action,
    track_message,
    handle_stale_callback
)

logger = logging.getLogger(__name__)


async def select_paint_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle paint material type selection.
    
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
    
    # Extract paint_type_id from callback data
    if not query.data.startswith(CALLBACK_PAINT_TYPE_PREFIX):
        return await handle_stale_callback(update, context, "paint_type_handler")
    
    paint_type_id = query.data[len(CALLBACK_PAINT_TYPE_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get paint type details
    paint_types = await sheet_service.get_paint_material_types()
    # Convert both type_id values to string to ensure consistent comparison
    selected_paint_type = next((pt for pt in paint_types if str(pt.get('type_id', '')) == str(paint_type_id)), None)
    
    if not selected_paint_type:
        logger.error(f"Paint type not found: {paint_type_id}")
        await query.edit_message_text(
            "Ошибка: выбранный тип материала не найден. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store paint type info in context for later use
    context.user_data['selected_paint_type'] = selected_paint_type
    
    # Load paint materials for this type
    try:
        paint_materials = await sheet_service.get_paint_materials(paint_type_id)
        if not paint_materials:
            await query.edit_message_text(
                f"Для типа \"{selected_paint_type.get('type_name', '')}\" не найдено материалов. "
                "Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Create keyboard with paint material buttons
        reply_markup = create_paint_materials_keyboard(paint_materials)
        
        current_report = context.user_data.get('current_report', {})
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: ЛКМ\n"
            f"Тип материала: {selected_paint_type.get('type_name', '')}\n\n"
            "Выберите материал:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_PAINT_MATERIAL
        
    except Exception as e:
        logger.error(f"Error loading paint materials: {e}")
        await query.edit_message_text(
            "Ошибка: не удалось загрузить список материалов. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def select_paint_material(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle paint material selection.
    
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
        # Go back to paint type selection
        sheet_service = context.bot_data.get('sheet_service')
        paint_types = await sheet_service.get_paint_material_types()
        
        # Create keyboard with paint type buttons
        reply_markup = create_paint_types_keyboard(paint_types)
        
        current_report = context.user_data.get('current_report', {})
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: ЛКМ\n\n"
            "Выберите тип материала:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_PAINT_TYPE
    
    # Extract paint_material_id from callback data
    if not query.data.startswith(CALLBACK_PAINT_MATERIAL_PREFIX):
        return await handle_stale_callback(update, context, "paint_material_handler")
    
    paint_material_id = query.data[len(CALLBACK_PAINT_MATERIAL_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get paint material details
    selected_paint_type = context.user_data.get('selected_paint_type', {})
    paint_type_id = selected_paint_type.get('type_id')
    
    if not paint_type_id:
        logger.error("Paint type ID not found in user data")
        await query.edit_message_text(
            "Ошибка: данные о типе материала не найдены. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    paint_materials = await sheet_service.get_paint_materials(paint_type_id)
    # Convert both material_id values to string to ensure consistent comparison
    selected_paint_material = next((pm for pm in paint_materials if str(pm.get('material_id', '')) == str(paint_material_id)), None)
    
    if not selected_paint_material:
        logger.error(f"Paint material not found: {paint_material_id}")
        await query.edit_message_text(
            "Ошибка: выбранный материал не найден. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store paint material info in current action
    current_action = get_current_action(context)
    current_action['category'] = CATEGORY_PAINT
    # Устанавливаем тип категории как ЛКМ
    current_action['type_name'] = 'ЛКМ'  # Set type_name to ЛКМ
    # Сохраняем тип материала в subcategory
    selected_paint_type = context.user_data.get('selected_paint_type', {})
    current_action['subcategory'] = selected_paint_type.get('type_name', '')  # Тип материала из PaintMaterialTypes
    # Сохраняем название материала в subcategory_name
    current_action['subcategory_name'] = selected_paint_material.get('material_name', '')  # Имя материала из PaintMaterials
    current_action['subcategory_id'] = paint_material_id
    current_action['unit'] = selected_paint_material.get('unit', '')
    
    current_report = context.user_data.get('current_report', {})
    
    # Создаем кнопки с стандартными объемами для категории ЛКМ
    keyboard = []
    
    # Получаем единицу измерения
    unit = selected_paint_material.get('unit', '')
    
    # Добавляем стандартные кнопки с шагом 0.5 до 6 для всех типов материалов
    # Добавляем кнопки по 3 в ряд
    row = []
    for i in range(1, 13):  # От 0.5 до 6 с шагом 0.5
        volume = i * 0.5
        # Добавляем единицу измерения к кнопке, если она есть
        button_text = f"{volume}"
        if unit:
            button_text = f"{volume} {unit}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"volume:{volume}"))
        
        # После каждых 3 кнопок начинаем новый ряд
        if i % 3 == 0:
            keyboard.append(row)
            row = []
            
    # Добавляем оставшиеся кнопки, если есть
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Проект: {current_report.get('project_name', '')}\n"
        f"Изделие: {current_report.get('product_name', '')}\n"
        f"Категория: ЛКМ\n"
        f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
        f"Материал: {selected_paint_material.get('material_name', '')}\n\n"
        f"Выберите из списка или введите количество (в {selected_paint_material.get('unit', '')}):",
        reply_markup=reply_markup
    )
    return ConversationState.ENTERING_PAINT_QUANTITY


async def enter_paint_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle paint quantity entry.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    # Проверяем, есть ли колбэк от кнопки
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Проверяем, нажата ли кнопка Назад
        if query.data == CALLBACK_BACK:
            # Go back to paint material selection
            selected_paint_type = context.user_data.get('selected_paint_type', {})
            paint_type_id = selected_paint_type.get('type_id')
            
            if not paint_type_id:
                logger.error("Paint type ID not found in user data")
                await query.edit_message_text(
                    "Ошибка: данные о типе материала не найдены. Пожалуйста, начните снова."
                )
                return ConversationHandler.END
            
            sheet_service = context.bot_data.get('sheet_service')
            paint_materials = await sheet_service.get_paint_materials(paint_type_id)
            
            # Create keyboard with paint material buttons
            reply_markup = create_paint_materials_keyboard(paint_materials)
            
            current_report = context.user_data.get('current_report', {})
            
            await query.edit_message_text(
                f"Проект: {current_report.get('project_name', '')}\n"
                f"Изделие: {current_report.get('product_name', '')}\n"
                f"Категория: ЛКМ\n"
                f"Тип материала: {selected_paint_type.get('type_name', '')}\n\n"
                "Выберите материал:",
                reply_markup=reply_markup
            )
            return ConversationState.CHOOSING_PAINT_MATERIAL
        
        # Проверяем, нажата ли кнопка с объемом
        elif query.data.startswith("volume:"):
            # Получаем выбранный объем
            try:
                volume = float(query.data.split(":")[1])
                
                # Сохраняем количество в current_action
                current_action = get_current_action(context)
                current_action['quantity'] = str(volume)
                
                current_report = context.user_data.get('current_report', {})
                selected_paint_type = context.user_data.get('selected_paint_type', {})
                
                # Показываем саммари и три кнопки
                reply_markup = create_action_summary_keyboard()
                
                await query.edit_message_text(
                    f"Проект: {current_report.get('project_name', '')}\n"
                    f"Изделие: {current_report.get('product_name', '')}\n"
                    f"Категория: ЛКМ\n"
                    f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
                    f"Материал: {current_action.get('subcategory_name', '')}\n"
                    f"Количество: {volume} {current_action.get('unit', '')}\n\n"
                    "Выберите действие:",
                    reply_markup=reply_markup
                )
                return ConversationState.CONFIRM_ACTION
                
            except (ValueError, IndexError) as e:
                logger.error(f"Error processing volume button: {e}")
                # В случае ошибки продолжаем ожидать ввод количества
                return ConversationState.ENTERING_PAINT_QUANTITY
    
    # Если нет колбэка, значит пользователь ввел количество вручную
    # Handle quantity input
    quantity_str = update.message.text.strip()
    
    # Отслеживаем сообщение с введенным количеством краски для последующего удаления
    await track_message(update, context, update.message.message_id)
    
    try:
        # Replace comma with dot for decimal point
        quantity_str = quantity_str.replace(',', '.')
        quantity = float(quantity_str)
        
        # Store quantity in current action
        current_action = get_current_action(context)
        current_action['quantity'] = str(quantity)
        
        current_report = context.user_data.get('current_report', {})
        selected_paint_type = context.user_data.get('selected_paint_type', {})
        
        # Показываем саммари и три кнопки
        reply_markup = create_action_summary_keyboard()
        
        # Отправляем сообщение и отслеживаем его для последующего удаления
        message = await update.message.reply_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: ЛКМ\n"
            f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
            f"Материал: {current_action.get('subcategory', '')}\n"
            f"Количество: {quantity} {current_action.get('unit', '')}\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        # Отслеживаем сообщение для последующего удаления
        await track_message(update, context, message.message_id)
        return ConversationState.CONFIRM_ACTION
        
    except ValueError:
        # Отправляем сообщение об ошибке и отслеживаем его для последующего удаления
        error_message = await update.message.reply_text(
            "Неверный формат количества. Пожалуйста, введите число:"
        )
        
        # Отслеживаем сообщение об ошибке для последующего удаления
        await track_message(update, context, error_message.message_id)
        return ConversationState.ENTERING_PAINT_QUANTITY
