"""
Mini App HTTP Server for VIBE

Runs alongside the Telegram bot to serve the Mini App.
Can be run as a separate process or integrated with the bot.

Usage:
    python miniapp_server.py

On server, run with systemd or supervisor alongside the main bot.
"""

# Force IPv4 connections
import socket
_original_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_ipv4_only(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET] or responses
socket.getaddrinfo = _getaddrinfo_ipv4_only

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiohttp import web
from telegram import Bot

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import load_config, configure_logging
from services.sheet_service import SheetService
from api.miniapp_api import create_miniapp_routes, setup_static_routes

logger = logging.getLogger(__name__)

# Configuration
HOST = os.getenv('MINIAPP_HOST', '0.0.0.0')
PORT = int(os.getenv('MINIAPP_PORT', '8080'))


async def create_app():
    """Create and configure the aiohttp application."""
    app = web.Application()

    # Load config
    config = load_config()

    # Initialize sheet service
    sheet_service = SheetService()
    await sheet_service.initialize()
    app['sheet_service'] = sheet_service

    # Initialize Telegram bot (for sending messages)
    bot = Bot(token=config['telegram_token'])
    app['bot'] = bot

    # Setup API routes
    routes = create_miniapp_routes(
        sheet_service=sheet_service,
        bot_token=config['telegram_token'],
        bot=bot
    )
    app.router.add_routes(routes)

    # Setup static files
    static_path = Path(__file__).parent / 'miniapp'
    if static_path.exists():
        setup_static_routes(app, str(static_path))
        logger.info(f"Static files served from: {static_path}")
    else:
        logger.warning(f"Static path not found: {static_path}")

    # CORS headers for development
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            response = await handler(request)

        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    app.middlewares.append(cors_middleware)

    # Startup/cleanup
    async def on_startup(app):
        logger.info(f"Mini App server starting on {HOST}:{PORT}")
        # Start background cache refresh
        refresh_task = asyncio.create_task(
            app['sheet_service']._background_cache_refresh()
        )
        app['refresh_task'] = refresh_task

    async def on_cleanup(app):
        logger.info("Mini App server shutting down...")
        # Cancel refresh task
        if 'refresh_task' in app:
            app['refresh_task'].cancel()
            try:
                await app['refresh_task']
            except asyncio.CancelledError:
                pass
        # Close bot session
        if 'bot' in app:
            await app['bot'].close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


def main():
    """Run the Mini App server."""
    configure_logging()
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    logger.info("=" * 50)
    logger.info("VIBE Mini App Server")
    logger.info("=" * 50)

    app = asyncio.get_event_loop().run_until_complete(create_app())

    logger.info(f"Starting server on http://{HOST}:{PORT}")
    logger.info(f"Mini App URL: http://{HOST}:{PORT}/miniapp")
    logger.info(f"API endpoint: http://{HOST}:{PORT}/api/miniapp/init")

    web.run_app(app, host=HOST, port=PORT, print=None)


if __name__ == '__main__':
    main()
