# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VIBE - Telegram-бот для учёта рабочих сессий, материалов и генерации отчётов. Интегрируется с Google Sheets для хранения данных и использует многоступенчатый ConversationHandler для создания отчётов.

## Technology Stack

**Telegram Bot:**
- **python-telegram-bot** (>=20.0) - асинхронная библиотека для Telegram Bot API
- **gspread** (>=5.7.0) - библиотека для работы с Google Sheets
- **google-auth** (>=2.16.0) - аутентификация через service account
- **python-dotenv** (>=1.0.0) - загрузка переменных окружения

**Mini App:**
- **aiohttp** (>=3.8.0) - асинхронный HTTP сервер для API и статики
- **Vanilla JavaScript** - фронтенд без фреймворков (~1557 строк)
- **IndexedDB** - клиентское хранилище для offline-режима (~267 строк обёртки)

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

**Основные:**
- `TELEGRAM_TOKEN` - токен бота из BotFather
- `GOOGLE_SERVICE_ACCOUNT_PATH` - путь к JSON-файлу с учётными данными сервисного аккаунта
- `SHEET_KEY_REFERENCE` - ID Google Spreadsheet с справочными данными
- `SHEET_KEY_REPORTS` - ID Google Spreadsheet для отчётов (может совпадать с SHEET_KEY_REFERENCE)
- `REGISTRATION_CODE` - кодовое слово для регистрации (по умолчанию 'vipe')
- `CACHE_REFRESH_INTERVAL` - интервал обновления кэша в минутах (по умолчанию 1440)

**Mini App (опционально):**
- `MINIAPP_HOST` - хост для сервера (по умолчанию '0.0.0.0')
- `MINIAPP_PORT` - порт для сервера (по умолчанию 8080)

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
├── miniapp/                     # Telegram Mini App
│   ├── index.html              # Single-page app
│   ├── style.css               # Telegram theme styles
│   ├── app.js                  # Main application logic
│   └── db.js                   # IndexedDB wrapper
├── api/
│   ├── __init__.py
│   └── miniapp_api.py          # REST API for Mini App
├── miniapp_server.py            # HTTP server for Mini App
├── deploy/
│   ├── miniapp.service         # Systemd service
│   └── nginx-miniapp.conf      # Nginx config example
└── requirements.txt
```

## Mini App

Telegram Mini App для создания отчётов с offline-поддержкой.

### Дизайн-система (iOS Telegram-like)

**Обновлено:** 2026-01-30
Mini App использует iOS/Telegram дизайн-систему для нативного ощущения в Telegram.

**Ключевые принципы:**
- **iOS Grouped List** - формы и табы объединены в единый белый контейнер с тенью
- **Segmented Control** - табы категорий выполнены в стиле iOS (padding 2px, border-radius 9px)
- **iOS Typography** - базовый размер 17px с line-height 1.29
- **Telegram Colors** - цветовая схема соответствует дизайн-гайдам Telegram

**Типографика (miniapp/style.css:66-87):**
```css
--text-xs: 12px;
--text-sm: 13px;
--text-base: 17px;    /* iOS standard */
--text-lg: 19px;
--text-xl: 22px;
--text-2xl: 26px;
--leading-normal: 1.29; /* iOS standard 17px = 22px line-height */
```

**Цветовая палитра (miniapp/style.css:28-51):**
```css
--text-secondary: #8E8E93;           /* iOS gray */
--text-tertiary: #C7C7CC;            /* iOS light gray */
--bg-tertiary: rgba(118,118,128,0.12); /* iOS input background */
--separator-opaque: rgba(60,60,67,0.29);
--separator-subtle: rgba(60,60,67,0.12);
--state-hover: rgba(0,0,0,0.05);     /* Subtle hover */
```

**Border Radius (miniapp/style.css:63-69):**
```css
--radius-sm: 7px;   /* iOS small radius */
--radius-md: 12px;  /* iOS medium radius */
--radius-lg: 14px;  /* iOS large radius */
```

**Grouped List структура (miniapp/index.html:18-184):**
```html
<div class="form-group">           <!-- iOS grouped list container -->
  <div class="category-tabs">      <!-- Segmented control -->
    <button class="tab active">
      <span class="tab-icon" data-icon="labour"></span>
      <span class="tab-label">Работы</span>
    </button>
    ...
  </div>
  <div class="form-separator"></div> <!-- 1px separator line -->
  <div id="action-form-container">
    <div class="action-form">...</div>
  </div>
