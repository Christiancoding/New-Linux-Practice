#!/usr/bin/env python3
"""
Question Model for Linux+ Study Game

Handles question data structure, loading, validation,
and intelligent question selection with weighting.
"""

import json
import random
import os
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from utils.config import SAMPLE_QUESTIONS
from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Question(Base):
    """SQLAlchemy model for quiz questions"""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    option_a = Column(String(500), nullable=False)
    option_b = Column(String(500), nullable=False)
    option_c = Column(String(500), nullable=False)
    option_d = Column(String(500), nullable=False)
    correct_answer = Column(String(1), nullable=False)  # A, B, C, or D
    category = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)  # Easy, Medium, Hard
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    times_asked = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    
    # Relationship with question history
    question_history = relationship("QuestionHistory", back_populates="question")
    
    def __init__(self, question_text: str, options: List[str], correct_answer: str, 
                 category: str, difficulty: str, explanation: str = None):
        """Initialize a new Question object"""
        self.question_text = question_text
        if len(options) >= 4:
            self.option_a = options[0]
            self.option_b = options[1]
            self.option_c = options[2]
            self.option_d = options[3]
        else:
            raise ValueError("Question must have at least 4 options")
        
        if correct_answer.upper() not in ['A', 'B', 'C', 'D']:
            raise ValueError("Correct answer must be A, B, C, or D")
        
        self.correct_answer = correct_answer.upper()
        self.category = category
        self.difficulty = difficulty
        self.explanation = explanation
    
    def __repr__(self):
        return f"<Question(id={self.id}, category='{self.category}', difficulty='{self.difficulty}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert question object to dictionary"""
        return {
            'id': self.id,
            'question_text': self.question_text,
            'options': [self.option_a, self.option_b, self.option_c, self.option_d],
            'correct_answer': self.correct_answer,
            'category': self.category,
            'difficulty': self.difficulty,
            'explanation': self.explanation,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'times_asked': self.times_asked,
            'times_correct': self.times_correct,
            'success_rate': self.get_success_rate()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """Create Question object from dictionary"""
        question = cls(
            question_text=data['question_text'],
            options=data['options'],
            correct_answer=data['correct_answer'],
            category=data['category'],
            difficulty=data['difficulty'],
            explanation=data.get('explanation')
        )
        return question
    
    def get_options_dict(self) -> Dict[str, str]:
        """Get options as a dictionary with letter keys"""
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d
        }
    
    def get_success_rate(self) -> float:
        """Calculate success rate for this question"""
        if self.times_asked == 0:
            return 0.0
        return (self.times_correct / self.times_asked) * 100
    
    def update_stats(self, is_correct: bool):
        """Update question statistics"""
        self.times_asked += 1
        if is_correct:
            self.times_correct += 1
        self.updated_at = datetime.utcnow()

class QuestionHistory(Base):
    """Track history of answered questions"""
    __tablename__ = 'question_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    user_answer = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken = Column(Integer, nullable=True)  # seconds
    answered_at = Column(DateTime, default=datetime.utcnow)
    quiz_session_id = Column(String(50), nullable=True)  # To group questions by quiz session
    
    # Relationship
    question = relationship("Question", back_populates="question_history")
    
    def __repr__(self):
        return f"<QuestionHistory(question_id={self.question_id}, is_correct={self.is_correct})>"
