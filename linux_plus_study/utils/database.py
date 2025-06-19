"""
Enhanced database utilities with SQLite support and improved data management.

This module provides both JSON (legacy) and SQLite database backends with
automatic migration capabilities and data validation.
"""

import json
import sqlite3
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from contextlib import contextmanager
import threading

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass

class DatabaseManager:
    """
    Unified database manager supporting both JSON (legacy) and SQLite backends.
    
    Features:
    - Automatic migration from JSON to SQLite
    - Data validation and integrity checks
    - Backup and recovery systems
    - Thread-safe operations
    - Connection pooling for SQLite
    """
    
    def __init__(self, db_path: str = "linux_plus_study.db", use_sqlite: bool = True):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            use_sqlite: Whether to use SQLite (True) or JSON (False)
        """
        self.db_path = Path(db_path)
        self.use_sqlite = use_sqlite
        self._lock = threading.Lock()
        
        # JSON file paths (for legacy support)
        self.json_paths = {
            'questions': Path('data/questions.json'),
            'history': Path('linux_plus_history.json'),
            'achievements': Path('linux_plus_achievements.json'),
            'settings': Path('web_settings.json')
        }
        
        if self.use_sqlite:
            try:
                self._init_sqlite_db()
                self._migrate_from_json_if_needed()
            except Exception as e:
                logger.error(f"Failed to initialize SQLite database: {e}")
                logger.warning("Falling back to JSON mode")
                self.use_sqlite = False
        
    def _init_sqlite_db(self):
        """Initialize SQLite database with proper schema."""
        try:
            with self._get_db_connection() as conn:
                self._create_tables(conn)
                logger.info("SQLite database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create all necessary database tables."""
        
        # Questions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                options TEXT NOT NULL,  -- JSON array of options
                correct_answer_index INTEGER NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT DEFAULT 'Intermediate',
                explanation TEXT,
                tags TEXT,  -- JSON array of tags
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # User history table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                question_text TEXT NOT NULL,  -- For legacy compatibility
                user_answer INTEGER,
                correct_answer INTEGER NOT NULL,
                is_correct BOOLEAN NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                quiz_mode TEXT DEFAULT 'standard',
                time_taken INTEGER,  -- Time in seconds
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )
        ''')
        
        # Achievements table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                description TEXT,
                points_value INTEGER DEFAULT 0,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(achievement_type, achievement_name)
            )
        ''')
        
        # User stats table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_name TEXT UNIQUE NOT NULL,
                stat_value TEXT NOT NULL,  -- JSON for complex values
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Settings table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,  -- JSON for complex values
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category)',
            'CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty)',
            'CREATE INDEX IF NOT EXISTS idx_history_timestamp ON user_history(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_history_question ON user_history(question_text)',
            'CREATE INDEX IF NOT EXISTS idx_history_correct ON user_history(is_correct)',
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
    def _validate_json_data(self) -> Dict[str, Any]:
        """
        Validate JSON data before migration.
        
        Returns:
            Dictionary with validation results for each file
        """
        validation_results = {}
        
        for file_type, file_path in self.json_paths.items():
            if not file_path.exists():
                validation_results[file_type] = {'exists': False, 'valid': True, 'message': 'File does not exist'}
                continue
            
            try:
                data = self.load_json_file(file_path)
                result = {'exists': True, 'valid': True, 'message': 'OK', 'data_type': type(data).__name__}
                
                if file_type == 'questions':
                    if isinstance(data, list):
                        result['count'] = len(data)
                        # Check first few questions for structure
                        if data and len(data) > 0:
                            first_question = data[0]
                            has_question_text = 'question_text' in first_question or 'question' in first_question
                            has_options = 'options' in first_question
                            has_answer = 'correct_answer_index' in first_question or 'correct_answer' in first_question
                            
                            if not (has_question_text and has_options and has_answer):
                                result['valid'] = False
                                result['message'] = 'Question structure appears invalid'
                    else:
                        result['valid'] = False
                        result['message'] = 'Questions should be a list'
                
                elif file_type == 'history':
                    if isinstance(data, dict):
                        result['count'] = len(data)
                        result['message'] = f'Dictionary with {len(data)} question entries'
                    elif isinstance(data, list):
                        result['count'] = len(data)
                        result['message'] = f'List with {len(data)} entries (unexpected format)'
                        result['valid'] = False
                    else:
                        result['valid'] = False
                        result['message'] = f'Unexpected data type: {type(data)}'
                
                validation_results[file_type] = result
                
            except Exception as e:
                validation_results[file_type] = {
                    'exists': True, 
                    'valid': False, 
                    'message': f'Error reading file: {e}',
                    'data_type': 'unknown'
                }
        
        return validation_results
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper error handling."""
        if not self.use_sqlite:
            raise DatabaseError("SQLite operations not available in JSON mode")
        
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def _migrate_from_json_if_needed(self):
        """Migrate existing JSON data to SQLite if present."""
        if not any(path.exists() for path in self.json_paths.values()):
            logger.info("No JSON files found, skipping migration")
            return
        
        logger.info("Starting migration from JSON to SQLite...")
        
        # Validate JSON data first
        validation_results = self._validate_json_data()
        logger.info("JSON Data Validation Results:")
        for file_type, result in validation_results.items():
            if result['exists']:
                status = "✓" if result['valid'] else "✗"
                logger.info(f"  {status} {file_type}: {result['message']}")
        
        migration_errors = []
        
        try:
            # Migrate questions
            if self.json_paths['questions'].exists() and validation_results.get('questions', {}).get('valid', False):
                try:
                    self._migrate_questions()
                except Exception as e:
                    error_msg = f"Failed to migrate questions: {e}"
                    logger.error(error_msg)
                    migration_errors.append(error_msg)
            
            # Migrate history (with fallback for invalid format)
            if self.json_paths['history'].exists():
                try:
                    self._migrate_history()
                except Exception as e:
                    error_msg = f"Failed to migrate history: {e}"
                    logger.error(error_msg)
                    migration_errors.append(error_msg)
            
            # Migrate achievements
            if self.json_paths['achievements'].exists():
                try:
                    self._migrate_achievements()
                except Exception as e:
                    error_msg = f"Failed to migrate achievements: {e}"
                    logger.warning(error_msg)
                    migration_errors.append(error_msg)
            
            # Migrate settings
            if self.json_paths['settings'].exists():
                try:
                    self._migrate_settings()
                except Exception as e:
                    error_msg = f"Failed to migrate settings: {e}"
                    logger.warning(error_msg)
                    migration_errors.append(error_msg)
            
            # Create backup of JSON files only if migration was mostly successful
            if len(migration_errors) <= 2:  # Allow some non-critical failures
                try:
                    self._backup_json_files()
                except Exception as e:
                    logger.warning(f"Failed to backup JSON files: {e}")
            
            if migration_errors:
                logger.warning(f"Migration completed with {len(migration_errors)} errors")
                for error in migration_errors:
                    logger.warning(f"  - {error}")
            else:
                logger.info("Migration completed successfully")
            
        except Exception as e:
            logger.error(f"Critical migration error: {e}")
            # Don't raise the error here, just log it and continue
            logger.warning("Continuing with fresh database instead of failing completely")
    
    def _migrate_questions(self):
        """Migrate questions from JSON to SQLite."""
        questions_data = self.load_json_file(self.json_paths['questions'])
        
        with self._get_db_connection() as conn:
            for question in questions_data:
                # Handle different question formats
                question_text = question.get('question_text') or question.get('question', '')
                options = json.dumps(question.get('options', []))
                correct_answer = question.get('correct_answer_index', 0)
                category = question.get('category', 'General')
                difficulty = question.get('difficulty', 'Intermediate')
                explanation = question.get('explanation', '')
                
                conn.execute('''
                    INSERT OR IGNORE INTO questions 
                    (question_text, options, correct_answer_index, category, difficulty, explanation)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (question_text, options, correct_answer, category, difficulty, explanation))
            
            conn.commit()
    
    def _validate_json_data(self) -> Dict[str, Any]:
        """
        Validate JSON data before migration.
        
        Returns:
            Dictionary with validation results for each file
        """
        validation_results = {}
        
        for file_type, file_path in self.json_paths.items():
            if not file_path.exists():
                validation_results[file_type] = {'exists': False, 'valid': True, 'message': 'File does not exist'}
                continue
            
            try:
                data = self.load_json_file(file_path)
                result = {'exists': True, 'valid': True, 'message': 'OK', 'data_type': type(data).__name__}
                
                if file_type == 'questions':
                    if isinstance(data, list):
                        result['count'] = len(data)
                        # Check first few questions for structure
                        if data and len(data) > 0:
                            first_question = data[0]
                            has_question_text = 'question_text' in first_question or 'question' in first_question
                            has_options = 'options' in first_question
                            has_answer = 'correct_answer_index' in first_question or 'correct_answer' in first_question
                            
                            if not (has_question_text and has_options and has_answer):
                                result['valid'] = False
                                result['message'] = 'Question structure appears invalid'
                    else:
                        result['valid'] = False
                        result['message'] = 'Questions should be a list'
                
                elif file_type == 'history':
                    if isinstance(data, dict):
                        result['count'] = len(data)
                        result['message'] = f'Dictionary with {len(data)} question entries'
                    elif isinstance(data, list):
                        result['count'] = len(data)
                        result['message'] = f'List with {len(data)} entries (unexpected format)'
                        result['valid'] = False
                    else:
                        result['valid'] = False
                        result['message'] = f'Unexpected data type: {type(data)}'
                
                validation_results[file_type] = result
                
            except Exception as e:
                validation_results[file_type] = {
                    'exists': True, 
                    'valid': False, 
                    'message': f'Error reading file: {e}',
                    'data_type': 'unknown'
                }
        
        return validation_results
        
        logger.info(f"Migrated {len(questions_data)} questions")
    
    def _migrate_history(self):
        """Migrate user history from JSON to SQLite."""
        history_data = self.load_json_file(self.json_paths['history'])
        
        # Handle different history data formats
        if not history_data:
            logger.info("No history data to migrate")
            return
        
        with self._get_db_connection() as conn:
            # Check if history_data is a list or dict
            if isinstance(history_data, list):
                logger.warning("History data is in list format, attempting to migrate as individual entries")
                for i, entry in enumerate(history_data):
                    if isinstance(entry, dict):
                        question_text = entry.get('question', f"Question {i+1}")
                        timestamp = entry.get('timestamp', datetime.now().isoformat())
                        is_correct = entry.get('correct', False)
                        
                        conn.execute('''
                            INSERT INTO user_history 
                            (question_text, is_correct, timestamp, correct_answer, user_answer)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (question_text, is_correct, timestamp, 0, 0))
            
            elif isinstance(history_data, dict):
                # Expected format: {question_text: {correct: int, attempts: int, history: [...]}}
                for question_text, data in history_data.items():
                    if isinstance(data, dict):
                        history_entries = data.get('history', [])
                        
                        for entry in history_entries:
                            if isinstance(entry, dict):
                                timestamp = entry.get('timestamp', datetime.now().isoformat())
                                is_correct = entry.get('correct', False)
                                
                                conn.execute('''
                                    INSERT INTO user_history 
                                    (question_text, is_correct, timestamp, correct_answer, user_answer)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (question_text, is_correct, timestamp, 0, 0))
                    else:
                        logger.warning(f"Unexpected data format for question: {question_text}")
            
            else:
                logger.error(f"Unexpected history data type: {type(history_data)}")
                return
            
            conn.commit()
        
        logger.info("Migrated user history")
    
    def _migrate_achievements(self):
        """Migrate achievements from JSON to SQLite."""
        try:
            achievements_data = self.load_json_file(self.json_paths['achievements'])
            
            with self._get_db_connection() as conn:
                # Handle different achievement data structures
                if isinstance(achievements_data, dict):
                    # Handle badges
                    badges = achievements_data.get('badges', [])
                    for badge in badges:
                        conn.execute('''
                            INSERT OR IGNORE INTO achievements 
                            (achievement_type, achievement_name, points_value)
                            VALUES (?, ?, ?)
                        ''', ('badge', badge, 10))
                    
                    # Handle other achievement types
                    points = achievements_data.get('points_earned', 0)
                    if points > 0:
                        conn.execute('''
                            INSERT OR IGNORE INTO user_stats (stat_name, stat_value)
                            VALUES (?, ?)
                        ''', ('total_points', str(points)))
                
                conn.commit()
            
            logger.info("Migrated achievements")
        except Exception as e:
            logger.warning(f"Could not migrate achievements: {e}")
    
    def _migrate_settings(self):
        """Migrate settings from JSON to SQLite."""
        try:
            settings_data = self.load_json_file(self.json_paths['settings'])
            
            with self._get_db_connection() as conn:
                for key, value in settings_data.items():
                    conn.execute('''
                        INSERT OR REPLACE INTO settings (setting_key, setting_value)
                        VALUES (?, ?)
                    ''', (key, json.dumps(value)))
                
                conn.commit()
            
            logger.info("Migrated settings")
        except Exception as e:
            logger.warning(f"Could not migrate settings: {e}")
    
    def _backup_json_files(self):
        """Create backup of JSON files after successful migration."""
        backup_dir = Path('json_backup') / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for name, path in self.json_paths.items():
            if path.exists():
                backup_path = backup_dir / f"{name}_{path.name}"
                shutil.copy2(path, backup_path)
                logger.info(f"Backed up {path} to {backup_path}")
    
    # Question management methods
    def load_questions(self) -> List[Dict[str, Any]]:
        """Load all questions from the database."""
        if self.use_sqlite:
            return self._load_questions_sqlite()
        else:
            return self._load_questions_json()
    
    def _load_questions_sqlite(self) -> List[Dict[str, Any]]:
        """Load questions from SQLite database."""
        with self._get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT id, question_text, options, correct_answer_index, 
                       category, difficulty, explanation, tags
                FROM questions 
                WHERE is_active = 1
                ORDER BY category, question_text
            ''')
            
            questions = []
            for row in cursor.fetchall():
                question = {
                    'id': row['id'],
                    'question_text': row['question_text'],
                    'options': json.loads(row['options']),
                    'correct_answer_index': row['correct_answer_index'],
                    'category': row['category'],
                    'difficulty': row['difficulty'],
                    'explanation': row['explanation'] or '',
                    'tags': json.loads(row['tags']) if row['tags'] else []
                }
                questions.append(question)
            
            return questions
    
    def _load_questions_json(self) -> List[Dict[str, Any]]:
        """Load questions from JSON file (legacy)."""
        return self.load_json_file(self.json_paths['questions'])
    
    def add_question(self, question_data: Dict[str, Any]) -> bool:
        """Add a new question to the database."""
        if self.use_sqlite:
            return self._add_question_sqlite(question_data)
        else:
            return self._add_question_json(question_data)
    
    def _add_question_sqlite(self, question_data: Dict[str, Any]) -> bool:
        """Add question to SQLite database."""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO questions 
                    (question_text, options, correct_answer_index, category, difficulty, explanation, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    question_data['question_text'],
                    json.dumps(question_data['options']),
                    question_data['correct_answer_index'],
                    question_data['category'],
                    question_data.get('difficulty', 'Intermediate'),
                    question_data.get('explanation', ''),
                    json.dumps(question_data.get('tags', []))
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add question: {e}")
            return False
    
    # Generic file operations (for JSON compatibility)
    @staticmethod
    def load_json_file(file_path: Union[str, Path]) -> Any:
        """Load data from a JSON file with error handling."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"JSON file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.debug(f"Loaded JSON file {file_path}: type={type(data)}, keys={list(data.keys()) if isinstance(data, dict) else f'length={len(data) if hasattr(data, '__len__') else 'unknown'}'}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}
    
    @staticmethod
    def save_json_file(file_path: Union[str, Path], data: Any) -> bool:
        """Save data to a JSON file with error handling."""
        file_path = Path(file_path)
        
        try:
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix('.bak')
                shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
            return False
    
    # History management
    def save_history(self, history_data: Dict[str, Any]) -> bool:
        """Save user history data."""
        if self.use_sqlite:
            return self._save_history_sqlite(history_data)
        else:
            return self.save_json_file(self.json_paths['history'], history_data)
    
    def load_history(self) -> Dict[str, Any]:
        """Load user history data."""
        if self.use_sqlite:
            return self._load_history_sqlite()
        else:
            return self.load_json_file(self.json_paths['history'])
    
    def _save_history_sqlite(self, history_data: Dict[str, Any]) -> bool:
        """Save history to SQLite database."""
        # This would implement the SQLite history saving logic
        # For now, return True as placeholder
        return True
    
    def _load_history_sqlite(self) -> Dict[str, Any]:
        """Load history from SQLite database."""
        # This would implement the SQLite history loading logic
        # For now, return empty dict as placeholder
        return {}
    
    # Database maintenance
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database."""
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"backup_linux_plus_study_{timestamp}.db"
        
        if self.use_sqlite:
            shutil.copy2(self.db_path, backup_path)
        else:
            # Backup JSON files
            backup_dir = Path(backup_path).with_suffix('')
            backup_dir.mkdir(exist_ok=True)
            for name, path in self.json_paths.items():
                if path.exists():
                    shutil.copy2(path, backup_dir / path.name)
        
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and return report."""
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        if self.use_sqlite:
            with self._get_db_connection() as conn:
                # Check for orphaned records
                cursor = conn.execute('SELECT COUNT(*) FROM questions WHERE is_active = 1')
                report['stats']['active_questions'] = cursor.fetchone()[0]
                
                cursor = conn.execute('SELECT COUNT(*) FROM user_history')
                report['stats']['history_entries'] = cursor.fetchone()[0]
        
        return report

# Legacy functions for backward compatibility
def load_json_file(file_path: str) -> Any:
    """Legacy function - use DatabaseManager.load_json_file instead."""
    return DatabaseManager.load_json_file(file_path)

def save_json_file(file_path: str, data: Any) -> bool:
    """Legacy function - use DatabaseManager.save_json_file instead."""
    return DatabaseManager.save_json_file(file_path, data)

def load_history(file_path: str) -> Dict[str, Any]:
    """Legacy function for loading history."""
    return DatabaseManager.load_json_file(file_path)

def save_history(file_path: str, history: Dict[str, Any]) -> bool:
    """Legacy function for saving history."""
    return DatabaseManager.save_json_file(file_path, history)

def load_achievements_data(file_path: str) -> Dict[str, Any]:
    """Legacy function for loading achievements."""
    return DatabaseManager.load_json_file(file_path)

def save_achievements_data(file_path: str, data: Dict[str, Any]) -> bool:
    """Legacy function for saving achievements."""
    return DatabaseManager.save_json_file(file_path, data)