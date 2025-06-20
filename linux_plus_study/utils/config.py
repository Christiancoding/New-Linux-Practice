#!/usr/bin/env python3
"""
Configuration settings for Linux+ Study Application

This module contains all configuration constants, database settings,
and application parameters used throughout the application.
"""

import sys
import os
from pathlib import Path

# =============================================================================
# BASE PATHS
# =============================================================================

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
UTILS_DIR = PROJECT_ROOT / "utils"

# =============================================================================
# FILE PATHS (Current JSON-based system)
# =============================================================================

# Data files (backward compatibility with existing system)
QUESTIONS_FILE = DATA_DIR / "questions.json"
ACHIEVEMENTS_FILE = PROJECT_ROOT / "linux_plus_achievements.json"
HISTORY_FILE = PROJECT_ROOT / "linux_plus_history.json"
WEB_SETTINGS_FILE = PROJECT_ROOT / "web_settings.json"

# Legacy file constants (for compatibility)
HISTORY_FILE_LEGACY = "linux_plus_history.json"
ACHIEVEMENTS_FILE_LEGACY = "linux_plus_achievements.json"

# =============================================================================
# APPLICATION MODES AND CONSTANTS
# =============================================================================

# Application modes (GUI mode removed)
SUPPORTED_MODES = ["cli", "web"]
DEFAULT_MODE = "cli"

# Quiz Mode Constants
QUIZ_MODE_STANDARD = "standard"
QUIZ_MODE_VERIFY = "verify"

# Gamification Constants
POINTS_PER_CORRECT = 10
POINTS_PER_INCORRECT = -2
STREAK_BONUS_THRESHOLD = 3
STREAK_BONUS_MULTIPLIER = 1.5

# Quick Fire Mode Constants
QUICK_FIRE_QUESTIONS = 5
QUICK_FIRE_TIME_LIMIT = 180  # 3 minutes in seconds

# Mini Quiz Constants
MINI_QUIZ_QUESTIONS = 3
MINI_QUIZ_TIME_LIMIT = 30  # 30 seconds

# =============================================================================
# CLI COLOR CONFIGURATION (COLORAMA)
# =============================================================================