</div>
```

**Icons:**
- Иконки инъектируются через `injectIcons()` в `miniapp/app.js:112`
- SVG иконки определены в `miniapp/icons.js`
- Размер: 20x20px для табов

**Важные правила:**
1. **Не использовать text-transform: uppercase** - iOS использует normal case
2. **Консистентные отступы** - использовать CSS переменные `--space-*`
3. **Line-height = 1.29** - для всех текстов (iOS стандарт)
4. **Input/textarea** - явно указывать font-size и line-height для консистентности с placeholder
5. **Segmented control** - border-radius контейнера на 2px больше чем у активной кнопки

### Архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Mini App   │────▶│  API Server │────▶│ Google      │
│  (Browser)  │◀────│  (aiohttp)  │     │ Sheets      │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  IndexedDB  │     │  Telegram   │
│  (offline)  │     │  Bot API    │
└─────────────┘     └─────────────┘
```

### Параллельная работа Bot + Mini App

**Два независимых процесса:**
1. `main.py` - Telegram бот (ConversationHandler) - порт 443 (Telegram webhook/polling)
2. `miniapp_server.py` - HTTP API для Mini App - порт 8080

**Общие компоненты:**
- Оба используют `services/sheet_service.py` для работы с Google Sheets
- Оба читают/пишут в одни и те же таблицы
- Оба используют один `config/.env`

**Разница:**
- Bot: пошаговый диалог через кнопки и текстовые сообщения
- Mini App: полноценный веб-интерфейс с формами и offline-поддержкой

**Деплой:** Оба процесса управляются через systemd (`hosting-bot.service` и `miniapp.service`) и могут работать независимо.

### Запуск локально

```bash
# Установить зависимости (добавлен aiohttp)
pip install -r requirements.txt

# Запустить Mini App сервер (порт 8080)
python miniapp_server.py

# Открыть в браузере
# http://localhost:8080/miniapp
```

### API Endpoints

```
POST /api/miniapp/init
  ← { initData: "telegram_init_string" }
  → { user, references: { projects, products, labourTypes, ... } }

  Валидирует initData через HMAC-SHA256 (см. validate_init_data в api/miniapp_api.py)
  Проверяет пользователя в Google Sheets (таблица Users)
  Возвращает справочники для offline-кэша

POST /api/miniapp/submit
  ← { initData, report: { projectId, productId, actions: [...] } }
  → { success: true }

  Сохраняет отчёт в Google Sheets
  Отправляет карточку в чат бота через Telegram Bot API

GET /api/miniapp/sync
  → { references: { ... } }

  Возвращает актуальные справочники (для фонового обновления кэша)
```

**Безопасность:** Все эндпоинты кроме `/sync` требуют валидный Telegram `initData` с корректным HMAC. Валидация происходит по алгоритму из официальной документации Telegram WebApps.

### Деплой Mini App на сервер

```bash
# 1. Скопировать systemd service
sudo cp deploy/miniapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable miniapp
sudo systemctl start miniapp

# 2. Настроить nginx (требуется домен с HTTPS для Telegram)
# Отредактировать deploy/nginx-miniapp.conf, заменить домен
sudo cp deploy/nginx-miniapp.conf /etc/nginx/sites-available/miniapp
sudo ln -s /etc/nginx/sites-available/miniapp /etc/nginx/sites-enabled/
sudo certbot --nginx -d miniapp.yourdomain.com
sudo nginx -t && sudo systemctl reload nginx

# 3. Проверить
curl https://miniapp.yourdomain.com/api/miniapp/sync
```

### Управление Mini App сервером

```bash
# Статус
systemctl status miniapp

# Перезапуск
systemctl restart miniapp

# Логи
journalctl -u miniapp -f
```

### Production URL

- **Mini App**: https://vibe-bot.brdg.tools/miniapp/
- **API**: https://vibe-bot.brdg.tools/api/miniapp/

### Регистрация Mini App в BotFather

1. Открыть @BotFather
2. Выбрать бота → Bot Settings → Menu Button
3. Указать URL: `https://vibe-bot.brdg.tools/miniapp/`

### IndexedDB структура

```javascript
// Store: references (кэш справочников)
{
  id: 'main',
  projects: [...],
  products: { projectId: [...] },
  labourTypes: [...],
  paintTypes: [...],
  paintMaterials: { typeId: [...] },
  materialTypes: [...],
  materials: { typeId: [...] },
  updatedAt: timestamp
}

// Store: drafts (черновики и pending отчёты)
{
  id: 'draft_xxx',
  status: 'draft' | 'pending' | 'synced',
  projectId, productId, projectName, productName,
  actions: [...],
  comment: '',
  createdAt, syncedAt
}
```

### Offline-режим

