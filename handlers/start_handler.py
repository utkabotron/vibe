"""
Start handler for Vibe Work Bot.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from fixed_start_report import fixed_start_report

from handlers.conversation_states import ConversationState
from services.sheet_service import SheetService
from utils.bot_utils import format_report_summary, clear_current_report, clean_chat_history, track_message

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start the conversation and check if user is authorized.
    If user is not registered, start registration process.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    # Отслеживаем команду /start для последующего удаления
    if update.message and update.message.text and update.message.text.startswith('/start'):
        await track_message(update, context, update.message.message_id)
    
    # Очищаем историю сообщений при запуске бота, но сохраняем отчеты
    await clean_chat_history(update, context)
    
    user = update.effective_user
    sheet_service = context.bot_data.get('sheet_service')
    
    if not sheet_service:
        logger.error("Sheet service not initialized")
        await update.message.reply_text(
            "Ошибка: сервис Google Sheets не инициализирован. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    # Check if user is authorized by looking up their Telegram ID in the employees list
    employee = await sheet_service.get_employee(user.id)
    
    # Если пользователь зарегистрирован и активен, сразу показываем выбор проектов
    if employee and employee.get('active') == 'TRUE':
        context.user_data['employee'] = employee
        # Очищаем историю сообщений перед началом нового отчета
        await clean_chat_history(update, context)
        
        # Инициализируем новый отчет
        context.user_data['current_report'] = {
            'timestamp': datetime.now().isoformat(),
            'employee_id': employee.get('id', ''),
            'employee_name': employee.get('name', ''),
            'actions': []
        }
        
        # Загружаем список проектов
        try:
            projects = await sheet_service.get_projects()
            if not projects:
                await update.message.reply_text(
                    "Не найдено активных проектов. Пожалуйста, обратитесь к администратору."
                )
                return ConversationHandler.END
            
            # Создаем клавиатуру с кнопками проектов
            keyboard = []
            for project in projects:
                project_id = project.get('project_id', '')
                project_name = project.get('project_name', '')
                if project_id and project_name:
                    keyboard.append([
                        InlineKeyboardButton(project_name, callback_data=f"project:{project_id}")
                    ])
            
            # Добавляем кнопку отмены
            keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем приветствие и список проектов
            welcome_text = f"Здравствуйте, {employee.get('name', 'сотрудник')}!\n\nВыберите проект:"
            message = await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            
            # Отслеживаем сообщение для последующего удаления
            await track_message(update, context, message.message_id)
            return ConversationState.CHOOSING_PROJECT
            
        except Exception as e:
            logger.error(f"Error loading projects: {e}")
            await update.message.reply_text(
                "Ошибка: не удалось загрузить список проектов. Пожалуйста, попробуйте позже."
            )
            return ConversationHandler.END
        
    if not employee:
        # Проверяем, есть ли пользователь в системе, но с неактивным статусом
        # Для этого получаем всех сотрудников и проверяем по ID без учета активности
        all_employees = sheet_service._cache['employees']
        inactive_employee = None
        for emp_id, emp_data in all_employees.items():
            if str(emp_id) == str(user.id) or str(emp_data.get('id', '')) == str(user.id):
                if emp_data.get('active', '').upper() == 'FALSE':
                    inactive_employee = emp_data
                    break
        
        if inactive_employee:
            # Пользователь найден, но неактивен
            await update.message.reply_text(
                f"Привет, {user.first_name}! Ваш аккаунт отключен администратором. "
                f"Пожалуйста, обратитесь к администратору для активации."
            )
            return ConversationHandler.END
        else:
            # User is not registered, start registration process
            logger.info(f"New user {user.id} ({user.full_name}) starting registration")
            await update.message.reply_text(
                f"Добро пожаловать! Вы еще не зарегистрированы в системе.\n\n"
                f"Ваш Telegram ID: {user.id}\n\n"
                f"Для регистрации введите кодовое слово:"
            )
            # Store user ID in context for registration
            context.user_data['registration_telegram_id'] = user.id
            return ConversationState.ENTERING_CODE
    
    # Store employee info in user_data
    context.user_data['employee'] = employee
    
    # Очищаем историю сообщений перед началом нового отчета
    await clean_chat_history(update, context) # Удаляем сообщения, но сохраняем отчеты
    
    # Clear any previous report data
    clear_current_report(context)
    
    # Инициализируем новый отчет сразу при запуске
    context.user_data['current_report'] = {
        'timestamp': datetime.now().isoformat(),
        'employee_id': employee.get('id', ''),
        'employee_name': employee.get('name', ''),
        'actions': []
    }
    
    # Загружаем список проектов
    try:
        projects = await sheet_service.get_projects()
        if not projects:
            await update.message.reply_text(
                "Не найдено активных проектов. Пожалуйста, обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Создаем клавиатуру с кнопками проектов
        keyboard = []
        for project in projects:
            project_id = project.get('project_id', '')
            project_name = project.get('project_name', '')
            if project_id and project_name:
                keyboard.append([
                    InlineKeyboardButton(project_name, callback_data=f"project:{project_id}")
                ])
        
        # Добавляем кнопку отмены
        keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем приветствие и список проектов
        welcome_text = f"Здравствуйте, {employee.get('name', 'сотрудник')}!\n\nВыберите проект:"
        message = await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        # Отслеживаем сообщение для последующего удаления
        await track_message(update, context, message.message_id)
        return ConversationState.CHOOSING_PROJECT
        
    except Exception as e:
        logger.error(f"Error loading projects: {e}")
        await update.message.reply_text(
            "Ошибка: не удалось загрузить список проектов. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def check_registration_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Check registration code during registration process.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    # Отслеживаем сообщение для последующего удаления
    if update.message:
        await track_message(update, context, update.message.message_id)
    
    user = update.effective_user
    user_code = update.message.text.strip()
    config = context.bot_data.get('config')
    
    if not config:
        logger.error("Config not found in bot_data")
        await update.message.reply_text(
            "Ошибка: конфигурация не найдена. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    registration_code = config.get('registration_code', 'vibe')
    
    if user_code.lower() != registration_code.lower():
        # Неверный код
        logger.warning(f"User {user.id} entered incorrect registration code: {user_code}")
        await update.message.reply_text(
            "Неверное кодовое слово. Пожалуйста, попробуйте еще раз или обратитесь к администратору."
        )
        return ConversationState.ENTERING_CODE
    
    # Код верный, продолжаем регистрацию
    logger.info(f"User {user.id} entered correct registration code")
    await update.message.reply_text(
        f"Кодовое слово верно! Теперь введите ваше имя и фамилию:"
    )
    return ConversationState.ENTERING_NAME


async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process user's name input during registration.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    user_name = update.message.text.strip()
    
    # Track the user's message for later deletion
    await track_message(update, context, update.message.message_id)
    
    if len(user_name) < 3:
        error_message = await update.message.reply_text(
            "Имя слишком короткое. Пожалуйста, введите полное имя и фамилию."
        )
        # Track error message for later deletion
        await track_message(update, context, error_message.message_id)
        return ConversationState.ENTERING_NAME
    
    # Store name in context
    context.user_data['registration_name'] = user_name
    telegram_id = context.user_data.get('registration_telegram_id')
    
    # Ask for confirmation
    confirmation_message = await update.message.reply_text(
        f"Спасибо! Проверьте введенные данные:\n\n"
        f"Имя: {user_name}\n"
        f"Telegram ID: {telegram_id}\n\n"
        f"Все верно? Нажмите кнопку для подтверждения.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Подтвердить", callback_data="confirm_registration")],
            [InlineKeyboardButton("Изменить имя", callback_data="change_name")]
        ])
    )
    
    # Track confirmation message for later deletion
    await track_message(update, context, confirmation_message.message_id)
    return ConversationState.REGISTRATION_CONFIRM

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Confirm user registration and save to Google Sheets.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()
    
    sheet_service = context.bot_data.get('sheet_service')
    telegram_id = context.user_data.get('registration_telegram_id')
    name = context.user_data.get('registration_name')
    
    if not sheet_service or not telegram_id or not name:
        await query.edit_message_text(
            "Ошибка регистрации. Пожалуйста, попробуйте снова с помощью команды /start."
        )
        return ConversationHandler.END
    
    # Register user in Google Sheets
    success = await sheet_service.register_user(telegram_id, name)
    
    if success:
        # Get the newly registered employee
        employee = await sheet_service.get_employee(telegram_id)
        if employee:
            context.user_data['employee'] = employee
            
            # Clear any previous report data
            clear_current_report(context)
            
            # Отправляем сообщение о успешной регистрации
            await query.edit_message_text(
                f"Регистрация успешно завершена! Добро пожаловать, {name}! 🎉\n\n"
                f"Теперь вы можете создавать отчеты о выполненных работах."
            )
            
            # Сразу начинаем создание отчета без дополнительной кнопки
            return await fixed_start_report(update, context)
    
    # If we got here, something went wrong
    await query.edit_message_text(
        "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже или обратитесь к администратору."
    )
    return ConversationHandler.END

async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Allow user to change their name during registration.
    
    Args:
        update: Update object
        context: CallbackContext
        
    Returns:
        Next conversation state
    """
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Пожалуйста, введите ваше имя и фамилию заново:"
    )
    return ConversationState.ENTERING_NAME

async def start_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start creating a new report.
    
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
    await clean_chat_history(update, context) # Удаляем сообщения, но сохраняем отчеты
    
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
        await track_message(update, context, message.message_id)
        return ConversationState.CHOOSING_PROJECT
        
    except Exception as e:
        logger.error(f"Error loading projects: {e}")
        # Вместо редактирования сообщения отправляем новое
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка: не удалось загрузить список проектов. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