# --- Colorama Setup (CLI Colors) ---
try:
    import colorama
    colorama.init(autoreset=True)
    
    # Define a richer color palette using colorama styles
    C = {
        "reset": colorama.Style.RESET_ALL,
        "bold": colorama.Style.BRIGHT,
        "dim": colorama.Style.DIM,
        # Foreground Colors
        "fg_black": colorama.Fore.BLACK,
        "fg_red": colorama.Fore.RED,
        "fg_green": colorama.Fore.GREEN,
        "fg_yellow": colorama.Fore.YELLOW,
        "fg_blue": colorama.Fore.BLUE,
        "fg_magenta": colorama.Fore.MAGENTA,
        "fg_cyan": colorama.Fore.CYAN,
        "fg_white": colorama.Fore.WHITE,
        "fg_lightblack_ex": colorama.Fore.LIGHTBLACK_EX,
        # Bright Foreground Colors
        "fg_bright_red": colorama.Fore.LIGHTRED_EX,
        "fg_bright_green": colorama.Fore.LIGHTGREEN_EX,
        "fg_bright_yellow": colorama.Fore.LIGHTYELLOW_EX,
        "fg_bright_blue": colorama.Fore.LIGHTBLUE_EX,
        "fg_bright_magenta": colorama.Fore.LIGHTMAGENTA_EX,
        "fg_bright_cyan": colorama.Fore.LIGHTCYAN_EX,
        "fg_bright_white": colorama.Fore.LIGHTWHITE_EX,
        # Background Colors
        "bg_red": colorama.Back.RED,
        "bg_green": colorama.Back.GREEN,
        "bg_yellow": colorama.Back.YELLOW,
        "bg_blue": colorama.Back.BLUE,
        "bg_magenta": colorama.Back.MAGENTA,
        "bg_cyan": colorama.Back.CYAN,
        "bg_white": colorama.Back.WHITE,
    }
    
    # Define semantic colors using the palette
    COLOR_QUESTION = C["fg_bright_cyan"] + C["bold"]
    COLOR_OPTIONS = C["fg_white"]
    COLOR_OPTION_NUM = C["fg_yellow"] + C["bold"]
    COLOR_CATEGORY = C["fg_bright_yellow"] + C["bold"]
    COLOR_CORRECT = C["fg_bright_green"] + C["bold"]
    COLOR_INCORRECT = C["fg_bright_red"] + C["bold"]
    COLOR_EXPLANATION = C["fg_lightblack_ex"]
    COLOR_PROMPT = C["fg_bright_magenta"] + C["bold"]
    COLOR_HEADER = C["fg_bright_blue"] + C["bold"]
    COLOR_SUBHEADER = C["fg_blue"] + C["bold"]
    COLOR_STATS_LABEL = C["fg_white"]
    COLOR_STATS_VALUE = C["fg_bright_yellow"]
    COLOR_STATS_ACC_GOOD = C["fg_bright_green"]
    COLOR_STATS_ACC_AVG = C["fg_yellow"]
    COLOR_STATS_ACC_BAD = C["fg_bright_red"]
    COLOR_BORDER = C["fg_blue"]
    COLOR_INPUT = C["fg_bright_white"]
    COLOR_ERROR = C["fg_white"] + C["bg_red"] + C["bold"]
    COLOR_WARNING = C["fg_bright_yellow"] + C["bold"]
    COLOR_INFO = C["fg_bright_cyan"]
    COLOR_WELCOME_BORDER = C["fg_bright_yellow"] + C["bold"]
    COLOR_WELCOME_TEXT = C["fg_white"]
    COLOR_WELCOME_TITLE = C["fg_bright_yellow"] + C["bold"]
    COLOR_RESET = C["reset"]
    
except ImportError:
    print("Warning: Colorama not found. Colored output will be disabled in CLI.")
    # Define empty strings if colorama is not available
    C = {k: "" for k in ["reset", "bold", "dim", "fg_black", "fg_red", "fg_green", 
         "fg_yellow", "fg_blue", "fg_magenta", "fg_cyan", "fg_white", "fg_lightblack_ex", 
         "fg_bright_red", "fg_bright_green", "fg_bright_yellow", "fg_bright_blue", 
         "fg_bright_magenta", "fg_bright_cyan", "fg_bright_white", "bg_red", "bg_green", 
         "bg_yellow", "bg_blue", "bg_magenta", "bg_cyan", "bg_white"]}
    
    COLOR_QUESTION, COLOR_OPTIONS, COLOR_OPTION_NUM, COLOR_CATEGORY = "", "", "", ""
    COLOR_CORRECT, COLOR_INCORRECT, COLOR_EXPLANATION, COLOR_PROMPT = "", "", "", ""
    COLOR_HEADER, COLOR_SUBHEADER, COLOR_STATS_LABEL, COLOR_STATS_VALUE = "", "", "", ""
    COLOR_STATS_ACC_GOOD, COLOR_STATS_ACC_AVG, COLOR_STATS_ACC_BAD = "", "", ""
    COLOR_BORDER, COLOR_INPUT, COLOR_ERROR, COLOR_WARNING, COLOR_INFO = "", "", "", "", ""
    COLOR_WELCOME_BORDER, COLOR_WELCOME_TEXT, COLOR_WELCOME_TITLE = "", "", ""
    COLOR_RESET = ""

# =============================================================================
# SAMPLE QUESTIONS DATA
# =============================================================================