1. Справочники кэшируются в IndexedDB при первой загрузке
2. При добавлении действия — сохраняется локально мгновенно (optimistic UI)
3. При отправке без сети — отчёт помечается как `pending`
4. При восстановлении связи — автоматическая синхронизация pending-отчётов
5. Пользователь видит индикатор pending-отчётов и может повторить отправку вручную

**Важно:** Mini App работает полностью автономно после первой загрузки. Интернет нужен только для отправки отчётов в Google Sheets.

## Common Gotchas

1. **Field name flexibility**: Код поддерживает разные названия полей в Google Sheets (project_id vs project, type_id vs type). При добавлении новых функций придерживайтесь этого паттерна.

2. **String conversion**: Все ID конвертируются в строки при использовании в качестве ключей словаря (`str(project_id)`).

3. **Active status**: Проекты фильтруются по `active='true'` (lowercase), пользователи по `active='TRUE'` (uppercase). Это inconsistency нужно учитывать.

4. **Time formatting**: При отображении трудозатрат в отчётах всегда используйте `format_time_as_hhmm()` для консистентности.

5. **Message tracking**: Все временные сообщения должны отслеживаться через `track_message()`, кроме сообщений с отчётами (используйте `mark_report_message()`).

6. **Report structure**: В Google Sheets записывается отдельная строка для каждого действия в отчёте, а не одна строка на весь отчёт.

7. **IPv6 проблема**: Сервер не поддерживает IPv6, но DNS возвращает IPv6 адреса первыми. В `main.py` добавлен патч для принудительного использования IPv4.

8. **Устаревшие сессии**: ConversationHandler имеет таймаут 10 минут. При нажатии на устаревшие кнопки показывается инлайн-кнопка "🔄 Начать заново" (callback_data="restart_session").

9. **Mini App initData validation**: При разработке новых эндпоинтов всегда используйте `validate_init_data()` для проверки подлинности запросов. Без этого возможна подделка данных.

10. **Два способа создания отчётов**: Пользователи могут создавать отчёты либо через Telegram-бот (ConversationHandler), либо через Mini App (веб-интерфейс). Оба способа пишут в одну таблицу Google Sheets, но используют разные entry points.

## Сервер и деплой

### Данные сервера
- **IP**: 176.57.214.150
- **Путь к боту**: `/root/Hosting_bot`
- **SSH алиас**: `vibe-server` (настроен в `~/.ssh/config` с ключом `id_server_176`)
- **SSH прямой**: `ssh root@176.57.214.150` (требует ключ)

### SSH настройка

**Конфигурация** (`~/.ssh/config`):
```
Host vibe-server
  HostName 176.57.214.150
  User root
  IdentityFile ~/.ssh/id_server_176
  ServerAliveInterval 15
  ServerAliveCountMax 3
  TCPKeepAlive yes
  Compression yes
  ControlMaster auto
  ControlPath ~/.ssh/control-%r@%h:%p
  ControlPersist 10m
  StrictHostKeyChecking no
```

**Проверка подключения:**
```bash
ssh vibe-server "whoami && pwd"
# Должен вернуть: root /root
```

**Если SSH не работает:**
- Проверить что ключ существует: `ls -la ~/.ssh/id_server_176`
- Проверить права: `chmod 600 ~/.ssh/id_server_176`
- Проверить порт: `nc -zv 176.57.214.150 22`

### Управление ботом (systemd)
```bash
# Статус
systemctl status hosting-bot

# Перезапуск
systemctl restart hosting-bot

# Остановка
systemctl stop hosting-bot

# Логи в реальном времени
journalctl -u hosting-bot -f

# Логи за последние N минут
journalctl -u hosting-bot --since "5 minutes ago" --no-pager
```

### Деплой изменений

**Полный процесс деплоя:**

```bash
# 1. Закоммитить и запушить изменения
git add -A
git commit -m "описание изменений

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main

# 2. Деплой на сервер (через алиас vibe-server)
ssh vibe-server "cd /root/Hosting_bot && git pull origin main && systemctl restart hosting-bot miniapp"

# 3. Проверка статуса
ssh vibe-server "systemctl status hosting-bot miniapp --no-pager | head -20"
```

**Быстрый деплой одной командой:**

```bash
# После git push origin main:
ssh vibe-server "cd /root/Hosting_bot && git pull && systemctl restart hosting-bot miniapp"
```

**Деплой только бота (без Mini App):**
```bash
ssh vibe-server "cd /root/Hosting_bot && git pull && systemctl restart hosting-bot"
```