class QuestionManager:
    """
    High-level question management class that provides a simplified interface
    for common question operations and business logic
    """
    
    def __init__(self, db_session):
        self.repository = QuestionRepository(db_session)
        self.session = db_session
    
    def load_questions(self, category: str = None, difficulty: str = None, 
                      limit: int = None) -> List[Question]:
        """
        Load questions with optional filtering - main entry point for getting questions
        """
        if category and difficulty:
            questions = self.repository.get_all_questions()
            filtered = [q for q in questions if q.category == category and q.difficulty == difficulty]
        elif category:
            filtered = self.repository.get_questions_by_category(category)
        elif difficulty:
            filtered = self.repository.get_questions_by_difficulty(difficulty)
        else:
            filtered = self.repository.get_all_questions()
        
        if limit:
            return filtered[:limit]
        return filtered
    
    def get_quiz_questions(self, count: int, category: str = None, 
                          difficulty: str = None, avoid_recent: bool = True) -> List[Question]:
        """
        Get questions for a quiz, optionally avoiding recently asked questions
        """
        if avoid_recent:
            # Get questions that haven't been asked recently
            return self._get_questions_avoiding_recent(count, category, difficulty)
        else:
            return self.repository.get_random_questions(count, category, difficulty)
    
    def get_review_questions(self, limit: int = 10) -> List[Question]:
        """
        Get questions that need review (answered incorrectly or have low success rate)
        """
        try:
            # Get questions with success rate below 70% or never answered correctly
            query = self.session.query(Question).filter(
                Question.is_active == True,
                Question.times_asked > 0
            )
            
            questions = query.all()
            review_questions = [q for q in questions if q.get_success_rate() < 70.0]
            
            # Sort by success rate (lowest first) and limit
            review_questions.sort(key=lambda x: x.get_success_rate())
            return review_questions[:limit]
        except Exception as e:
            logger.error(f"Error getting review questions: {e}")
            return []
    
    def get_adaptive_question(self, user_performance: Dict[str, float]) -> Optional[Question]:
        """
        Get next question based on adaptive learning algorithm
        Args:
            user_performance: Dict with category/difficulty performance percentages
        """
        try:
            # Find weakest areas
            weakest_category = min(user_performance.get('categories', {}), 
                                 key=user_performance['categories'].get, default=None)
            
            if weakest_category:
                # Get questions from weakest category
                questions = self.repository.get_questions_by_category(weakest_category)
                if questions:
                    # Return a random question from the weakest category
                    import random
                    return random.choice(questions)
            
            # Fallback to random question
            random_questions = self.repository.get_random_questions(1)
            return random_questions[0] if random_questions else None
        except Exception as e:
            logger.error(f"Error getting adaptive question: {e}")
            return None
    
    def bulk_import_questions(self, questions_data: List[Dict[str, Any]]) -> int:
        """
        Import multiple questions from a list of dictionaries
        Returns the number of successfully imported questions
        """
        imported_count = 0
        for question_data in questions_data:
            try:
                question = self.repository.create_question(question_data)
                if question:
                    imported_count += 1
            except Exception as e:
                logger.error(f"Error importing question: {e}")
                continue
        
        logger.info(f"Successfully imported {imported_count} out of {len(questions_data)} questions")
        return imported_count
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about all questions
        """
        try:
            all_questions = self.repository.get_all_questions()
            categories = self.repository.get_categories()
            difficulties = self.repository.get_difficulties()
            
            total_questions = len(all_questions)
            total_asked = sum(q.times_asked for q in all_questions)
            total_correct = sum(q.times_correct for q in all_questions)
            
            # Category breakdown
            category_stats = {}
            for category in categories:
                cat_questions = [q for q in all_questions if q.category == category]
                category_stats[category] = {
                    'total': len(cat_questions),
                    'asked': sum(q.times_asked for q in cat_questions),
                    'correct': sum(q.times_correct for q in cat_questions)
                }
            
            # Difficulty breakdown
            difficulty_stats = {}
            for difficulty in difficulties:
                diff_questions = [q for q in all_questions if q.difficulty == difficulty]
                difficulty_stats[difficulty] = {
                    'total': len(diff_questions),
                    'asked': sum(q.times_asked for q in diff_questions),
                    'correct': sum(q.times_correct for q in diff_questions)
                }
            
            return {
                'total_questions': total_questions,
                'total_asked': total_asked,
                'total_correct': total_correct,
                'overall_success_rate': (total_correct / total_asked * 100) if total_asked > 0 else 0,
                'categories': category_stats,
                'difficulties': difficulty_stats,
                'available_categories': categories,
                'available_difficulties': difficulties
            }
        except Exception as e:
            logger.error(f"Error getting statistics summary: {e}")
            return {}
    
    def process_answer(self, question_id: int, user_answer: str, 
                      time_taken: int = None, quiz_session_id: str = None) -> Dict[str, Any]:
        """
        Process a user's answer and return detailed feedback
        """
        try:
            question = self.repository.get_question_by_id(question_id)
            if not question:
                return {'error': 'Question not found'}
            
            is_correct = user_answer.upper() == question.correct_answer.upper()
            
            # Record the answer
            self.repository.record_answer(question_id, user_answer, is_correct, 
                                        time_taken, quiz_session_id)
            
            return {
                'is_correct': is_correct,
                'correct_answer': question.correct_answer,
                'explanation': question.explanation,
                'user_answer': user_answer.upper(),
                'question': question.to_dict(),
                'success_rate': question.get_success_rate(),
                'times_asked': question.times_asked
            }
        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            return {'error': str(e)}
    
    def _get_questions_avoiding_recent(self, count: int, category: str = None, 
                                     difficulty: str = None, hours_threshold: int = 24) -> List[Question]:
        """
        Get questions avoiding those asked in the last N hours
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            
            # Get recently asked question IDs
            recent_history = self.session.query(QuestionHistory.question_id).filter(
                QuestionHistory.answered_at > cutoff_time
            ).distinct().all()
            recent_question_ids = [h[0] for h in recent_history]
            
            # Get questions not in recent list
            query = self.session.query(Question).filter(
                Question.is_active == True,
                ~Question.id.in_(recent_question_ids) if recent_question_ids else True
            )
            
            if category:
                query = query.filter(Question.category == category)
            if difficulty:
                query = query.filter(Question.difficulty == difficulty)
            
            from sqlalchemy import func
            questions = query.order_by(func.random()).limit(count).all()
            
            # If we don't have enough non-recent questions, fill with random ones
            if len(questions) < count:
                remaining = count - len(questions)
                additional = self.repository.get_random_questions(remaining, category, difficulty)
                questions.extend(additional)
            
            return questions[:count]
        except Exception as e:
            logger.error(f"Error getting questions avoiding recent: {e}")
            return self.repository.get_random_questions(count, category, difficulty)

# Update the legacy function to use QuestionManager
def load_questions(db_session, category: str = None, difficulty: str = None) -> List[Question]:
    """
    Legacy function for backward compatibility
    """
    manager = QuestionManager(db_session)
    return manager.load_questions(category, difficulty)