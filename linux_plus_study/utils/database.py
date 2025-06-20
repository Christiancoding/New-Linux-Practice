"""
Database operations using SQLAlchemy ORM for the Linux+ Study Application.
Replaces JSON file operations with proper database operations.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Database Models
class User(Base):
    """User model for authentication and progress tracking"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    total_points = Column(Integer, default=0)
    
    # Relationships
    quiz_history = relationship("QuizHistory", back_populates="user", cascade="all, delete-orphan")
    user_achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    study_sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")

class Question(Base):
    """Question model for storing quiz questions"""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # Store as JSON array
    correct_answer = Column(Integer, nullable=False)  # Index of correct option
    category = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    explanation = Column(Text)
    tags = Column(JSON)  # Store tags as JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    quiz_history = relationship("QuizHistory", back_populates="question")

class QuizHistory(Base):
    """Quiz history model for tracking user answers"""
    __tablename__ = 'quiz_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    user_answer = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Float)
    answered_at = Column(DateTime, default=datetime.utcnow)
    quiz_session_id = Column(String(50))  # Group questions from same quiz session
    
    # Relationships
    user = relationship("User", back_populates="quiz_history")
    question = relationship("Question", back_populates="quiz_history")

class Achievement(Base):
    """Achievement definitions"""
    __tablename__ = 'achievements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    icon = Column(String(100))
    points_required = Column(Integer)
    condition_type = Column(String(50))  # points, streak, category_mastery, etc.
    condition_data = Column(JSON)  # Store condition-specific data
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")

class UserAchievement(Base):
    """User's earned achievements"""
    __tablename__ = 'user_achievements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_id = Column(Integer, ForeignKey('achievements.id'), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

class StudySession(Base):
    """Study session tracking"""
    __tablename__ = 'study_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String(50), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    session_type = Column(String(50))  # normal, quick_fire, daily_challenge
    category_focus = Column(String(100))
    
    # Relationships
    user = relationship("User", back_populates="study_sessions")

class SpacedRepetition(Base):
    """Spaced repetition system for questions"""
    __tablename__ = 'spaced_repetition'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    repetition_count = Column(Integer, default=0)
    next_review_date = Column(DateTime, default=datetime.utcnow)
    last_reviewed = Column(DateTime)

class DatabaseManager:
    """Main database manager class"""
    
    def __init__(self, database_url: str = None, echo: bool = False):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection URL. If None, uses SQLite
            echo: Whether to echo SQL queries for debugging
        """
        if database_url is None:
            # Default to SQLite in the project directory
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'linux_plus_study.db')
            database_url = f"sqlite:///{db_path}"
        
        self.engine = create_engine(
            database_url,
            echo=echo,
            poolclass=StaticPool if 'sqlite' in database_url else None,
            connect_args={'check_same_thread': False} if 'sqlite' in database_url else {}
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
        
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
        
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

# Database Operations
class QuestionOperations:
    """Operations for managing questions"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def load_questions_from_json(self, json_file_path: str) -> List[Question]:
        """Load questions from JSON file and convert to database objects"""
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        questions = []
        with self.db.get_session() as session:
            for item in data.get('questions', []):
                question = Question(
                    question_text=item['question'],
                    options=item['options'],
                    correct_answer=item['correct_answer'],
                    category=item.get('category', 'General'),
                    difficulty=item.get('difficulty', 'medium'),
                    explanation=item.get('explanation', ''),
                    tags=item.get('tags', [])
                )
                session.add(question)
                questions.append(question)
            
            session.commit()
        
        logger.info(f"Loaded {len(questions)} questions from {json_file_path}")
        return questions
    
    def get_all_questions(self, category: str = None, difficulty: str = None, 
                         is_active: bool = True) -> List[Question]:
        """Get all questions with optional filtering"""
        with self.db.get_session() as session:
            query = session.query(Question).filter(Question.is_active == is_active)
            
            if category:
                query = query.filter(Question.category == category)
            if difficulty:
                query = query.filter(Question.difficulty == difficulty)
                
            return query.all()
    
    def get_random_question(self, category: str = None, exclude_ids: List[int] = None) -> Optional[Question]:
        """Get a random question with optional filtering"""
        with self.db.get_session() as session:
            query = session.query(Question).filter(Question.is_active == True)
            
            if category:
                query = query.filter(Question.category == category)
            if exclude_ids:
                query = query.filter(~Question.id.in_(exclude_ids))
                
            return query.order_by('RANDOM()' if 'sqlite' in str(self.db.engine.url) else 'RAND()').first()