**Деплой только Mini App:**
```bash
ssh vibe-server "cd /root/Hosting_bot && git pull && systemctl restart miniapp"
```

**На сервере вручную:**
```bash
# Подключиться
ssh vibe-server

# В директории бота
cd /root/Hosting_bot
git pull origin main
systemctl restart hosting-bot miniapp

# Проверить
systemctl status hosting-bot
systemctl status miniapp
```

### Проверка успешности деплоя

**После деплоя проверить:**

```bash
# 1. Статус сервисов
ssh vibe-server "systemctl is-active hosting-bot miniapp"
# Должен вернуть: active active

# 2. Логи (последние 10 строк)
ssh vibe-server "journalctl -u hosting-bot -n 10 --no-pager"
ssh vibe-server "journalctl -u miniapp -n 10 --no-pager"

# 3. Порты (8080 для miniapp)
ssh vibe-server "ss -tlnp | grep 8080"
# Должен показать: python3 слушает на 0.0.0.0:8080

# 4. HTTP доступность
curl -s -o /dev/null -w "HTTP: %{http_code}\n" https://vibe-bot.brdg.tools/miniapp/
# Должен вернуть: HTTP: 200

# 5. API работает
curl -s https://vibe-bot.brdg.tools/api/miniapp/sync | python3 -m json.tool | head -10
# Должен вернуть JSON с проектами
```

**Признаки успешного деплоя:**
- ✅ Оба сервиса `active (running)`
- ✅ В логах нет ошибок (ERROR, FAILED)
- ✅ Порт 8080 слушает на 0.0.0.0
- ✅ HTTPS возвращает 200
- ✅ API возвращает данные

## Git workflow

### Настройка git (один раз)
```bash
git config user.email "pavelbrick@gmail.com"
```

### Коммит и пуш
```bash
git add -A && git commit -m "описание изменений" && git push origin main
```

### Коммит с Co-Author (для Claude)
```bash
git commit -m "$(cat <<'EOF'
описание изменений

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

## Диагностика проблем

### Бот не запускается
1. Проверить логи: `journalctl -u hosting-bot --since "2 minutes ago" --no-pager`
2. Проверить процессы: `ps aux | grep python`
3. Убить зависшие процессы: `killall -9 python`
4. Перезапустить: `systemctl restart hosting-bot`

### Google Sheets API quota exceeded (429)
- Подождать 1-2 минуты
- Не перезапускать бота многократно - каждый запуск потребляет ~20 API запросов

### Бот зависает при запуске (не доходит до "Successfully connected")
- Вероятно проблема с IPv6 - проверить что патч в main.py на месте
- Тест: `curl -s --max-time 10 https://sheets.googleapis.com` должен вернуть ответ

### Конфликт "terminated by other getUpdates request"
- Запущено несколько экземпляров бота
- Решение: `killall -9 python && systemctl restart hosting-bot`

### Mini App не загружается или показывает ошибки
1. Проверить статус сервера: `systemctl status miniapp`
2. Проверить логи: `journalctl -u miniapp -f`
3. Убедиться что nginx проксирует на правильный порт (8080 по умолчанию)
4. Проверить HTTPS сертификат (Telegram требует HTTPS для Mini Apps)
5. Проверить CORS headers в ответах API (должен быть Access-Control-Allow-Origin)

### Проблемы при деплое

**SSH зависает:**
```bash
# Проверить порт открыт
nc -zv 176.57.214.150 22

# Если зависает - проблема с sshpass, использовать алиас:
ssh vibe-server "whoami"
```

**Git pull не работает:**
```bash
# На сервере проверить статус
ssh vibe-server "cd /root/Hosting_bot && git status"

# Если есть uncommitted changes - сбросить
ssh vibe-server "cd /root/Hosting_bot && git reset --hard HEAD && git pull"
```

**Mini App возвращает 502:**
```bash
# Проверить слушает ли на правильном интерфейсе
ssh vibe-server "ss -tlnp | grep 8080"
# Должен быть 0.0.0.0:8080, а не 127.0.0.1:8080

# Если 127.0.0.1 - исправить в systemd:
ssh vibe-server "sed -i 's/MINIAPP_HOST=127.0.0.1/MINIAPP_HOST=0.0.0.0/' /etc/systemd/system/miniapp.service && systemctl daemon-reload && systemctl restart miniapp"
```

**Telegram flood control при перезапуске:**
```bash
# Ошибка: "Flood control exceeded. Retry in X seconds"
# Просто подождать указанное время, сервис автоматически перезапустится
# Или подождать и перезапустить вручную:
sleep 60 && ssh vibe-server "systemctl restart miniapp"
```
