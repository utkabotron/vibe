"""
Decorator utilities for Vibe Work Bot.
"""
import functools
import logging
from typing import Callable, Any

from telegram import Update
from telegram.ext import ContextTypes

from utils.bot_utils import track_message

logger = logging.getLogger(__name__)


def track_bot_messages(func: Callable) -> Callable:
    """
    Decorator to automatically track bot messages for deletion.
    
    Args:
        func: The handler function to decorate
        
    Returns:
        Wrapped function that tracks bot messages
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        # Call the original function
        result = await func(update, context, *args, **kwargs)
        
        # If the function returned a message, track it
        if hasattr(result, 'message_id'):
            await track_message(update, context, result.message_id)
        
        return result
    
    return wrapper