# --- Sample Questions Data ---
SAMPLE_QUESTIONS = [
    (
        "Which command installs the GRUB2 bootloader to a specified device?",
        ["grub2-mkconfig", "grub2-install", "update-grub", "dracut"],
        1, "Commands (System Management)",
        "`grub2-install` installs the GRUB2 bootloader files to the appropriate location and typically installs the boot code to the MBR or EFI partition. Example: `grub2-install /dev/sda` (for BIOS systems) or `grub2-install --target=x86_64-efi --efi-directory=/boot/efi` (for UEFI systems)."
    )
]

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database URLs
SQLITE_URL = f"sqlite:///{PROJECT_ROOT}/linux_plus_study.db"
POSTGRESQL_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://username:password@localhost:5432/linux_plus_study"
)

# Database settings
DATABASE_CONFIG = {
    "SQLALCHEMY_DATABASE_URI": SQLITE_URL,  # Default to SQLite
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": {"check_same_thread": False} if "sqlite" in SQLITE_URL else {}
    }
}

# Connection pool settings
CONNECTION_POOL_CONFIG = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600
}

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# Application metadata
APP_NAME = "Linux+ Study Assistant"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Comprehensive Linux+ certification study tool"

# CLI Configuration Settings
CLI_SETTINGS = {
    "welcome_message": "Welcome to Linux Plus Study Tool",
    "prompt_symbol": ">>> ",
    "clear_screen": True,
    "show_progress_bar": True,
    "colored_output": True,
    "max_menu_options": 10,
    "input_timeout": 300,  # 5 minutes
}

# Web Configuration Settings (Enhanced)
WEB_SETTINGS = {
    "default_host": "127.0.0.1",
    "default_port": 5000,
    "debug_mode": False,
    "threaded": True,
    "template_auto_reload": True,
    "session_timeout": 3600,  # 1 hour
    "max_content_length": 16 * 1024 * 1024,  # 16MB
}

# Quiz Configuration (Enhanced)
QUIZ_SETTINGS = {
    "default_question_count": 10,
    "max_question_count": 50,
    "min_question_count": 1,
    "shuffle_questions": True,
    "shuffle_options": True,
    "show_immediate_feedback": True,
    "allow_review": True,
}

# Default quiz settings (for backward compatibility)
DEFAULT_QUIZ_CONFIG = {
    "questions_per_quiz": QUIZ_SETTINGS["default_question_count"],
    "time_limit_minutes": None,  # No time limit by default
    "shuffle_questions": QUIZ_SETTINGS["shuffle_questions"],
    "shuffle_options": QUIZ_SETTINGS["shuffle_options"],
    "show_immediate_feedback": QUIZ_SETTINGS["show_immediate_feedback"],
    "allow_review": QUIZ_SETTINGS["allow_review"]
}

# Quick fire mode settings (Enhanced)
QUICK_FIRE_CONFIG = {
    "default_duration_seconds": QUICK_FIRE_TIME_LIMIT,
    "questions_per_minute": 2,
    "bonus_points_multiplier": STREAK_BONUS_MULTIPLIER,
    "quick_fire_questions": QUICK_FIRE_QUESTIONS,
    "mini_quiz_questions": MINI_QUIZ_QUESTIONS,
    "mini_quiz_time_limit": MINI_QUIZ_TIME_LIMIT
}

# Achievement settings (Enhanced)
ACHIEVEMENT_SETTINGS = {
    "points_per_correct": POINTS_PER_CORRECT,
    "bonus_streak_multiplier": STREAK_BONUS_MULTIPLIER,
    "streak_threshold": 5,
    "daily_challenge_bonus": 50,
    "perfect_quiz_bonus": 25,
}

ACHIEVEMENT_CONFIG = {
    "points_per_correct": ACHIEVEMENT_SETTINGS["points_per_correct"],
    "bonus_points_streak": 5,
    "daily_challenge_bonus": ACHIEVEMENT_SETTINGS["daily_challenge_bonus"],
    "achievement_unlock_sound": True
}

# Scoring and Statistics
SCORING_SETTINGS = {
    "passing_percentage": 70,
    "excellent_percentage": 90,
    "streak_bonus_threshold": 10,
    "leaderboard_max_entries": 100,
}

