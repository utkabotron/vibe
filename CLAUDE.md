# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VIBE - Telegram-бот для учёта рабочих сессий, материалов и генерации отчётов. Интегрируется с Google Sheets для хранения данных и использует многоступенчатый ConversationHandler для создания отчётов.

## Technology Stack

- **python-telegram-bot** (>=20.0) - асинхронная библиотека для Telegram Bot API
- **gspread** (>=5.7.0) - библиотека для работы с Google Sheets
- **google-auth** (>=2.16.0) - аутентификация через service account
- **python-dotenv** (>=1.0.0) - загрузка переменных окружения

## Development Commands

### Запуск бота локально
```bash
python main.py
```

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Настройка окружения
Скопируйте `config/.env.example` в `config/.env` и заполните:
- `TELEGRAM_TOKEN` - токен бота из BotFather
- `GOOGLE_SERVICE_ACCOUNT_PATH` - путь к JSON-файлу с учётными данными сервисного аккаунта
- `SHEET_KEY_REFERENCE` - ID Google Spreadsheet с справочными данными
- `SHEET_KEY_REPORTS` - ID Google Spreadsheet для отчётов (может совпадать с SHEET_KEY_REFERENCE)
- `REGISTRATION_CODE` - кодовое слово для регистрации (по умолчанию 'vipe')
- `CACHE_REFRESH_INTERVAL` - интервал обновления кэша в минутах (по умолчанию 1440)

## Core Architecture

### Entry Point (main.py)
- Инициализирует Application builder от python-telegram-bot
- Создаёт единый ConversationHandler со всеми состояниями
- Инициализирует SheetService с автоматическим кэшированием
- Запускает фоновую задачу периодического обновления кэша
- Настраивает graceful shutdown с platform-specific обработкой сигналов (Windows vs Unix)

### State Management (handlers/conversation_states.py)
Определяет все состояния разговора через ConversationState (IntEnum):

**Регистрация:**
- `ENTERING_CODE` → `ENTERING_NAME` → `REGISTRATION_CONFIRM`

**Основной flow:**
- `CHOOSING_PROJECT` → `CHOOSING_PRODUCT` → `CHOOSING_CATEGORY`

**Категории действий:**
- **Работы**: `CHOOSING_LABOUR_TYPE` → `ENTERING_HOURS`
- **ЛКМ**: `CHOOSING_PAINT_TYPE` → `CHOOSING_PAINT_MATERIAL` → `ENTERING_PAINT_QUANTITY`
- **Плита**: `CHOOSING_MATERIAL_TYPE` → `CHOOSING_MATERIAL` → `ENTERING_MATERIAL_QUANTITY`
- **Брак**: обрабатывается без дополнительных состояний

**Завершение:**
- `ENTERING_COMMENT` → `CONFIRM_ACTION` → `ADD_ANOTHER_ACTION` → `CONFIRM_REPORT`

### Handler System

Handlers используют callback_query patterns для навигации:

1. **start_handler.py**: Регистрация и начало работы
   - Проверяет авторизацию по telegram_id в таблице Users
   - Запрашивает кодовое слово (REGISTRATION_CODE) для новых пользователей
   - Проверяет статус `active` пользователя ('TRUE'/'FALSE')
   - После успешной регистрации сразу переходит к созданию отчёта

2. **project_handler.py** / **product_handler.py**: Выбор проекта и изделия
   - Использует callback_data с префиксами: `project:ID`, `product:ID`

3. **category_handler.py**: Выбор категории действия (Работы/ЛКМ/Плита/Брак)

4. **labour_handler.py**: Трудозатраты
   - Поддерживает ввод времени в формате `HH:MM` или десятичных часов
   - Парсинг через `parse_time_input()` из bot_utils.py
   - Quick-select кнопки: `time:0:15`, `time:0:30`, `time:1:00` и т.д.

5. **paint_handler.py** / **materials_handler.py**: Расход материалов
   - Двухступенчатый выбор: тип → конкретный материал
   - Поддержка quick-select объёмов: `volume:0.5`, `volume:1.0`
   - Для материалов доступен `skip_quantity` (опционально)

6. **comment_handler.py**: Комментарий к действию (опционально)

7. **report_handler.py**: Подтверждение и отправка отчёта
   - Форматирует summary через `format_report_summary()`
   - Сохраняет через `sheet_service.save_report()`
   - Отмечает сообщения с отчётами через `mark_report_message()` для защиты от автоудаления

### Google Sheets Integration (services/sheet_service.py)

**Кэширование:**
- Асинхронная инициализация с начальной загрузкой всех справочников
- Периодическое обновление через `refresh_cache_periodically()` (фоновая задача)
- Асинхронные локи (`asyncio.Lock`) для защиты кэша
- Все операции чтения работают с кэшем, запись идёт напрямую в Sheets

**Структура кэша:**
```python
_cache = {
    'projects': [],
    'products': {},        # Keyed by project_id
    'labour_types': [],
    'paint_material_types': [],
    'paint_materials': {},  # Keyed by type_id
    'material_types': [],
    'materials': {},        # Keyed by type_id
    'employees': {}         # Keyed by telegram_id
}
```

**Ожидаемые worksheets:**
- `Projects`: project_id, project_name, active
- `Products`: product_id, product_name, project_id (или project)
- `Operations`: work_id/type_id, work_name/type_name (для трудозатрат)
- `PaintMaterialTypes`: type_id, type_name
- `PaintMaterials`: material_id, material_name, type_id (или type)
- `MaterialTypes`: type_id, type_name
- `Materials`: material_id, material_name, type_id (или type)
- `Users`: telegram_id (или id/tg_id), name, role, active
- `Reports`: timestamp, employee_id, employee_name, project_id, project_name, product_id, product_name, category, subcategory, subcategory_name, quantity, unit, comment