class HistoryOperations:
    """Operations for managing quiz history"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def record_answer(self, user_id: int, question_id: int, user_answer: int, 
                     is_correct: bool, time_taken: float = None, 
                     session_id: str = None) -> QuizHistory:
        """Record a user's answer to a question"""
        with self.db.get_session() as session:
            history_entry = QuizHistory(
                user_id=user_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                time_taken_seconds=time_taken,
                quiz_session_id=session_id
            )
            session.add(history_entry)
            session.commit()
            return history_entry
    
    def get_user_history(self, user_id: int, limit: int = None) -> List[QuizHistory]:
        """Get user's quiz history"""
        with self.db.get_session() as session:
            query = session.query(QuizHistory).filter(QuizHistory.user_id == user_id)\
                          .order_by(QuizHistory.answered_at.desc())
            
            if limit:
                query = query.limit(limit)
                
            return query.all()
    
    def get_incorrect_answers(self, user_id: int) -> List[QuizHistory]:
        """Get all questions user answered incorrectly"""
        with self.db.get_session() as session:
            return session.query(QuizHistory)\
                         .filter(QuizHistory.user_id == user_id)\
                         .filter(QuizHistory.is_correct == False)\
                         .order_by(QuizHistory.answered_at.desc()).all()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        with self.db.get_session() as session:
            total_answers = session.query(QuizHistory).filter(QuizHistory.user_id == user_id).count()
            correct_answers = session.query(QuizHistory)\
                                   .filter(QuizHistory.user_id == user_id)\
                                   .filter(QuizHistory.is_correct == True).count()
            
            accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
            
            return {
                'total_questions_answered': total_answers,
                'correct_answers': correct_answers,
                'incorrect_answers': total_answers - correct_answers,
                'accuracy_percentage': round(accuracy, 2)
            }

class AchievementOperations:
    """Operations for managing achievements"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def initialize_default_achievements(self):
        """Initialize default achievements"""
        default_achievements = [
            {
                'name': 'First Steps',
                'description': 'Answer your first question correctly',
                'points_required': 0,
                'condition_type': 'first_correct',
                'condition_data': {}
            },
            {
                'name': 'Quick Learner',
                'description': 'Get 10 questions correct in a row',
                'points_required': 0,
                'condition_type': 'streak',
                'condition_data': {'required_streak': 10}
            },
            {
                'name': 'Century Club',
                'description': 'Earn 100 points',
                'points_required': 100,
                'condition_type': 'points',
                'condition_data': {}
            }
        ]
        
        with self.db.get_session() as session:
            for ach_data in default_achievements:
                existing = session.query(Achievement).filter(Achievement.name == ach_data['name']).first()
                if not existing:
                    achievement = Achievement(**ach_data)
                    session.add(achievement)
            session.commit()
    
    def check_new_achievements(self, user_id: int) -> List[Achievement]:
        """Check for newly earned achievements"""
        # This would contain logic to check various achievement conditions
        # Implementation depends on specific achievement types
        new_achievements = []
        # ... achievement checking logic ...
        return new_achievements

# Utility Functions
def migrate_from_json_files(db_manager: DatabaseManager, json_files_path: str):
    """Migrate existing JSON data to database"""
    question_ops = QuestionOperations(db_manager)
    
    # Migrate questions
    questions_file = os.path.join(json_files_path, 'questions.json')
    if os.path.exists(questions_file):
        question_ops.load_questions_from_json(questions_file)
        logger.info("Questions migrated successfully")
    
    # Initialize achievements
    achievement_ops = AchievementOperations(db_manager)
    achievement_ops.initialize_default_achievements()
    logger.info("Default achievements initialized")

def get_database_manager(config_path: str = None) -> DatabaseManager:
    """Factory function to get configured database manager"""
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        database_url = config.get('database_url')
        echo = config.get('debug', False)
    else:
        database_url = None
        echo = False
    
    return DatabaseManager(database_url=database_url, echo=echo)

# Legacy compatibility functions (for gradual migration)
def load_json_file(file_path: str) -> Dict[str, Any]:
    """Legacy function - replaced by database operations"""
    logger.warning("load_json_file is deprecated. Use database operations instead.")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json_file(file_path: str, data: Dict[str, Any]):
    """Legacy function - replaced by database operations"""
    logger.warning("save_json_file is deprecated. Use database operations instead.")
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)