# =============================================================================
# WEB FRAMEWORK SETTINGS
# =============================================================================

# Flask/FastAPI settings (Enhanced)
WEB_CONFIG = {
    "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
    "DEBUG": WEB_SETTINGS["debug_mode"],
    "HOST": WEB_SETTINGS["default_host"],
    "PORT": WEB_SETTINGS["default_port"],
    "THREADED": WEB_SETTINGS["threaded"]
}

# Session configuration (Enhanced)
SESSION_CONFIG = {
    "SESSION_TYPE": "filesystem",
    "SESSION_PERMANENT": False,
    "SESSION_USE_SIGNER": True,
    "SESSION_KEY_PREFIX": "linux_plus_study:",
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SECURE": False,  # Set to True in production with HTTPS
    "SESSION_COOKIE_SAMESITE": "Lax",
    "session_timeout": WEB_SETTINGS["session_timeout"]
}

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# Authentication settings
AUTH_CONFIG = {
    "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production"),
    "JWT_ACCESS_TOKEN_EXPIRES": 3600,  # 1 hour
    "JWT_REFRESH_TOKEN_EXPIRES": 2592000,  # 30 days
    "PASSWORD_MIN_LENGTH": 8,
    "REQUIRE_EMAIL_VERIFICATION": False,
    "RATE_LIMIT_PER_MINUTE": 60
}

# CORS settings
CORS_CONFIG = {
    "CORS_ORIGINS": ["http://localhost:3000", "http://127.0.0.1:3000"],
    "CORS_METHODS": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "CORS_ALLOW_HEADERS": ["Content-Type", "Authorization"]
}

# =============================================================================
# CACHING CONFIGURATION
# =============================================================================

# Redis settings
REDIS_CONFIG = {
    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    "CACHE_TYPE": "redis",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "linux_plus_study:"
}

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Enable/disable features for gradual rollout
FEATURE_FLAGS = {
    "USE_DATABASE": os.getenv("USE_DATABASE", "False").lower() == "true",
    "ENABLE_SPACED_REPETITION": True,
    "ENABLE_ADAPTIVE_LEARNING": False,
    "ENABLE_SOCIAL_FEATURES": False,
    "ENABLE_API": True,
    "ENABLE_WEBSOCKETS": False,
    "ENABLE_OFFLINE_MODE": False,
    "ENABLE_VOICE_COMMANDS": False
}

# =============================================================================
# LEARNING ALGORITHM SETTINGS
# =============================================================================

# Spaced Repetition System settings
SRS_CONFIG = {
    "initial_interval": 1,  # days
    "max_interval": 365,    # days
    "ease_factor": 2.5,
    "minimum_ease": 1.3,
    "ease_bonus": 0.15,
    "ease_penalty": 0.2
}

# Adaptive learning settings
ADAPTIVE_CONFIG = {
    "difficulty_adjustment_factor": 0.1,
    "performance_window": 10,  # questions
    "min_difficulty": 0.1,
    "max_difficulty": 1.0
}

# =============================================================================
# NOTIFICATION SETTINGS
# =============================================================================

# Email settings
EMAIL_CONFIG = {
    "MAIL_SERVER": os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    "MAIL_PORT": int(os.getenv("MAIL_PORT", "587")),
    "MAIL_USE_TLS": True,
    "MAIL_USERNAME": os.getenv("MAIL_USERNAME"),
    "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD"),
    "MAIL_DEFAULT_SENDER": os.getenv("MAIL_DEFAULT_SENDER", "noreply@linuxplustudy.com")
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging Settings (Enhanced)
LOGGING_SETTINGS = {
    "log_level": "INFO",
    "log_file": PROJECT_ROOT / "app.log",
    "max_log_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": LOGGING_SETTINGS["format"]
        },
    },
    "handlers": {
        "default": {
            "level": LOGGING_SETTINGS["log_level"],
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": str(LOGGING_SETTINGS["log_file"]),
            "mode": "a",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default", "file"],
            "level": "DEBUG",
            "propagate": False
        }
    }
}

