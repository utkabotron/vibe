"""
Google Sheets service for Vibe Work Bot.
Handles all interactions with Google Sheets, including caching.
"""
import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import gspread
from gspread.exceptions import SpreadsheetNotFound, APIError

from config.config import load_config
from handlers.conversation_states import (
    CATEGORY_LABOUR,
    CATEGORY_PAINT,
    CATEGORY_MATERIALS,
    CATEGORY_DEFECT
)

# Load configuration
config = load_config()

# Словарь для перевода категорий на русский язык
CATEGORY_TRANSLATIONS = {
    CATEGORY_LABOUR: "Работы",
    CATEGORY_PAINT: "ЛКМ",
    CATEGORY_MATERIALS: "Плита",
    CATEGORY_DEFECT: "Брак"
}

logger = logging.getLogger(__name__)


class SheetService:
    """Service for interacting with Google Sheets."""
    
    def __init__(self):
        """Initialize the SheetService."""
        self.gc = None
        self.reference_sheet = None
        self.reports_sheet = None
        
        # Cache for reference data
        self._cache = {
            'projects': [],
            'products': {},  # Keyed by project_id
            'labour_types': [],
            'paint_material_types': [],
            'paint_materials': {},  # Keyed by type_id
            'material_types': [],
            'materials': {},  # Keyed by type_id
            'employees': {}  # Keyed by telegram_id
        }
        self._last_cache_update = 0
        self._cache_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize connection to Google Sheets."""
        try:
            # Получаем путь к файлу учетных данных и обрабатываем его относительно корня проекта
            service_account_path = config['google_service_account_path']
            # Если путь относительный, преобразуем его в абсолютный относительно корня проекта
            if not os.path.isabs(service_account_path):
                # Получаем путь к корню проекта (родительская директория vibe_work_bot)
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                service_account_path = os.path.join(project_root, service_account_path)
            
            logger.info(f"Using service account file: {service_account_path}")
            self.gc = gspread.service_account(filename=service_account_path)
            self.reference_sheet = self.gc.open_by_key(config['sheet_key_reference'])
            # Use the same sheet for reports if sheet_key_reports is not specified
            self.reports_sheet = self.gc.open_by_key(config['sheet_key_reference'])
            logger.info("Successfully connected to Google Sheets")
            
            # Initial cache load
            await self.refresh_cache()
            logger.info(f"Initial cache loaded. Will refresh every {config['cache_refresh_interval']} minutes")
            
            # We don't start the background task here - it will be started by refresh_cache_periodically
            # which is called from main.py
            
        except SpreadsheetNotFound:
            logger.error("Could not find spreadsheet. Check if service account has access.")
            raise
        except Exception as e:
            logger.error(f"Error initializing SheetService: {e}")
            raise
    
    async def _background_cache_refresh(self):
        """Background task to refresh cache periodically."""
        while True:
            try:
                # First sleep, then refresh - this way we don't refresh immediately after startup
                await asyncio.sleep(config['cache_refresh_interval'] * 60)  # Convert minutes to seconds
                logger.info(f"Refreshing cache after {config['cache_refresh_interval']} minutes interval")
                await self.refresh_cache()
                logger.info("Cache refreshed successfully")
            except asyncio.CancelledError:
                logger.info("Cache refresh task cancelled")
                break
            except Exception as e:
                logger.error(f"Error refreshing cache: {e}")
                
    async def refresh_cache_periodically(self):
        """Start background task to refresh cache periodically."""
        # Cancel any existing task first
        await self.stop_refresh_task()
        
        # Create and store new task
        self._refresh_task = asyncio.create_task(self._background_cache_refresh())
        logger.info(f"Started periodic cache refresh task (every {config['cache_refresh_interval']} minutes)")
        return self._refresh_task
        
    async def stop_refresh_task(self):
        """Stop the background cache refresh task."""
        if hasattr(self, '_refresh_task') and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                logger.info("Cache refresh task cancelled")
            except Exception as e:
                logger.error(f"Error cancelling cache refresh task: {e}")
        return
    
    async def refresh_cache(self):
        """Refresh all cached data from Google Sheets."""
        async with self._cache_lock:
            try:
                logger.debug("Starting cache refresh...")
                start_time = time.time()
                
                # Load all reference data
                self._cache['projects'] = self._load_projects_sync()
                self._cache['labour_types'] = self._load_labour_types_sync()
                self._cache['paint_material_types'] = self._load_paint_material_types_sync()
                self._cache['material_types'] = self._load_material_types_sync()
                
                # Load employees
                employees = self._load_employees_sync()
                # Handle different field names for telegram_id
                self._cache['employees'] = {}
                for emp in employees:
                    # Try different possible field names for telegram_id
                    telegram_id = emp.get('telegram_id', emp.get('id', emp.get('tg_id', '')))
                    if telegram_id:
                        self._cache['employees'][str(telegram_id)] = emp
                
                # Load products and materials for each project/type
                for project in self._cache['projects']:
                    # Use 'id' or fallback to 'project_id' if it exists
                    project_id = project.get('id', project.get('project_id', ''))
                    if project.get('active', 'true').lower() == 'true' and project_id:
                        # Convert project_id to string to ensure consistent lookup
                        str_project_id = str(project_id)
                        self._cache['products'][str_project_id] = self._load_products_sync(project_id)
                
                # Handle paint material types with flexible field names
                for paint_type in self._cache['paint_material_types']:
                    type_id = paint_type.get('id', paint_type.get('type_id', ''))
                    if type_id:
                        # Convert type_id to string to ensure consistent lookup
                        str_type_id = str(type_id)
                        self._cache['paint_materials'][str_type_id] = self._load_paint_materials_sync(type_id)
                
                # Handle material types with flexible field names
                for material_type in self._cache['material_types']:
                    type_id = material_type.get('id', material_type.get('type_id', ''))
                    if type_id:
                        # Convert type_id to string to ensure consistent lookup
                        str_type_id = str(type_id)
                        self._cache['materials'][str_type_id] = self._load_materials_sync(type_id)
                
                self._last_cache_update = time.time()
                elapsed_time = time.time() - start_time
                logger.debug(f"Cache refresh completed in {elapsed_time:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Error refreshing cache: {e}")
                raise
    
    def _load_projects_sync(self) -> List[Dict[str, str]]:
        """Load projects from Google Sheets."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['projects'])
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Error loading projects: {e}")
            return []
    
    def _load_products_sync(self, project_id: str) -> List[Dict[str, str]]:
        """Load products for a specific project."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['products'])
            all_products = worksheet.get_all_records()
            # Check for both 'project_id' and 'project' fields
            return [p for p in all_products if str(p.get('project_id', p.get('project', ''))) == str(project_id)]
        except Exception as e:
            logger.error(f"Error loading products for project {project_id}: {e}")
            return []
    
    def _load_labour_types_sync(self) -> List[Dict[str, str]]:
        """Load labour types from Google Sheets."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['labour_types'])
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Error loading labour types: {e}")
            return []
    
    def _load_paint_material_types_sync(self) -> List[Dict[str, str]]:
        """Load paint material types from Google Sheets."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['paint_material_types'])
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Error loading paint material types: {e}")
            return []
    
    def _load_paint_materials_sync(self, type_id: str) -> List[Dict[str, str]]:
        """Load paint materials for a specific type."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['paint_materials'])
            all_materials = worksheet.get_all_records()
            # Check for both 'type_id' and 'type' fields
            return [m for m in all_materials if str(m.get('type_id', m.get('type', ''))) == str(type_id)]
        except Exception as e:
            logger.error(f"Error loading paint materials for type {type_id}: {e}")
            return []
    
    def _load_material_types_sync(self) -> List[Dict[str, str]]:
        """Load material types from Google Sheets."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['material_types'])
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Error loading material types: {e}")
            return []
    
    def _load_materials_sync(self, type_id: str) -> List[Dict[str, str]]:
        """Load materials for a specific type."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['materials'])
            all_materials = worksheet.get_all_records()
            # Check for both 'type_id' and 'type' fields
            return [m for m in all_materials if str(m.get('type_id', m.get('type', ''))) == str(type_id)]
        except Exception as e:
            logger.error(f"Error loading materials for type {type_id}: {e}")
            return []
    
    def _load_employees_sync(self) -> List[Dict[str, str]]:
        """Load employees from Google Sheets."""
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['employees'])
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Error loading employees: {e}")
            return []
    
    async def get_projects(self) -> List[Dict[str, str]]:
        """Get list of active projects."""
        async with self._cache_lock:
            return [p for p in self._cache['projects'] if p.get('active', 'true').lower() == 'true']
    
    async def get_products(self, project_id: str) -> List[Dict[str, str]]:
        """Get list of products for a specific project."""
        async with self._cache_lock:
            # Convert project_id to string to ensure consistent lookup
            str_project_id = str(project_id)
            return self._cache['products'].get(str_project_id, [])
    
    async def get_labour_types(self) -> List[Dict[str, str]]:
        """Get list of labour types."""
        async with self._cache_lock:
            return self._cache['labour_types']
    
    async def get_paint_material_types(self) -> List[Dict[str, str]]:
        """Get list of paint material types."""
        async with self._cache_lock:
            return self._cache['paint_material_types']
    
    async def get_paint_materials(self, type_id: str) -> List[Dict[str, str]]:
        """Get list of paint materials for a specific type."""
        async with self._cache_lock:
            # Convert type_id to string to ensure consistent lookup
            str_type_id = str(type_id)
            return self._cache['paint_materials'].get(str_type_id, [])
    
    async def get_material_types(self) -> List[Dict[str, str]]:
        """Get list of material types."""
        async with self._cache_lock:
            return self._cache['material_types']
    
    async def get_materials(self, type_id: str) -> List[Dict[str, str]]:
        """Get list of materials for a specific type."""
        async with self._cache_lock:
            # Convert type_id to string to ensure consistent lookup
            str_type_id = str(type_id)
            return self._cache['materials'].get(str_type_id, [])
    
    async def get_employee(self, telegram_id: str) -> Optional[Dict[str, str]]:
        """Get employee by telegram_id and check if they are active."""
        async with self._cache_lock:
            # Try to get employee by telegram_id
            employee = self._cache['employees'].get(str(telegram_id))
            if employee:
                # Проверяем статус активности пользователя
                if employee.get('active', '').upper() == 'FALSE':
                    logger.info(f"User {telegram_id} found but is inactive")
                    return None
                return employee
                
            # If not found, try to find by id if it's different from telegram_id
            for emp_id, emp_data in self._cache['employees'].items():
                if str(emp_data.get('id', '')) == str(telegram_id):
                    # Проверяем статус активности пользователя
                    if emp_data.get('active', '').upper() == 'FALSE':
                        logger.info(f"User {telegram_id} found but is inactive")
                        return None
                    return emp_data
                    
            return None
    
    async def append_report(self, report_data: Dict[str, Any]) -> bool:
        """Append a report to the Reports sheet."""
        try:
            worksheet = self.reports_sheet.worksheet(config['sheet_names']['reports'])
            worksheet.append_row([
                report_data.get('timestamp', ''),
                report_data.get('employee_id', ''),
                report_data.get('employee_name', ''),
                report_data.get('project_id', ''),
                report_data.get('project_name', ''),
                report_data.get('product_id', ''),
                report_data.get('product_name', ''),
                CATEGORY_TRANSLATIONS.get(report_data.get('category', ''), report_data.get('category', '')),  # Используем русское название категории
                report_data.get('type_name', ''),  # Add type_name between category and subcategory
                report_data.get('subcategory_name', report_data.get('subcategory', '')),  # Используем subcategory_name вместо subcategory
                report_data.get('quantity', ''),
                report_data.get('unit', ''),
                report_data.get('comment', '')
            ])
            logger.info(f"Report added for employee {report_data.get('employee_name')}")
            return True
        except Exception as e:
            logger.error(f"Error appending report: {e}")
            return False
    
    async def append_multiple_reports(self, reports_data: List[Dict[str, Any]]) -> bool:
        """Append multiple reports to the Reports sheet."""
        try:
            if not reports_data:
                return True
                
            worksheet = self.reports_sheet.worksheet(config['sheet_names']['reports'])
            rows = []
            
            for report in reports_data:
                rows.append([
                    report.get('timestamp', ''),
                    report.get('employee_id', ''),
                    report.get('employee_name', ''),
                    report.get('project_id', ''),
                    report.get('project_name', ''),
                    report.get('product_id', ''),
                    report.get('product_name', ''),
                    CATEGORY_TRANSLATIONS.get(report.get('category', ''), report.get('category', '')),  # Используем русское название категории
                    report.get('type_name', ''),  # Add type_name between category and subcategory
                    report.get('subcategory_name', report.get('subcategory', '')),  # Используем subcategory_name вместо subcategory
                    report.get('quantity', ''),
                    report.get('unit', ''),
                    report.get('comment', '')
                ])
            
            worksheet.append_rows(rows)
            logger.info(f"Added {len(rows)} reports")
            return True
        except Exception as e:
            logger.error(f"Error appending multiple reports: {e}")
            return False
    
    async def get_last_employee_report(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get the last report for a specific employee."""
        try:
            employee = await self.get_employee(telegram_id)
            if not employee:
                return None
                
            worksheet = self.reports_sheet.worksheet(config['sheet_names']['reports'])
            all_reports = worksheet.get_all_records()
            
            # Filter reports for this employee and sort by timestamp (descending)
            # Try different field names for employee_id in reports and employee data
            employee_reports = []
            for report in all_reports:
                report_emp_id = report.get('employee_id', report.get('telegram_id', ''))
                emp_id = employee.get('id', employee.get('telegram_id', ''))
                if str(report_emp_id) == str(emp_id):
                    employee_reports.append(report)
            if not employee_reports:
                return None
                
            # Sort by timestamp (assuming ISO format)
            employee_reports.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
            return employee_reports[0] if employee_reports else None
            
        except Exception as e:
            logger.error(f"Error getting last employee report: {e}")
            return None
            
    async def register_user(self, telegram_id: str, name: str) -> bool:
        """
        Register a new user in the employees sheet.
        
        Args:
            telegram_id: User's Telegram ID
            name: User's full name
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            worksheet = self.reference_sheet.worksheet(config['sheet_names']['employees'])
            
            # Check if user already exists
            all_employees = worksheet.get_all_records()
            for emp in all_employees:
                emp_id = emp.get('telegram_id', emp.get('id', emp.get('tg_id', '')))
                if str(emp_id) == str(telegram_id):
                    logger.warning(f"User with Telegram ID {telegram_id} already exists")
                    return False
            
            # Add new user
            new_row = [telegram_id, name, 'user', 'true']
            worksheet.append_row(new_row)
            
            # Update cache
            async with self._cache_lock:
                if 'employees' not in self._cache:
                    self._cache['employees'] = {}
                self._cache['employees'][str(telegram_id)] = {
                    'telegram_id': telegram_id,
                    'name': name,
                    'role': 'user',
                    'active': 'true'
                }
                
            logger.info(f"Registered new user: {name} (ID: {telegram_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
    
    async def save_report(self, report_data: Dict[str, Any]) -> bool:
        """
        Save a complete report with multiple actions to the Reports sheet.
        
        Args:
            report_data: Dictionary containing report data including actions list
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not report_data or not report_data.get('actions'):
                logger.warning("Attempted to save empty report")
                return False
                
            # Extract common report data
            timestamp = report_data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            employee_id = report_data.get('employee_id', '')
            employee_name = report_data.get('employee_name', '')
            project_id = report_data.get('project_id', '')
            project_name = report_data.get('project_name', '')
            product_id = report_data.get('product_id', '')
            product_name = report_data.get('product_name', '')
            
            # Prepare rows for each action
            rows = []
            for action in report_data.get('actions', []):
                rows.append([
                    timestamp,
                    employee_id,
                    employee_name,
                    project_id,
                    project_name,
                    product_id,
                    product_name,
                    CATEGORY_TRANSLATIONS.get(action.get('category', ''), action.get('category', '')),  # Используем русское название категории
                    # Колонка I (subcategory):
                    # - для Работы всегда "Трудозатраты"
                    # - для ЛКМ и Плита - тип материала из PaintMaterialTypes/MaterialTypes (subcategory)
                    # - для остальных - type_name
                    "Трудозатраты" if action.get('category') == 'Работы' else action.get('subcategory') if action.get('category') in ['ЛКМ', 'Плита'] else action.get('type_name', ''),
                    # Колонка J (name) - для всех категорий используем subcategory_name
                    action.get('subcategory_name', action.get('subcategory', '')),
                    action.get('quantity', ''),
                    action.get('unit', ''),
                    action.get('comment', '')
                ])
            
            # Append all rows at once for efficiency
            if rows:
                worksheet = self.reports_sheet.worksheet(config['sheet_names']['reports'])
                worksheet.append_rows(rows)
                logger.info(f"Saved report with {len(rows)} actions for employee {employee_name}")
                return True
            else:
                logger.warning("No actions to save in report")
                return False
                
        except Exception as e:
            logger.error(f"Error saving report: {e}", exc_info=True)
            return False