**Гибкость полей:**
- Код поддерживает разные названия полей (project_id/project, type_id/type, telegram_id/id/tg_id)
- При поиске по ID всегда конвертирует в string для консистентности

**Сохранение отчётов:**
- `save_report()` записывает несколько строк за один вызов (по одной на каждое действие)
- Категории автоматически транслируются на русский через `CATEGORY_TRANSLATIONS`
- Для категории "Работы" в колонке subcategory всегда "Трудозатраты"
- Для "ЛКМ" и "Плита" в subcategory записывается тип материала

### User Data Flow (context.user_data)

**Структура current_report:**
```python
{
    'timestamp': '2025-12-08T15:30:00',
    'employee_id': '123',
    'employee_name': 'Иван Иванов',
    'project_id': 'P1',
    'project_name': 'Проект 1',
    'product_id': 'PR1',
    'product_name': 'Изделие 1',
    'actions': [
        {
            'category': 'Работы',
            'subcategory': 'Монтаж',
            'subcategory_name': 'Монтаж оборудования',
            'quantity': '2.5',
            'unit': 'ч',
            'comment': 'Опционально'
        }
    ]
}
```

**Структура current_action:**
- Формируется по мере прохождения состояний
- После подтверждения добавляется в `current_report['actions']` и очищается

**Отслеживание сообщений:**
- `message_ids_to_delete` - ID временных сообщений для удаления
- `report_message_ids` - ID сообщений с отчётами (не удаляются при clean_chat_history)

### Keyboard Utilities (utils/bot_utils.py)

Все клавиатуры создаются через `build_menu()` с footer_buttons для Back-кнопок:
- `create_projects_keyboard()`
- `create_products_keyboard()`
- `create_category_keyboard()`
- `create_labour_types_keyboard()`
- `create_paint_types_keyboard()` / `create_paint_materials_keyboard()`
- `create_material_types_keyboard()` / `create_materials_keyboard()`

**Парсинг времени:**
- `parse_time_input(time_str)` - поддерживает `HH:MM` и десятичные часы с запятой/точкой
- `format_time_as_hhmm(hours_float)` - форматирует обратно в `HH:MM`

**Управление чатом:**
- `clean_chat_history()` - удаляет отслеживаемые сообщения, кроме отчётов
- `track_message()` - добавляет message_id в список на удаление
- `mark_report_message()` - защищает сообщение от удаления

## Error Handling Patterns

- Global error handler в main.py обрабатывает `APIError`, `SpreadsheetNotFound`, `TimeoutError`
- Все handler-ы имеют try/except с fallback на ConversationHandler.END
- При ошибках сохранения отчёта предлагается кнопка "Повторить"
- Логирование через стандартный logging module с настройками из config.py

## Important Implementation Notes

### Регистрация пользователей
- Новые пользователи обязаны ввести `REGISTRATION_CODE` перед регистрацией
- После успешной регистрации пользователь добавляется в кэш и сразу переходит к созданию отчёта
- Проверка статуса `active` происходит при каждом старте

### ConversationHandler
- Единый ConversationHandler на всё приложение (не отдельные обработчики)
- Fallback handlers: `/cancel` команда и `cancel` callback
- После завершения отчёта пользователь должен использовать `/start` для нового отчёта

### Кэширование
- Все справочные данные загружаются при старте
- Фоновое обновление каждые `CACHE_REFRESH_INTERVAL` минут
- Graceful shutdown останавливает фоновую задачу

### Платформа
- Windows-специфичная обработка сигналов (signal.signal вместо loop.add_signal_handler)
- Относительные пути к service account файлам преобразуются относительно project root

## File Structure

```
vibe/
├── main.py                      # Entry point
├── config/
│   ├── config.py               # Environment variables & constants
│   └── .env.example            # Template for .env
├── handlers/
│   ├── conversation_states.py  # State machine definition
│   ├── start_handler.py        # Registration & start
│   ├── project_handler.py
│   ├── product_handler.py
│   ├── category_handler.py
│   ├── labour_handler.py
│   ├── paint_handler.py
│   ├── materials_handler.py
│   ├── defect_handler.py
│   ├── comment_handler.py
│   └── report_handler.py       # Confirmation & submission
├── services/
│   └── sheet_service.py        # Google Sheets integration
├── utils/
│   ├── bot_utils.py            # Keyboards, formatting, chat management
│   └── decorators.py           # Message tracking decorator
└── requirements.txt
```

## Common Gotchas

1. **Field name flexibility**: Код поддерживает разные названия полей в Google Sheets (project_id vs project, type_id vs type). При добавлении новых функций придерживайтесь этого паттерна.

2. **String conversion**: Все ID конвертируются в строки при использовании в качестве ключей словаря (`str(project_id)`).

3. **Active status**: Проекты фильтруются по `active='true'` (lowercase), пользователи по `active='TRUE'` (uppercase). Это inconsistency нужно учитывать.

4. **Time formatting**: При отображении трудозатрат в отчётах всегда используйте `format_time_as_hhmm()` для консистентности.

5. **Message tracking**: Все временные сообщения должны отслеживаться через `track_message()`, кроме сообщений с отчётами (используйте `mark_report_message()`).

6. **Report structure**: В Google Sheets записывается отдельная строка для каждого действия в отчёте, а не одна строка на весь отчёт.