# =============================================================================
# CATEGORIES AND DIFFICULTY LEVELS
# =============================================================================

# Question categories based on Linux+ certification domains (Enhanced)
QUESTION_CATEGORIES = [
    "Hardware and System Configuration",
    "Systems Operation and Maintenance", 
    "Security",
    "Linux Troubleshooting and Diagnostics",
    "Automation and Scripting",
    # Additional technical categories
    "hardware",
    "system_architecture", 
    "gnu_linux_installation",
    "package_management",
    "command_line",
    "file_systems",
    "boot_process",
    "runlevels",
    "text_processing",
    "user_management",
    "networking",
    "shell_scripting",
    "system_maintenance"
]

# Difficulty levels
DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"]

# =============================================================================
# USER INTERFACE AND MESSAGES
# =============================================================================

# File validation settings
FILE_VALIDATION = {
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "allowed_extensions": [".json", ".txt", ".csv"],
    "encoding": "utf-8",
}

# Error Messages
ERROR_MESSAGES = {
    "file_not_found": "Required file not found: {filename}",
    "invalid_mode": "Invalid mode. Supported modes: {modes}",
    "no_questions": "No questions available for the selected category",
    "invalid_answer": "Invalid answer format. Please try again.",
    "network_error": "Network connection error. Please check your connection.",
    "permission_error": "Permission denied. Check file permissions.",
}

# Success Messages  
SUCCESS_MESSAGES = {
    "quiz_completed": "Quiz completed successfully!",
    "achievement_unlocked": "Achievement unlocked: {achievement}",
    "stats_cleared": "Statistics cleared successfully",
    "file_saved": "File saved successfully: {filename}",
}

# User Interface Constants
UI_CONSTANTS = {
    "page_title": "Linux Plus Study Tool",
    "app_version": APP_VERSION,
    "copyright": "© 2024 Linux Plus Study Tool",
    "support_email": "support@linuxplus.example.com",
}

# Performance Settings
PERFORMANCE_SETTINGS = {
    "cache_questions": True,
    "cache_timeout": 3600,  # 1 hour
    "lazy_loading": True,
    "pagination_size": 20,
}

# =============================================================================
# API CONFIGURATION
# =============================================================================

# API versioning (Enhanced)
API_CONFIG = {
    "API_PREFIX": "/api",
    "API_VERSION": "v1",
    "API_TITLE": "Linux+ Study API",
    "API_DESCRIPTION": "RESTful API for Linux+ certification study tool",
    "API_VERSION_HEADER": "X-API-Version"
}

# API Settings (Enhanced)  
API_SETTINGS = {
    "version": API_CONFIG["API_VERSION"],
    "rate_limit": 100,  # requests per minute
    "cors_enabled": False,
    "authentication_required": False,
}

# Rate limiting (Enhanced)
RATE_LIMIT_CONFIG = {
    "DEFAULT_RATE_LIMIT": "100 per hour",
    "AUTH_RATE_LIMIT": "10 per minute",
    "QUIZ_RATE_LIMIT": "30 per hour",
    "REGISTRATION_RATE_LIMIT": "5 per hour"
}

# =============================================================================
# DEVELOPMENT/TESTING SETTINGS
# =============================================================================

# Development and Debug Settings (Enhanced)
DEBUG_SETTINGS = {
    "verbose_logging": False,
    "show_sql_queries": False,
    "profile_performance": False,
    "mock_data": False,
}

# Testing configuration (Enhanced)
TEST_CONFIG = {
    "TESTING": True,
    "WTF_CSRF_ENABLED": False,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "SERVER_NAME": "localhost.localdomain"
}

