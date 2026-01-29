"""
Mini App API endpoints for VIBE bot
Provides REST API for the Telegram Mini App
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import parse_qsl

from aiohttp import web

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Validate Telegram Mini App initData using HMAC-SHA256.
    Returns parsed user data if valid, None if invalid.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        return None

    try:
        # Parse init data
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))

        # Extract hash
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return None

        # Build data-check-string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        # Calculate secret key
        secret_key = hmac.new(
            b'WebAppData',
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Validate
        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning("Invalid init_data hash")
            return None

        # Parse user data
        user_data = parsed.get('user')
        if user_data:
            return json.loads(user_data)

        return parsed

    except Exception as e:
        logger.error(f"Error validating init_data: {e}")
        return None


def create_miniapp_routes(sheet_service, bot_token: str, bot=None):
    """
    Create aiohttp routes for Mini App API.

    Args:
        sheet_service: SheetService instance for data access
        bot_token: Telegram bot token for validation
        bot: Telegram bot instance for sending messages

    Returns:
        List of aiohttp routes
    """

    async def handle_init(request: web.Request) -> web.Response:
        """
        POST /api/miniapp/init

        Initialize Mini App: validate user and return references.
        """
        try:
            data = await request.json()
            init_data = data.get('initData', '')

            # Validate Telegram initData
            user_data = validate_init_data(init_data, bot_token)

            # For development/testing without Telegram
            if not user_data:
                logger.warning("No valid initData - using development mode")
                user_data = {'id': 191440421, 'first_name': 'Developer'}

            # Get employee info from Users table
            employee = None
            telegram_id = user_data.get('id')
            if telegram_id:
                employee = await sheet_service.get_employee(str(telegram_id))

            # Build references
            references = await build_references(sheet_service)

            # Check if user is registered and active
            is_registered = employee is not None
            is_active = employee.get('active', '').upper() == 'TRUE' if employee else False

            return web.json_response({
                'success': True,
                'user': {
                    'telegram_id': telegram_id,
                    'telegram_name': user_data.get('first_name'),
                    # Employee data from Users table
                    'employee_id': employee.get('id', '') if employee else None,
                    'employee_name': employee.get('name', '') if employee else None,
                    'is_registered': is_registered,
                    'is_active': is_active
                },
                'references': references
            })

        except Exception as e:
            logger.error(f"Error in /init: {e}", exc_info=True)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)


    async def handle_submit(request: web.Request) -> web.Response:
        """
        POST /api/miniapp/submit

        Submit a report to Google Sheets and send notification to chat.
        """
        try:
            data = await request.json()
            init_data = data.get('initData', '')
            report = data.get('report', {})

            # Validate user
            user_data = validate_init_data(init_data, bot_token)
            if not user_data:
                # Fallback for development/testing without Telegram
                user_data = {'id': 191440421, 'first_name': 'Developer'}

            # Validate report
            if not report.get('actions'):
                return web.json_response({
                    'success': False,
                    'error': 'No actions in report'
                }, status=400)

            # Get employee data from Users table
            telegram_id = user_data.get('id')
            employee = None
            if telegram_id:
                employee = await sheet_service.get_employee(str(telegram_id))

            # Use employee data from table, fallback to report data
            employee_id = employee.get('id', '') if employee else report.get('employee_id', str(telegram_id))
            employee_name = employee.get('name', '') if employee else report.get('employee_name', 'Unknown')

            # Prepare report data for sheet_service
            report_data = {
                'timestamp': report.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                'employee_id': str(employee_id),
                'employee_name': employee_name,
                'project_id': report.get('project_id'),
                'project_name': report.get('project_name'),
                'product_id': report.get('product_id'),
                'product_name': report.get('product_name'),
                'actions': report.get('actions', [])
            }

            # Each action now has its own comment field (no global comment)

            # Save to Google Sheets
            success = await sheet_service.save_report(report_data)

            if not success:
                return web.json_response({
                    'success': False,
                    'error': 'Failed to save report'
                }, status=500)

            # Send notification to chat
            if bot and user_data and user_data.get('id'):
                try:
                    await send_report_notification(
                        bot,
                        user_data['id'],
                        report_data
                    )
                except Exception as e:
                    logger.error(f"Error sending notification: {e}")
                    # Don't fail the request, report is already saved

            return web.json_response({
                'success': True,
                'message': 'Report saved successfully'
            })

        except Exception as e:
            logger.error(f"Error in /submit: {e}", exc_info=True)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)


    async def handle_sync(request: web.Request) -> web.Response:
        """
        GET /api/miniapp/sync

        Get updated references (for cache refresh).
        """
        try:
            references = await build_references(sheet_service)

            return web.json_response({
                'success': True,
                'references': references
            })

        except Exception as e:
            logger.error(f"Error in /sync: {e}", exc_info=True)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)


    # Return routes
    return [
        web.post('/api/miniapp/init', handle_init),
        web.post('/api/miniapp/submit', handle_submit),
        web.get('/api/miniapp/sync', handle_sync),
    ]


async def build_references(sheet_service) -> Dict[str, Any]:
    """
    Build complete references dictionary from sheet_service cache.
    """
    # Get all basic references
    projects = await sheet_service.get_projects()
    labour_types = await sheet_service.get_labour_types()
    paint_types = await sheet_service.get_paint_material_types()
    material_types = await sheet_service.get_material_types()

    # Build products by project
    products_by_project = {}
    for project in projects:
        project_id = project.get('project_id') or project.get('id')
        if project_id:
            products = await sheet_service.get_products(str(project_id))
            products_by_project[str(project_id)] = products

    # Build paint materials by type
    paint_materials_by_type = {}
    for ptype in paint_types:
        type_id = ptype.get('type_id') or ptype.get('id')
        if type_id:
            materials = await sheet_service.get_paint_materials(str(type_id))
            paint_materials_by_type[str(type_id)] = materials

    # Build materials by type
    materials_by_type = {}
    for mtype in material_types:
        type_id = mtype.get('type_id') or mtype.get('id')
        if type_id:
            materials = await sheet_service.get_materials(str(type_id))
            materials_by_type[str(type_id)] = materials

    return {
        'projects': projects,
        'products': products_by_project,
        'labourTypes': labour_types,
        'paintTypes': paint_types,
        'paintMaterials': paint_materials_by_type,
        'materialTypes': material_types,
        'materials': materials_by_type
    }


async def send_report_notification(bot, chat_id: int, report_data: Dict[str, Any]):
    """
    Send report notification message to user's chat.
    """
    # Format timestamp
    timestamp = report_data.get('timestamp', '')
    if isinstance(timestamp, str) and 'T' in timestamp:
        timestamp = timestamp.replace('T', ' ').split('.')[0]

    # Build message
    lines = [
        f"📋 <b>Отчёт отправлен</b>",
        f"",
        f"📊 <b>Дата:</b> {timestamp}",
        f"👤 <b>Сотрудник:</b> {report_data.get('employee_name', 'Unknown')}",
        f"🏗️ <b>Проект:</b> {report_data.get('project_name', '—')}",
        f"📦 <b>Изделие:</b> {report_data.get('product_name', '—')}",
        f"",
        f"📋 <b>Действия:</b>"
    ]

    # Add actions
    for action in report_data.get('actions', []):
        category = action.get('category', '')
        name = action.get('subcategory_name', '')
        quantity = action.get('quantity', '')
        unit = action.get('unit', '')

        icon = {
            'Работы': '🔧',
            'ЛКМ': '🎨',
            'Плита': '📦',
            'Брак': '⚠️'
        }.get(category, '📋')

        # Format time for labour
        if category == 'Работы' and unit == 'ч':
            try:
                hours = float(quantity)
                h = int(hours)
                m = int((hours - h) * 60)
                if m > 0:
                    quantity = f"{h}:{m:02d}"
                else:
                    quantity = f"{h}:00"
            except:
                pass

        lines.append(f"  • {icon} {name}: {quantity} {unit}")

    # Add comment if any
    comment = None
    for action in report_data.get('actions', []):
        if action.get('comment'):
            comment = action.get('comment')
            break

    if comment:
        lines.append(f"")
        lines.append(f"💬 <b>Комментарий:</b> {comment}")

    message = '\n'.join(lines)

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='HTML'
    )


def setup_static_routes(app: web.Application, static_path: str):
    """
    Setup static file serving for Mini App.
    """
    # Add route for index.html (both /miniapp and /miniapp/)
    async def index_handler(request):
        return web.FileResponse(f"{static_path}/index.html")

    app.router.add_get('/miniapp', index_handler)
    app.router.add_get('/miniapp/', index_handler)

    # Static files (css, js)
    app.router.add_static('/miniapp/', static_path, name='miniapp', show_index=False)
