"""
Enhanced Question model with database integration and data validation.

This module provides the Question class and related utilities for managing
quiz questions with support for both SQLite and JSON backends.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from utils.database import DatabaseManager
from utils.config import QUESTION_CATEGORIES, DIFFICULTY_LEVELS

# Configure logging
logger = logging.getLogger(__name__)

class QuestionValidationError(Exception):
    """Custom exception for question validation errors."""
    pass

@dataclass
class Question:
    """
    Enhanced Question class with comprehensive data validation and database integration.
    
    Attributes:
        question_text: The main question text
        options: List of answer options
        correct_answer_index: Index of the correct answer (0-based)
        category: Question category
        difficulty: Difficulty level
        explanation: Detailed explanation of the answer
        tags: List of tags for categorization
        id: Database ID (auto-generated)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    question_text: str
    options: List[str]
    correct_answer_index: int
    category: str
    difficulty: str = "Intermediate"
    explanation: str = ""
    tags: List[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.tags is None:
            self.tags = []
        
        # Validate the question data
        self.validate()
        
        # Set timestamps if not provided
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
    
    def validate(self) -> bool:
        """
        Validate question data integrity.
        
        Returns:
            bool: True if valid
            
        Raises:
            QuestionValidationError: If validation fails
        """
        errors = []
        
        # Validate question text
        if not self.question_text or not self.question_text.strip():
            errors.append("Question text cannot be empty")
        elif len(self.question_text.strip()) < 10:
            errors.append("Question text must be at least 10 characters long")
        elif len(self.question_text) > 1000:
            errors.append("Question text must be less than 1000 characters")
        
        # Validate options
        if not self.options:
            errors.append("Question must have options")
        elif len(self.options) < 2:
            errors.append("Question must have at least 2 options")
        elif len(self.options) > 6:
            errors.append("Question cannot have more than 6 options")
        else:
            # Check for empty options
            for i, option in enumerate(self.options):
                if not option or not option.strip():
                    errors.append(f"Option {i+1} cannot be empty")
                elif len(option) > 200:
                    errors.append(f"Option {i+1} must be less than 200 characters")
            
            # Check for duplicate options
            if len(set(self.options)) != len(self.options):
                errors.append("Options cannot contain duplicates")
        
        # Validate correct answer index
        if not isinstance(self.correct_answer_index, int):
            errors.append("Correct answer index must be an integer")
        elif self.correct_answer_index < 0 or self.correct_answer_index >= len(self.options):
            errors.append(f"Correct answer index must be between 0 and {len(self.options) - 1}")
        
        # Validate category
        if not self.category or not self.category.strip():
            errors.append("Category cannot be empty")
        elif self.category not in QUESTION_CATEGORIES:
            logger.warning(f"Category '{self.category}' is not in predefined categories")
        
        # Validate difficulty
        if self.difficulty not in DIFFICULTY_LEVELS:
            errors.append(f"Difficulty must be one of: {', '.join(DIFFICULTY_LEVELS)}")
        
        # Validate explanation length
        if self.explanation and len(self.explanation) > 2000:
            errors.append("Explanation must be less than 2000 characters")
        
        # Validate tags
        if self.tags:
            for tag in self.tags:
                if not isinstance(tag, str) or not tag.strip():
                    errors.append("All tags must be non-empty strings")
                elif len(tag) > 50:
                    errors.append("Tags must be less than 50 characters each")
        
        if errors:
            raise QuestionValidationError(f"Question validation failed: {'; '.join(errors)}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert question object to dictionary.
        
        Returns:
            Dict containing question data
        """
        data = asdict(self)
        
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """
        Create question object from dictionary with flexible field mapping.
        
        Args:
            data: Dictionary containing question data
            
        Returns:
            Question object
            
        Raises:
            QuestionValidationError: If required fields are missing
        """
        # Handle different question text field names for backward compatibility
        question_text = (
            data.get('question_text') or 
            data.get('question') or 
            data.get('text') or 
            ""
        )
        
        # Handle different option field names
        options = (
            data.get('options') or 
            data.get('choices') or 
            data.get('answers') or 
            []
        )
        
        # Handle different correct answer field names
        correct_answer_index = data.get('correct_answer_index')
        if correct_answer_index is None:
            # Try alternative field names
            correct_answer_index = (
                data.get('correct_answer') or
                data.get('answer_index') or
                data.get('correct_index') or
                0
            )
        
        # Handle string-based correct answers (convert to index)
        if isinstance(correct_answer_index, str):
            try:
                # If it's a letter (A, B, C, D), convert to index
                if correct_answer_index.upper() in 'ABCDEF':
                    correct_answer_index = ord(correct_answer_index.upper()) - ord('A')
                else:
                    correct_answer_index = int(correct_answer_index)
            except (ValueError, TypeError):
                correct_answer_index = 0
        
        # Create question object
        try:
            return cls(
                question_text=question_text,
                options=options,
                correct_answer_index=int(correct_answer_index),
                category=data.get('category', 'General'),
                difficulty=data.get('difficulty', 'Intermediate'),
                explanation=data.get('explanation', ''),
                tags=data.get('tags', []),
                id=data.get('id'),
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at')
            )
        except Exception as e:
            logger.error(f"Error creating question from data: {e}")
            logger.error(f"Problematic data: {data}")
            raise QuestionValidationError(f"Could not create question from data: {e}")
    
    def get_correct_answer(self) -> str:
        """
        Get the correct answer text.
        
        Returns:
            The correct answer as a string
        """
        if 0 <= self.correct_answer_index < len(self.options):
            return self.options[self.correct_answer_index]
        return ""
    
    def get_answer_letter(self) -> str:
        """
        Get the correct answer as a letter (A, B, C, etc.).
        
        Returns:
            Letter representation of the correct answer
        """
        if 0 <= self.correct_answer_index < len(self.options):
            return chr(ord('A') + self.correct_answer_index)
        return "A"
    
    def is_answer_correct(self, user_answer: Union[int, str]) -> bool:
        """
        Check if the user's answer is correct.
        
        Args:
            user_answer: User's answer (index, letter, or text)
            
        Returns:
            True if correct, False otherwise
        """
        # Handle different answer formats
        if isinstance(user_answer, str):
            # If it's a letter (A, B, C, D)
            if len(user_answer) == 1 and user_answer.upper() in 'ABCDEF':
                user_index = ord(user_answer.upper()) - ord('A')
                return user_index == self.correct_answer_index
            
            # If it's the actual answer text
            if user_answer in self.options:
                user_index = self.options.index(user_answer)
                return user_index == self.correct_answer_index
            
            # Try to parse as number
            try:
                user_index = int(user_answer)
                return user_index == self.correct_answer_index
            except ValueError:
                return False
        
        elif isinstance(user_answer, int):
            return user_answer == self.correct_answer_index
        
        return False
    
    def get_display_text(self, include_options: bool = True, 
                        option_format: str = "letter") -> str:
        """
        Get formatted question text for display.
        
        Args:
            include_options: Whether to include answer options
            option_format: Format for options ("letter", "number", "plain")
            
        Returns:
            Formatted question text
        """
        text = self.question_text.strip()
        
        if include_options and self.options:
            text += "\n\n"
            for i, option in enumerate(self.options):
                if option_format == "letter":
                    prefix = f"{chr(ord('A') + i)}. "
                elif option_format == "number":
                    prefix = f"{i + 1}. "
                else:
                    prefix = "• "
                
                text += f"{prefix}{option}\n"
        
        return text
    
    def update(self, **kwargs) -> None:
        """
        Update question fields and re-validate.
        
        Args:
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.now().isoformat()
        self.validate()
    
    def clone(self, **kwargs) -> 'Question':
        """
        Create a copy of the question with optional modifications.
        
        Args:
            **kwargs: Fields to override in the clone
            
        Returns:
            New Question object
        """
        data = self.to_dict()
        data.pop('id', None)  # Remove ID for clone
        data.update(kwargs)
        return Question.from_dict(data)

class QuestionManager:
    """
    Manager class for question operations with database integration.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize question manager.
        
        Args:
            db_manager: Database manager instance (creates new if None)
        """
        self.db_manager = db_manager or DatabaseManager()
        self._question_cache = {}
        self._cache_timestamp = None
    
    def load_questions(self, force_reload: bool = False) -> List[Question]:
        """
        Load all questions from the database.
        
        Args:
            force_reload: Force reload from database ignoring cache
            
        Returns:
            List of Question objects
        """
        try:
            # Check cache validity
            if not force_reload and self._question_cache and self._cache_timestamp:
                cache_age = (datetime.now() - self._cache_timestamp).seconds
                if cache_age < 300:  # 5 minutes cache
                    return list(self._question_cache.values())
            
            # Load from database
            questions_data = self.db_manager.load_questions()
            questions = []
            
            for data in questions_data:
                try:
                    question = Question.from_dict(data)
                    questions.append(question)
                except QuestionValidationError as e:
                    logger.warning(f"Skipping invalid question: {e}")
                    continue
            
            # Update cache
            self._question_cache = {q.id or hash(q.question_text): q for q in questions}
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Loaded {len(questions)} questions")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to load questions: {e}")
            return []
    
    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """
        Get a specific question by ID.
        
        Args:
            question_id: Question ID
            
        Returns:
            Question object or None if not found
        """
        if not self._question_cache:
            self.load_questions()
        
        return self._question_cache.get(question_id)
    
    def get_questions_by_category(self, category: str) -> List[Question]:
        """
        Get all questions in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of questions in the category
        """
        questions = self.load_questions()
        return [q for q in questions if q.category == category]
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[Question]:
        """
        Get all questions of a specific difficulty.
        
        Args:
            difficulty: Difficulty level
            
        Returns:
            List of questions at the difficulty level
        """
        questions = self.load_questions()
        return [q for q in questions if q.difficulty == difficulty]
    
    def search_questions(self, search_term: str, 
                        category: Optional[str] = None,
                        difficulty: Optional[str] = None) -> List[Question]:
        """
        Search questions by text content.
        
        Args:
            search_term: Text to search for
            category: Optional category filter
            difficulty: Optional difficulty filter
            
        Returns:
            List of matching questions
        """
        questions = self.load_questions()
        search_term = search_term.lower()
        
        filtered_questions = []
        for question in questions:
            # Apply filters
            if category and question.category != category:
                continue
            if difficulty and question.difficulty != difficulty:
                continue
            
            # Search in question text and options
            if (search_term in question.question_text.lower() or
                any(search_term in option.lower() for option in question.options) or
                search_term in question.explanation.lower()):
                filtered_questions.append(question)
        
        return filtered_questions
    
    def add_question(self, question: Question) -> bool:
        """
        Add a new question to the database.
        
        Args:
            question: Question object to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            question.validate()
            success = self.db_manager.add_question(question.to_dict())
            
            if success:
                # Clear cache to force reload
                self._question_cache = {}
                logger.info(f"Added new question: {question.question_text[:50]}...")
            
            return success
        except Exception as e:
            logger.error(f"Failed to add question: {e}")
            return False
    
    def validate_all_questions(self) -> Dict[str, Any]:
        """
        Validate all questions in the database.
        
        Returns:
            Validation report
        """
        questions = self.load_questions()
        report = {
            'total_questions': len(questions),
            'valid_questions': 0,
            'invalid_questions': 0,
            'errors': [],
            'warnings': []
        }
        
        for question in questions:
            try:
                question.validate()
                report['valid_questions'] += 1
            except QuestionValidationError as e:
                report['invalid_questions'] += 1
                report['errors'].append({
                    'question_id': question.id,
                    'question_text': question.question_text[:100],
                    'error': str(e)
                })
        
        # Check for category distribution
        categories = {}
        for question in questions:
            categories[question.category] = categories.get(question.category, 0) + 1
        
        # Warn about categories with few questions
        for category, count in categories.items():
            if count < 5:
                report['warnings'].append(f"Category '{category}' has only {count} questions")
        
        return report
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the question database.
        
        Returns:
            Statistics dictionary
        """
        questions = self.load_questions()
        
        # Category distribution
        categories = {}
        difficulties = {}
        
        for question in questions:
            categories[question.category] = categories.get(question.category, 0) + 1
            difficulties[question.difficulty] = difficulties.get(question.difficulty, 0) + 1
        
        return {
            'total_questions': len(questions),
            'categories': categories,
            'difficulties': difficulties,
            'avg_options_per_question': sum(len(q.options) for q in questions) / len(questions) if questions else 0,
            'questions_with_explanations': sum(1 for q in questions if q.explanation),
            'questions_with_tags': sum(1 for q in questions if q.tags)
        }

# Legacy function for backward compatibility
def load_questions(file_path: str) -> List[Question]:
    """
    Legacy function to load questions from file.
    
    Args:
        file_path: Path to questions file
        
    Returns:
        List of Question objects
    """
    logger.warning("Using legacy load_questions function. Consider using QuestionManager instead.")
    
    try:
        manager = QuestionManager()
        return manager.load_questions()
    except Exception as e:
        logger.error(f"Failed to load questions using legacy function: {e}")
        return []

# Factory function for creating questions
def create_question(question_text: str, options: List[str], 
                   correct_answer: Union[int, str], category: str,
                   difficulty: str = "Intermediate", 
                   explanation: str = "", tags: List[str] = None) -> Question:
    """
    Factory function for creating questions with validation.
    
    Args:
        question_text: The question text
        options: List of answer options
        correct_answer: Correct answer (index, letter, or text)
        category: Question category
        difficulty: Difficulty level
        explanation: Answer explanation
        tags: List of tags
        
    Returns:
        Question object
    """
    # Convert correct_answer to index if needed
    if isinstance(correct_answer, str):
        if len(correct_answer) == 1 and correct_answer.upper() in 'ABCDEF':
            correct_answer_index = ord(correct_answer.upper()) - ord('A')
        elif correct_answer in options:
            correct_answer_index = options.index(correct_answer)
        else:
            try:
                correct_answer_index = int(correct_answer)
            except ValueError:
                correct_answer_index = 0
    else:
        correct_answer_index = correct_answer
    
    return Question(
        question_text=question_text,
        options=options,
        correct_answer_index=correct_answer_index,
        category=category,
        difficulty=difficulty,
        explanation=explanation,
        tags=tags or []
    )