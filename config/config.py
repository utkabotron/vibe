"""
Configuration module for Vibe Work Bot.
Loads environment variables from .env file.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # Try to load from current directory

# Telegram Bot settings
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in environment variables")

# Кодовое слово для регистрации
REGISTRATION_CODE = os.getenv('REGISTRATION_CODE', 'vipe')  # По умолчанию 'vipe'

# Google Sheets settings
GOOGLE_SERVICE_ACCOUNT_PATH = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
if not GOOGLE_SERVICE_ACCOUNT_PATH:
    raise ValueError("GOOGLE_SERVICE_ACCOUNT_PATH is not set in environment variables")

SHEET_KEY_REFERENCE = os.getenv('SHEET_KEY_REFERENCE')
SHEET_KEY_REPORTS = os.getenv('SHEET_KEY_REPORTS')

# Cache settings
CACHE_REFRESH_INTERVAL = int(os.getenv('CACHE_REFRESH_INTERVAL', '1440'))  # minutes

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/vibe_work_bot.log')

# Sheet names
SHEET_PROJECTS = 'Projects'
SHEET_PRODUCTS = 'Products'
SHEET_LABOUR_TYPES = 'Operations'
SHEET_PAINT_MATERIAL_TYPES = 'PaintMaterialTypes'
SHEET_PAINT_MATERIALS = 'PaintMaterials'
SHEET_MATERIAL_TYPES = 'MaterialTypes'
SHEET_MATERIALS = 'Materials'
SHEET_EMPLOYEES = 'Users'
SHEET_REPORTS = 'Reports'

def load_config():
    """Load configuration from environment variables."""
    return {
        'telegram_token': TELEGRAM_TOKEN,
        'registration_code': REGISTRATION_CODE,  # Добавляем кодовое слово в конфигурацию
        'google_service_account_path': GOOGLE_SERVICE_ACCOUNT_PATH,
        'sheet_key_reference': SHEET_KEY_REFERENCE,
        'sheet_key_reports': SHEET_KEY_REPORTS,
        'cache_refresh_interval': CACHE_REFRESH_INTERVAL,
        'log_level': LOG_LEVEL,
        'log_file': LOG_FILE,
        'sheet_names': {
            'projects': SHEET_PROJECTS,
            'products': SHEET_PRODUCTS,
            'labour_types': SHEET_LABOUR_TYPES,
            'paint_material_types': SHEET_PAINT_MATERIAL_TYPES,
            'paint_materials': SHEET_PAINT_MATERIALS,
            'material_types': SHEET_MATERIAL_TYPES,
            'materials': SHEET_MATERIALS,
            'employees': SHEET_EMPLOYEES,
            'reports': SHEET_REPORTS
        }
    }

# Configure logging
def configure_logging():
    """Configure logging for the application."""
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
