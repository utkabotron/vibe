"""
Material type, material selection and quantity entry handlers for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState,
    CALLBACK_MATERIAL_TYPE_PREFIX,
    CALLBACK_MATERIAL_PREFIX,
    CALLBACK_BACK,
    CALLBACK_SKIP,
    CATEGORY_MATERIALS
)
from utils.bot_utils import (
    create_category_keyboard,
    create_material_types_keyboard,
    create_materials_keyboard,
    create_skip_keyboard,
    create_action_summary_keyboard,
    get_current_action,
    track_message,
    handle_stale_callback
)

logger = logging.getLogger(__name__)


async def select_material_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle material type selection.
    
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
    
    # Extract material_type_id from callback data
    if not query.data.startswith(CALLBACK_MATERIAL_TYPE_PREFIX):
        return await handle_stale_callback(update, context, "material_type_handler")
    
    material_type_id = query.data[len(CALLBACK_MATERIAL_TYPE_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get material type details
    material_types = await sheet_service.get_material_types()
    # Convert both type_id values to string to ensure consistent comparison
    selected_material_type = next((mt for mt in material_types if str(mt.get('type_id', '')) == str(material_type_id)), None)
    
    if not selected_material_type:
        logger.error(f"Material type not found: {material_type_id}")
        await query.edit_message_text(
            "Ошибка: выбранная группа материалов не найдена. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store material type info in context for later use
    context.user_data['selected_material_type'] = selected_material_type
    
    # Load materials for this type
    try:
        materials = await sheet_service.get_materials(material_type_id)
        if not materials:
            await query.edit_message_text(
                f"Для группы \"{selected_material_type.get('type_name', '')}\" не найдено материалов. "
                "Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Create keyboard with material buttons
        reply_markup = create_materials_keyboard(materials)
        
        current_report = context.user_data.get('current_report', {})
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Плита\n"
            f"Группа материалов: {selected_material_type.get('type_name', '')}\n\n"
            "Выберите материал:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_MATERIAL
        
    except Exception as e:
        logger.error(f"Error loading materials: {e}")
        await query.edit_message_text(
            "Ошибка: не удалось загрузить список материалов. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def select_material(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle material selection.
    
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
        # Go back to material type selection
        sheet_service = context.bot_data.get('sheet_service')
        material_types = await sheet_service.get_material_types()
        
        # Create keyboard with material type buttons
        reply_markup = create_material_types_keyboard(material_types)
        
        current_report = context.user_data.get('current_report', {})
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Плита\n\n"
            "Выберите группу материалов:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_MATERIAL_TYPE
    
    # Extract material_id from callback data
    if not query.data.startswith(CALLBACK_MATERIAL_PREFIX):
        return await handle_stale_callback(update, context, "material_handler")
    
    material_id = query.data[len(CALLBACK_MATERIAL_PREFIX):]
    
    sheet_service = context.bot_data.get('sheet_service')
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await query.edit_message_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Get material details
    selected_material_type = context.user_data.get('selected_material_type', {})
    material_type_id = selected_material_type.get('type_id')
    
    if not material_type_id:
        logger.error("Material type ID not found in user data")
        await query.edit_message_text(
            "Ошибка: данные о группе материалов не найдены. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    materials = await sheet_service.get_materials(material_type_id)
    # Convert both material_id values to string to ensure consistent comparison
    selected_material = next((m for m in materials if str(m.get('material_id', '')) == str(material_id)), None)
    
    if not selected_material:
        logger.error(f"Material not found: {material_id}")
        await query.edit_message_text(
            "Ошибка: выбранный материал не найден. Пожалуйста, начните снова."
        )
        return ConversationHandler.END
    
    # Store material info in current action
    current_action = get_current_action(context)
    current_action['category'] = CATEGORY_MATERIALS
    # Устанавливаем тип категории как Плита
    current_action['type_name'] = 'Плита'  # Set type_name to Плита
    # Сохраняем тип материала в subcategory
    selected_material_type = context.user_data.get('selected_material_type', {})
    current_action['subcategory'] = selected_material_type.get('type_name', '')  # Тип материала из MaterialTypes
    # Сохраняем название материала в subcategory_name
    current_action['subcategory_name'] = selected_material.get('material_name', '')  # Имя материала из Materials
    current_action['subcategory_id'] = material_id
    current_action['unit'] = selected_material.get('unit', '')
    
    current_report = context.user_data.get('current_report', {})
    
    # Создаем кнопки с стандартными объемами
    keyboard = []
    
    # Добавляем стандартные кнопки с шагом 0.5 до 6 для всех типов материалов
    # Получаем единицу измерения
    unit = current_action.get('unit', '')
    
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
    
    # Добавляем кнопки для пропуска и возврата
    keyboard.append([InlineKeyboardButton("Пропустить количество", callback_data="skip_quantity")])
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Устанавливаем флаг, что ожидаем ввод количества
    context.user_data['expecting_material_quantity'] = True
    
    await query.edit_message_text(
        f"Проект: {current_report.get('project_name', '')}\n"
        f"Изделие: {current_report.get('product_name', '')}\n"
        f"Категория: Материалы\n"
        f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
        f"Материал: {selected_material.get('material_name', '')}\n\n"
        f"Выберите из списка или введите количество (в {current_action.get('unit', '')}):",
        reply_markup=reply_markup
    )
    return ConversationState.ENTERING_MATERIAL_QUANTITY




async def enter_material_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle material quantity entry.
    
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
            # Go back to material selection
            selected_material_type = context.user_data.get('selected_material_type', {})
            material_type_id = selected_material_type.get('type_id')
            
            if not material_type_id:
                logger.error("Material type ID not found in user data")
                await query.edit_message_text(
                    "Ошибка: данные о группе материалов не найдены. Пожалуйста, начните снова."
                )
                return ConversationHandler.END
            
            sheet_service = context.bot_data.get('sheet_service')
            materials = await sheet_service.get_materials(material_type_id)
            
            # Create keyboard with material buttons
            reply_markup = create_materials_keyboard(materials)
            
            current_report = context.user_data.get('current_report', {})
            
            await query.edit_message_text(
                f"Проект: {current_report.get('project_name', '')}\n"
                f"Изделие: {current_report.get('product_name', '')}\n"
                f"Категория: Плита\n"
                f"Группа материалов: {selected_material_type.get('type_name', '')}\n\n"
                "Выберите материал:",
                reply_markup=reply_markup
            )
            return ConversationState.CHOOSING_MATERIAL
        
        # Проверяем, нажата ли кнопка Пропустить количество
        elif query.data == "skip_quantity":
            # Skip quantity and go to summary
            current_action = get_current_action(context)
            current_action['quantity'] = ""
            
            # Сбрасываем флаг ожидания ввода количества
            context.user_data['expecting_material_quantity'] = False
            
            current_report = context.user_data.get('current_report', {})
            selected_material_type = context.user_data.get('selected_material_type', {})
            
            # Показываем саммари и три кнопки
            reply_markup = create_action_summary_keyboard()
            
            await query.edit_message_text(
                f"Проект: {current_report.get('project_name', '')}\n"
                f"Изделие: {current_report.get('product_name', '')}\n"
                f"Категория: Плита\n"
                f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
                f"Материал: {current_action.get('subcategory_name', '')}\n\n"
                "Выберите действие:",
                reply_markup=reply_markup
            )
            return ConversationState.CONFIRM_ACTION
        
        # Проверяем, нажата ли кнопка с объемом
        elif query.data.startswith("volume:"):
            # Получаем выбранный объем
            try:
                volume = float(query.data.split(":")[1])
                
                # Сохраняем количество в current_action
                current_action = get_current_action(context)
                current_action['quantity'] = str(volume)
                
                # Сбрасываем флаг ожидания ввода количества
                context.user_data['expecting_material_quantity'] = False
                
                current_report = context.user_data.get('current_report', {})
                selected_material_type = context.user_data.get('selected_material_type', {})
                
                # Показываем саммари и три кнопки
                reply_markup = create_action_summary_keyboard()
                
                await query.edit_message_text(
                    f"Проект: {current_report.get('project_name', '')}\n"
                    f"Изделие: {current_report.get('product_name', '')}\n"
                    f"Категория: Плита\n"
                    f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
                    f"Материал: {current_action.get('subcategory_name', '')}\n"
                    f"Количество: {volume} {current_action.get('unit', '')}\n\n"
                    "Выберите действие:",
                    reply_markup=reply_markup
                )
                return ConversationState.CONFIRM_ACTION
                
            except (ValueError, IndexError) as e:
                logger.error(f"Error processing volume button: {e}")
                # В случае ошибки продолжаем ожидать ввод количества
                return ConversationState.ENTERING_MATERIAL_QUANTITY
    
    # Если нет колбэка, значит пользователь ввел количество вручную
    # If we're not expecting quantity input, ignore this message
    if not context.user_data.get('expecting_material_quantity'):
        return ConversationState.ENTERING_MATERIAL_QUANTITY
    
    # Handle quantity input
    quantity_str = update.message.text.strip()
    
    # Track the user's message for later deletion
    await track_message(update, context, update.message.message_id)
    
    try:
        # Replace comma with dot for decimal point
        quantity_str = quantity_str.replace(',', '.')
        quantity = float(quantity_str)
        
        # Store quantity in current action
        current_action = get_current_action(context)
        current_action['quantity'] = str(quantity)
        
        # Clear the flag
        context.user_data['expecting_material_quantity'] = False
        
        current_report = context.user_data.get('current_report', {})
        selected_material_type = context.user_data.get('selected_material_type', {})
        
        # Показываем саммари и три кнопки
        reply_markup = create_action_summary_keyboard()
        
        message = await update.message.reply_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n"
            f"Категория: Плита\n"
            f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
            f"Материал: {current_action.get('subcategory', '')}\n"
            f"Количество: {quantity} {current_action.get('unit', '')}\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        # Track the message for later deletion
        await track_message(update, context, message.message_id)
        return ConversationState.CONFIRM_ACTION
        
    except ValueError:
        error_message = await update.message.reply_text(
            "Неверный формат количества. Пожалуйста, введите число:"
        )
        
        # Track error message for later deletion
        await track_message(update, context, error_message.message_id)
        return ConversationState.ENTERING_MATERIAL_QUANTITY