# Development settings (Enhanced)
DEV_CONFIG = {
    "FLASK_ENV": "development",
    "FLASK_DEBUG": True,
    "TEMPLATES_AUTO_RELOAD": WEB_SETTINGS["template_auto_reload"],
    "SEND_FILE_MAX_AGE_DEFAULT": 0
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_database_url():
    """Get the appropriate database URL based on environment"""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    elif FEATURE_FLAGS["USE_DATABASE"]:
        return POSTGRESQL_URL
    else:
        return SQLITE_URL

def is_production():
    """Check if running in production environment"""
    return os.getenv("FLASK_ENV") == "production"

def get_config_for_environment():
    """Get configuration based on current environment"""
    if os.getenv("TESTING"):
        return TEST_CONFIG
    elif is_production():
        return {**WEB_CONFIG, "DEBUG": False, "SECRET_KEY": os.getenv("SECRET_KEY")}
    else:
        return {**WEB_CONFIG, **DEV_CONFIG}

def get_config_value(section, key, default=None):
    """
    Retrieve a configuration value from the specified section.
    
    Args:
        section (str): Configuration section name
        key (str): Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    config_sections = {
        "cli": CLI_SETTINGS,
        "web": WEB_SETTINGS,
        "quiz": QUIZ_SETTINGS,
        "achievements": ACHIEVEMENT_SETTINGS,
        "scoring": SCORING_SETTINGS,
        "logging": LOGGING_SETTINGS,
        "debug": DEBUG_SETTINGS,
        "api": API_SETTINGS,
        "ui": UI_CONSTANTS,
        "performance": PERFORMANCE_SETTINGS,
    }
    
    section_config = config_sections.get(section, {})
    return section_config.get(key, default)

def validate_mode(mode):
    """
    Validate if the provided mode is supported.
    
    Args:
        mode (str): Application mode to validate
        
    Returns:
        bool: True if mode is supported, False otherwise
    """
    return mode in SUPPORTED_MODES

def get_file_path(file_type):
    """
    Get the full file path for a specific file type.
    
    Args:
        file_type (str): Type of file (questions, achievements, history, etc.)
        
    Returns:
        Path: Full path to the specified file
    """
    file_paths = {
        "questions": QUESTIONS_FILE,
        "achievements": ACHIEVEMENTS_FILE,
        "history": HISTORY_FILE,
        "web_settings": WEB_SETTINGS_FILE,
    }
    
    return file_paths.get(file_type)

def ensure_directories():
    """
    Ensure all required directories exist.
    Create them if they don't exist.
    """
    directories = [
        DATA_DIR,
        TEMPLATES_DIR,
        STATIC_DIR,
        STATIC_DIR / "css",
        STATIC_DIR / "js",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """Validate critical configuration settings"""
    errors = []
    
    if is_production():
        if WEB_CONFIG["SECRET_KEY"] == "dev-secret-key-change-in-production":
            errors.append("SECRET_KEY must be changed in production")
        
        if AUTH_CONFIG["JWT_SECRET_KEY"] == "jwt-secret-key-change-in-production":
            errors.append("JWT_SECRET_KEY must be changed in production")
    
    # Validate file paths exist
    if not FEATURE_FLAGS["USE_DATABASE"]:
        DATA_DIR.mkdir(exist_ok=True)
        if not QUESTIONS_FILE.exists():
            errors.append(f"Questions file not found: {QUESTIONS_FILE}")
    
    return errors

# =============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# =============================================================================

# Environment-specific overrides (Enhanced)
if os.getenv("FLASK_ENV") == "development":
    WEB_SETTINGS["debug_mode"] = True
    WEB_CONFIG["DEBUG"] = True
    DEBUG_SETTINGS["verbose_logging"] = True

if os.getenv("PRODUCTION") == "true":
    WEB_SETTINGS["debug_mode"] = False
    WEB_CONFIG["DEBUG"] = False
    DEBUG_SETTINGS["verbose_logging"] = False
    LOGGING_SETTINGS["log_level"] = "WARNING"

# Auto-validate configuration on import
if __name__ != "__main__":
    config_errors = validate_config()
    if config_errors:
        import warnings
        for error in config_errors:
            warnings.warn(f"Configuration warning: {error}")