"""
Conversation states for Vibe Work Bot.
"""
from enum import IntEnum, auto

class ConversationState(IntEnum):
    """States for the conversation handler."""
    START = auto()
    
    # Registration states
    REGISTRATION_START = auto()
    ENTERING_CODE = auto()  # Добавлено состояние для ввода кодового слова
    ENTERING_NAME = auto()
    REGISTRATION_CONFIRM = auto()
    
    CHOOSING_PROJECT = auto()
    CHOOSING_PRODUCT = auto()
    CHOOSING_CATEGORY = auto()
    
    # Labour category states
    CHOOSING_LABOUR_TYPE = auto()
    ENTERING_HOURS = auto()
    
    # Paint category states
    CHOOSING_PAINT_TYPE = auto()
    CHOOSING_PAINT_MATERIAL = auto()
    ENTERING_PAINT_QUANTITY = auto()
    
    # Materials category states
    CHOOSING_MATERIAL_TYPE = auto()
    CHOOSING_MATERIAL = auto()
    ENTERING_MATERIAL_QUANTITY = auto()
    
    # Common states
    ENTERING_COMMENT = auto()
    CONFIRM_ACTION = auto()
    ADD_ANOTHER_ACTION = auto()
    CONFIRM_REPORT = auto()
    STARTING_REPORT = auto()
    REPORT_COMPLETED = auto()
    
    # End state
    END = auto()

# Category types
CATEGORY_LABOUR = "Работы"
CATEGORY_PAINT = "ЛКМ"
CATEGORY_MATERIALS = "Плита"
CATEGORY_DEFECT = "Брак"

# Callback data prefixes
CALLBACK_PROJECT_PREFIX = "project:"
CALLBACK_PRODUCT_PREFIX = "product:"
CALLBACK_CATEGORY_PREFIX = "category:"
CALLBACK_LABOUR_TYPE_PREFIX = "labour_type:"
CALLBACK_PAINT_TYPE_PREFIX = "paint_type:"
CALLBACK_PAINT_MATERIAL_PREFIX = "paint_material:"
CALLBACK_MATERIAL_TYPE_PREFIX = "material_type:"
CALLBACK_MATERIAL_PREFIX = "material:"
CALLBACK_NEW_REPORT = "new_report"
CALLBACK_BACK = "back"
CALLBACK_SKIP = "skip"
CALLBACK_CONFIRM = "confirm"
CALLBACK_ADD_MORE = "add_more"
CALLBACK_FINISH = "finish"
CALLBACK_SEND_REPORT = "send_report"
CALLBACK_ADD_COMMENT = "add_comment"
