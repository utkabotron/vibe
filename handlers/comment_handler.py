"""
Comment entry and action confirmation handlers for Vibe Work Bot.
"""
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.conversation_states import (
    ConversationState,
    CALLBACK_BACK,
    CALLBACK_SKIP,
    CALLBACK_CONFIRM,
    CALLBACK_ADD_MORE,
    CALLBACK_FINISH,
    CALLBACK_SEND_REPORT,
    CALLBACK_ADD_COMMENT,
    CATEGORY_LABOUR,
    CATEGORY_PAINT,
    CATEGORY_MATERIALS,
    CATEGORY_DEFECT
)
from utils.bot_utils import (
    get_current_action,
    get_current_report,
    add_action_to_report,
    clear_current_action,
    format_report_summary,
    create_yes_no_keyboard,
    create_skip_keyboard,
    create_action_summary_keyboard,
    create_confirm_keyboard,
    track_message,
    handle_stale_callback
)

logger = logging.getLogger(__name__)


async def enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle comment entry.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    # Check if this is a back button or skip button press
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == CALLBACK_BACK:
            # Go back to previous state based on category
            current_action = get_current_action(context)
            category = current_action.get('category')
            
            if category == CATEGORY_LABOUR:
                # Go back to hours entry
                current_report = context.user_data.get('current_report', {})
                
                keyboard = [
                    [InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Проект: {current_report.get('project_name', '')}\n"
                    f"Изделие: {current_report.get('product_name', '')}\n"
                    f"Категория: Работы\n"
                    f"Вид работы: {current_action.get('subcategory', '')}\n\n"
                    "Введите затраченное время в формате часы:минуты (например, 2:30) "
                    "или как десятичное число (например, 2.5):",
                    reply_markup=reply_markup
                )
                return ConversationState.ENTERING_HOURS
                
            elif category == CATEGORY_PAINT:
                # Go back to paint quantity entry
                current_report = context.user_data.get('current_report', {})
                selected_paint_type = context.user_data.get('selected_paint_type', {})
                
                keyboard = [
                    [InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Проект: {current_report.get('project_name', '')}\n"
                    f"Изделие: {current_report.get('product_name', '')}\n"
                    f"Категория: ЛКМ\n"
                    f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
                    f"Материал: {current_action.get('subcategory', '')}\n\n"
                    f"Введите количество (в {current_action.get('unit', '')}):",
                    reply_markup=reply_markup
                )
                return ConversationState.ENTERING_PAINT_QUANTITY
                
            elif category == CATEGORY_MATERIALS:
                # Go back to material quantity choice
                current_report = context.user_data.get('current_report', {})
                selected_material_type = context.user_data.get('selected_material_type', {})
                
                # Create keyboard with quantity/skip buttons
                keyboard = [
                    [InlineKeyboardButton("Указать количество", callback_data="enter_quantity")],
                    [InlineKeyboardButton("Пропустить количество", callback_data="skip_quantity")],
                    [InlineKeyboardButton("« Назад", callback_data=CALLBACK_BACK)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Проект: {current_report.get('project_name', '')}\n"
                    f"Изделие: {current_report.get('product_name', '')}\n"
                    f"Категория: Плита\n"
                    f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
                    f"Материал: {current_action.get('subcategory', '')}\n\n"
                    "Хотите указать количество материала?",
                    reply_markup=reply_markup
                )
                return ConversationState.ENTERING_MATERIAL_QUANTITY
                
            elif category == CATEGORY_DEFECT:
                # Go back to category selection
                current_report = context.user_data.get('current_report', {})
                
                from utils.bot_utils import create_category_keyboard
                reply_markup = create_category_keyboard()
                
                await query.edit_message_text(
                    f"Проект: {current_report.get('project_name', '')}\n"
                    f"Изделие: {current_report.get('product_name', '')}\n\n"
                    "Выберите категорию:",
                    reply_markup=reply_markup
                )
                return ConversationState.CHOOSING_CATEGORY
            
            else:
                logger.error(f"Unknown category: {category}")
                await query.edit_message_text(
                    "Ошибка: неизвестная категория. Пожалуйста, начните снова."
                )
                return ConversationHandler.END
        
        elif query.data == CALLBACK_SKIP:
            # Skip comment and go to confirm action
            current_action = get_current_action(context)
            current_action['comment'] = ""

            return await confirm_action(update, context)

        else:
            return await handle_stale_callback(update, context, "enter_comment")

    # Handle comment input - check if message exists
    if not update.message or not update.message.text:
        logger.warning("No message text in enter_comment")
        return ConversationState.ENTERING_COMMENT

    comment = update.message.text.strip()
    
    # Track the user's message for later deletion
    await track_message(update, context, update.message.message_id)
    
    # Check if comment is too long
    if len(comment) > 500:
        error_message = await update.message.reply_text(
            "Комментарий слишком длинный. Пожалуйста, введите комментарий не более 500 символов:"
        )
        # Track error message for later deletion
        await track_message(update, context, error_message.message_id)
        return ConversationState.ENTERING_COMMENT
    
    # Store comment in current action
    current_action = get_current_action(context)
    current_action['comment'] = comment
    
    # Go to confirm action
    reply_markup = create_confirm_keyboard()
    
    current_report = context.user_data.get('current_report', {})
    category = current_action.get('category')
    
    message_text = (
        f"Проект: {current_report.get('project_name', '')}\n"
        f"Изделие: {current_report.get('product_name', '')}\n"
    )
    
    if category == CATEGORY_LABOUR:
        message_text += (
            f"Категория: Работы\n"
            f"Вид работы: {current_action.get('subcategory', '')}\n"
            f"Время: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n"
        )
    elif category == CATEGORY_PAINT:
        selected_paint_type = context.user_data.get('selected_paint_type', {})
        message_text += (
            f"Категория: ЛКМ\n"
            f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
            f"Материал: {current_action.get('subcategory', '')}\n"
            f"Количество: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n"
        )
    elif category == CATEGORY_MATERIALS:
        selected_material_type = context.user_data.get('selected_material_type', {})
        message_text += (
            f"Категория: Плита\n"
            f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
            f"Материал: {current_action.get('subcategory', '')}\n"
        )
        if current_action.get('quantity'):
            message_text += f"Количество: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n"
    elif category == CATEGORY_DEFECT:
        message_text += f"Категория: Брак\n"
    
    message_text += f"Комментарий: {comment}\n\n"
    message_text += "Подтвердите действие:"
    
    message = await update.message.reply_text(message_text, reply_markup=reply_markup)
    # Track confirmation message for later deletion
    await track_message(update, context, message.message_id)
    return ConversationState.CONFIRM_ACTION


async def confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle action confirmation.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    # Handle back button
    if query and query.data == CALLBACK_BACK:
        await query.answer()
        
        # Go back to comment entry
        current_action = get_current_action(context)
        category = current_action.get('category', '')
        current_report = context.user_data.get('current_report', {})
        
        # Create skip keyboard
        reply_markup = create_skip_keyboard()
        
        # Prepare message based on category
        message = f"Проект: {current_report.get('project_name', '')}\n" \
                 f"Изделие: {current_report.get('product_name', '')}\n"
        
        if category == CATEGORY_LABOUR:
            message += (
                f"Категория: Работы\n"
                f"Вид работы: {current_action.get('subcategory_name', '')}\n"
                f"Время: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n\n"
            )
        elif category == CATEGORY_PAINT:
            selected_paint_type = context.user_data.get('selected_paint_type', {})
            message += (
                f"Категория: ЛКМ\n"
                f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
                f"Материал: {current_action.get('subcategory', '')}\n"
                f"Количество: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n\n"
            )
        elif category == CATEGORY_MATERIALS:
            selected_material_type = context.user_data.get('selected_material_type', {})
            message += (
                f"Категория: Плита\n"
                f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
                f"Материал: {current_action.get('subcategory', '')}\n"
            )
            if current_action.get('quantity'):
                message += f"Количество: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n"
            message += "\n"
        elif category == CATEGORY_DEFECT:
            message += f"Категория: Брак\n\n"
        
        message += "Введите комментарий (или нажмите «Пропустить»):"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        return ConversationState.ENTERING_COMMENT
    
    # Обработка кнопки "Отправить отчет"
    if query and query.data == CALLBACK_SEND_REPORT:
        await query.answer()
        
        # Добавляем действие в отчет без комментария
        current_action = get_current_action(context)
        current_action['comment'] = ""
        add_action_to_report(context)
        
        # Спрашиваем, хочет ли пользователь добавить еще одно действие
        reply_markup = create_yes_no_keyboard(CALLBACK_ADD_MORE, CALLBACK_FINISH)
        
        message = "Действие добавлено в отчёт. Хотите добавить ещё одно действие?"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        return ConversationState.ADD_ANOTHER_ACTION
    
    # Обработка кнопки "Добавить комментарий"
    if query and query.data == CALLBACK_ADD_COMMENT:
        await query.answer()
        
        # Переходим к вводу комментария
        current_action = get_current_action(context)
        category = current_action.get('category', '')
        current_report = context.user_data.get('current_report', {})
        
        # Create skip keyboard
        reply_markup = create_skip_keyboard()
        
        # Prepare message based on category
        message = f"Проект: {current_report.get('project_name', '')}\n" \
                 f"Изделие: {current_report.get('product_name', '')}\n"
        
        if category == CATEGORY_LABOUR:
            message += (
                f"Категория: Работы\n"
                f"Вид работы: {current_action.get('subcategory_name', '')}\n"
                f"Время: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n\n"
            )
        elif category == CATEGORY_PAINT:
            selected_paint_type = context.user_data.get('selected_paint_type', {})
            message += (
                f"Категория: ЛКМ\n"
                f"Тип материала: {selected_paint_type.get('type_name', '')}\n"
                f"Материал: {current_action.get('subcategory', '')}\n"
                f"Количество: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n\n"
            )
        elif category == CATEGORY_MATERIALS:
            selected_material_type = context.user_data.get('selected_material_type', {})
            message += (
                f"Категория: Плита\n"
                f"Группа материалов: {selected_material_type.get('type_name', '')}\n"
                f"Материал: {current_action.get('subcategory', '')}\n"
            )
            if current_action.get('quantity'):
                message += f"Количество: {current_action.get('quantity', '')} {current_action.get('unit', '')}\n"
            message += "\n"
        elif category == CATEGORY_DEFECT:
            message += f"Категория: Брак\n\n"
        
        message += "Введите комментарий (или нажмите «Пропустить»):"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        return ConversationState.ENTERING_COMMENT
    
    # Handle confirm button
    if not query or query.data == CALLBACK_CONFIRM:
        # Add action to report
        add_action_to_report(context)
        
        # Ask if user wants to add another action
        reply_markup = create_yes_no_keyboard(CALLBACK_ADD_MORE, CALLBACK_FINISH)
        
        message = "Действие добавлено в отчёт. Хотите добавить ещё одно действие?"
        
        if query:
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            # Это случай, когда мы приходим из skip_comment
            # В этом случае update.callback_query уже должен быть определен
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
            else:
                # Если callback_query отсутствует, отправляем новое сообщение
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=reply_markup
                )
        
        return ConversationState.ADD_ANOTHER_ACTION
    
    # Если мы дошли до этого места, значит получили неизвестный callback_data
    # Завершаем разговор и просим начать снова
    keyboard = [[InlineKeyboardButton("🔄 Начать заново", callback_data="restart_session")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.edit_message_text(
            "Создание отчёта отменено.",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Создание отчёта отменено.",
            reply_markup=reply_markup
        )
    return ConversationHandler.END


async def add_another_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle choice to add another action or finish report.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == CALLBACK_ADD_MORE:
        # Clear current action
        clear_current_action(context)
        
        # Go back to category selection
        current_report = context.user_data.get('current_report', {})
        
        from utils.bot_utils import create_category_keyboard
        reply_markup = create_category_keyboard()
        
        await query.edit_message_text(
            f"Проект: {current_report.get('project_name', '')}\n"
            f"Изделие: {current_report.get('product_name', '')}\n\n"
            "Выберите категорию для нового действия:",
            reply_markup=reply_markup
        )
        return ConversationState.CHOOSING_CATEGORY
    
    elif query.data == CALLBACK_FINISH:
        # Show report summary and ask for confirmation
        current_report = get_current_report(context)
        
        # Format report summary
        summary = format_report_summary(current_report)
        
        # Create confirm keyboard
        reply_markup = create_confirm_keyboard()
        
        # Отправляем новое сообщение и отслеживаем его для последующего удаления
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Итоговый отчёт:\n\n{summary}\n"
            "Подтвердите отправку отчёта:",
            reply_markup=reply_markup
        )
        
        # Отслеживаем сообщение для последующего удаления
        await track_message(update, context, message.message_id)
        return ConversationState.CONFIRM_REPORT
    
    else:
        return await handle_stale_callback(update, context, "add_another_action")
