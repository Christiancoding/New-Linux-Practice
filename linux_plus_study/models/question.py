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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Text, JSON
from sqlalchemy import create_engine

Base = declarative_base()


class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # Store list of options as JSON
    correct_answer = Column(String(10), nullable=False)  # e.g., 'A', 'B', 'C', 'D'
    category = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)  # e.g., 'Easy', 'Medium', 'Hard'
    
    def __init__(self, question_text, options, correct_answer, category, difficulty):
        self.question_text = question_text
        self.options = options
        self.correct_answer = correct_answer
        self.category = category
        self.difficulty = difficulty
    
    def to_dict(self):
        """Convert the question object to a dictionary - KEEP this method"""
        return {
            'id': self.id,
            'question_text': self.question_text,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'category': self.category,
            'difficulty': self.difficulty
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a question object from a dictionary - KEEP but UPDATE"""
        return cls(
            question_text=data['question_text'],
            options=data['options'],
            correct_answer=data['correct_answer'],
            category=data['category'],
            difficulty=data['difficulty']
        )
    
    def __repr__(self):
        return f"<Question(id={self.id}, category='{self.category}', difficulty='{self.difficulty}')>"
    
    def _validate(self):
        """Validate question data integrity."""
        if not self.text or not self.text.strip():
            raise ValueError("Question text cannot be empty")
        
        if not self.options or len(self.options) < 2:
            raise ValueError("Question must have at least 2 options")
        
        if not (0 <= self.correct_index < len(self.options)):
            raise ValueError(f"Correct index {self.correct_index} is out of range for {len(self.options)} options")
        
        if not self.category or not self.category.strip():
            raise ValueError("Question category cannot be empty")
        
        # Check for empty options
        for i, option in enumerate(self.options):
            if not option or not option.strip():
                raise ValueError(f"Option {i} cannot be empty")
    
    def to_tuple(self) -> Tuple[str, List[str], int, str, str]:
        """
        Convert question to tuple format for backwards compatibility.
        
        Returns:
            Tuple: (text, options, correct_index, category, explanation)
        """
        return (self.text, self.options, self.correct_index, self.category, self.explanation)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert question to dictionary format.
        
        Returns:
            Dict: Question data as dictionary
        """
        return {
            'text': self.text,
            'options': self.options,
            'correct_index': self.correct_index,
            'category': self.category,
            'explanation': self.explanation
        }
    
    @classmethod
    def from_tuple(cls, question_tuple: Tuple) -> 'Question':
        """
        Create Question from tuple format.
        
        Args:
            question_tuple: Tuple in format (text, options, correct_index, category, explanation)
            
        Returns:
            Question: New Question instance
        """
        if len(question_tuple) < 4:
            raise ValueError(f"Question tuple must have at least 4 elements, got {len(question_tuple)}")
        
        text = question_tuple[0]
        options = question_tuple[1]
        correct_index = question_tuple[2]
        category = question_tuple[3]
        explanation = question_tuple[4] if len(question_tuple) > 4 else ""
        
        return cls(text, options, correct_index, category, explanation)
    
    @classmethod
    def from_dict(cls, question_dict: Dict[str, Any]) -> 'Question':
        """
        Create Question from dictionary format.
        
        Args:
            question_dict: Dictionary containing question data
            
        Returns:
            Question: New Question instance
        """
        # Handle both formats: "question"/"text" and "correct_answer_index"/"correct_index"
        text = question_dict.get('text') or question_dict.get('question')
        if not text:
            raise ValueError("Missing required field: 'text' or 'question'")
        
        if 'options' not in question_dict:
            raise ValueError("Missing required field: 'options'")
        
        correct_index = question_dict.get('correct_index')
        if correct_index is None:
            correct_index = question_dict.get('correct_answer_index')
        if correct_index is None:
            raise ValueError("Missing required field: 'correct_index' or 'correct_answer_index'")
        
        if 'category' not in question_dict:
            raise ValueError("Missing required field: 'category'")
        
        return cls(
            text=text,
            options=question_dict['options'],
            correct_index=correct_index,
            category=question_dict['category'],
            explanation=question_dict.get('explanation', '')
        )
    
    def get_correct_option(self) -> str:
        """
        Get the text of the correct answer option.
        
        Returns:
            str: Text of the correct option
        """
        return self.options[self.correct_index]
    
    def is_answer_correct(self, answer_index: int) -> bool:
        """
        Check if the given answer index is correct.
        
        Args:
            answer_index (int): Index of the selected answer
            
        Returns:
            bool: True if answer is correct
        """
        return answer_index == self.correct_index
    
    def __str__(self) -> str:
        """String representation of the question."""
        return f"Question({self.category}): {self.text[:50]}..."
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Question(text='{self.text[:30]}...', category='{self.category}', options={len(self.options)})"


class QuestionManager:
    """Manages the question pool and selection logic."""
    
    def __init__(self):
        """Initialize the question manager."""
        self.questions: List[Question] = []
        self.categories: set = set()
        self.answered_indices_session: List[int] = []
        
        # Load questions from various sources
        self.load_questions()
    
    def get_database_session(database_url="sqlite:///linux_plus_study.db"):
        """Create and return a database session"""
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)  # Create tables if they don't exist
        Session = sessionmaker(bind=engine)
        return Session()

    def load_questions_from_db(session, category=None, difficulty=None):
        """Load questions from database with optional filtering"""
        query = session.query(Question)
        
        if category:
            query = query.filter(Question.category == category)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        
        return query.all()

    def get_question_by_id(session, question_id):
        """Get a specific question by ID"""
        return session.query(Question).filter(Question.id == question_id).first()

    def get_categories(session):
        """Get all unique categories"""
        return [cat[0] for cat in session.query(Question.category).distinct().all()]

    def get_difficulties(session):
        """Get all unique difficulty levels"""
        return [diff[0] for diff in session.query(Question.difficulty).distinct().all()]
    def migrate_json_to_db(json_file_path, session):
        """One-time migration function to move questions from JSON file to database"""
        import json
        
        with open(json_file_path, 'r') as f:
            questions_data = json.load(f)
        
        for question_data in questions_data:
            # Check if question already exists to avoid duplicates
            existing = session.query(Question).filter(
                Question.question_text == question_data['question_text']
            ).first()
            
            if not existing:
                question = Question.from_dict(question_data)
                session.add(question)
        
        session.commit()
        print(f"Migrated {len(questions_data)} questions to database")
    
    def _load_from_json_file(self, filename: str) -> List[Question]:
        """
        Load questions from a JSON file.
        
        Args:
            filename (str): Path to the JSON file
            
        Returns:
            List[Question]: List of loaded questions
        """
        questions = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, list):
            # List of question tuples or dictionaries
            for item in data:
                try:
                    if isinstance(item, (list, tuple)):
                        question = Question.from_tuple(tuple(item))
                    elif isinstance(item, dict):
                        question = Question.from_dict(item)
                    else:
                        print(f"Warning: Unknown question format: {type(item)}")
                        continue
                    
                    questions.append(question)
                except ValueError as e:
                    print(f"Warning: Invalid question in file {filename}: {e}")
        
        elif isinstance(data, dict):
            # Handle structured format with metadata
            if 'questions' in data:
                questions_data = data['questions']
                for item in questions_data:
                    try:
                        if isinstance(item, dict):
                            question = Question.from_dict(item)
                        else:
                            question = Question.from_tuple(item)
                        questions.append(question)
                    except ValueError as e:
                        print(f"Warning: Invalid question in file {filename}: {e}")
        
        return questions
    
    def get_question_count(self, category_filter: Optional[str] = None) -> int:
        """
        Get count of available questions.
        
        Args:
            category_filter (str, optional): Category to filter by
            
        Returns:
            int: Number of available questions
        """
        if category_filter is None:
            return len(self.questions)
        
        return sum(1 for q in self.questions if q.category == category_filter)
    
    def get_categories(self) -> List[str]:
        """
        Get list of all question categories.
        
        Returns:
            List[str]: Sorted list of category names
        """
        return sorted(list(self.categories))
    
    def select_question(self, category_filter: Optional[str] = None, 
                       game_history: Optional[Dict] = None) -> Tuple[Optional[Question], int]:
        """
        Select a question using intelligent weighting based on performance history.
        
        Args:
            category_filter (str, optional): Category to filter questions by
            game_history (dict, optional): Game history for weighting calculations
            
        Returns:
            Tuple[Optional[Question], int]: Selected question and its index, or (None, -1) if none available
        """
        # Get possible question indices
        possible_indices = [
            idx for idx, q in enumerate(self.questions)
            if (category_filter is None or q.category == category_filter)
        ]
        
        if not possible_indices:
            return None, -1
        
        # Filter out questions answered this session
        available_indices = [
            idx for idx in possible_indices 
            if idx not in self.answered_indices_session
        ]
        
        # If all questions in category have been answered this session, return None
        if not available_indices:
            return None, -1
        
        # Apply intelligent weighting if history is available
        if game_history:
            chosen_index = self._select_weighted_question(available_indices, game_history)
        else:
            # Simple random selection if no history
            chosen_index = random.choice(available_indices)
        
        # Mark as answered this session
        self.answered_indices_session.append(chosen_index)
        
        return self.questions[chosen_index], chosen_index
    
    def _select_weighted_question(self, available_indices: List[int], 
                                 game_history: Dict) -> int:
        """
        Select question using performance-based weighting.
        
        Args:
            available_indices (List[int]): Available question indices
            game_history (dict): Game history for weighting
            
        Returns:
            int: Selected question index
        """
        weights = []
        question_history = game_history.get("questions", {})
        
        for q_idx in available_indices:
            if q_idx < 0 or q_idx >= len(self.questions):
                continue  # Safety check
            
            question = self.questions[q_idx]
            q_stats = question_history.get(question.text, {"correct": 0, "attempts": 0})
            
            attempts = q_stats.get("attempts", 0)
            correct = q_stats.get("correct", 0)
            
            # Calculate accuracy (default to 50% for unasked questions)
            accuracy = (correct / attempts) if attempts > 0 else 0.5
            
            # Weight calculation: favor incorrect answers and less attempted questions
            # Higher weight for lower accuracy and fewer attempts
            weight = (1.0 - accuracy) * 10 + (1.0 / (attempts + 1)) * 3
            weights.append(max(0.1, weight))  # Ensure minimum weight
        
        # Weighted random selection
        try:
            chosen_index = random.choices(available_indices, weights=weights, k=1)[0]
        except (IndexError, ValueError):
            # Fallback to simple random if weighting fails
            chosen_index = random.choice(available_indices)
        
        return chosen_index
    
    def reset_session(self):
        """Reset the session-specific answered questions list."""
        self.answered_indices_session = []
    
    def get_question_by_index(self, index: int) -> Optional[Question]:
        """
        Get a question by its index.
        
        Args:
            index (int): Question index
            
        Returns:
            Optional[Question]: Question if index is valid, None otherwise
        """
        if 0 <= index < len(self.questions):
            return self.questions[index]
        return None
    
    def get_questions_by_category(self, category: str) -> List[Tuple[Question, int]]:
        """
        Get all questions in a specific category.
        
        Args:
            category (str): Category name
            
        Returns:
            List[Tuple[Question, int]]: List of (question, index) tuples
        """
        return [
            (question, idx) for idx, question in enumerate(self.questions)
            if question.category == category
        ]
    
    def add_question(self, question: Question) -> int:
        """
        Add a new question to the pool.
        
        Args:
            question (Question): Question to add
            
        Returns:
            int: Index of the added question
        """
        self.questions.append(question)
        self.categories.add(question.category)
        return len(self.questions) - 1
    
    def remove_question(self, index: int) -> bool:
        """
        Remove a question by index.
        
        Args:
            index (int): Index of question to remove
            
        Returns:
            bool: True if removed successfully
        """
        if 0 <= index < len(self.questions):
            removed_question = self.questions.pop(index)
            
            # Update categories if this was the last question in its category
            if not any(q.category == removed_question.category for q in self.questions):
                self.categories.discard(removed_question.category)
            
            # Update answered indices to account for removed question
            self.answered_indices_session = [
                idx - 1 if idx > index else idx 
                for idx in self.answered_indices_session 
                if idx != index
            ]
            
            return True
        return False
    
    def export_questions(self, filename: str, format_type: str = "json"):
        """
        Export questions to a file.
        
        Args:
            filename (str): Output filename
            format_type (str): Export format ("json", "md", or "csv")
        """
        if format_type.lower() == "json":
            self._export_json(filename)
        elif format_type.lower() == "md":
            self._export_markdown(filename)
        elif format_type.lower() == "csv":
            self._export_csv(filename)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_json(self, filename: str):
        """Export questions to JSON format."""
        export_data = {
            "metadata": {
                "title": "Linux+ Study Questions",
                "export_date": str(datetime.now()),
                "total_questions": len(self.questions),
                "categories": sorted(list(self.categories))
            },
            "questions": [q.to_dict() for q in self.questions]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def _export_markdown(self, filename: str):
        """Export questions to Markdown format."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Linux+ Study Questions\n\n")
            
            # Questions section
            f.write("## Questions\n\n")
            for i, question in enumerate(self.questions, 1):
                f.write(f"**Q{i}.** ({question.category})\n")
                f.write(f"{question.text}\n")
                for j, option in enumerate(question.options):
                    f.write(f"   {chr(ord('A') + j)}. {option}\n")
                f.write("\n")
            
            f.write("---\n\n")
            
            # Answers section
            f.write("## Answers\n\n")
            for i, question in enumerate(self.questions, 1):
                correct_letter = chr(ord('A') + question.correct_index)
                correct_text = question.get_correct_option()
                
                f.write(f"**A{i}.** {correct_letter}. {correct_text}\n")
                if question.explanation:
                    f.write(f"   *Explanation:* {question.explanation}\n")
                f.write("\n")
    
    def _export_csv(self, filename: str):
        """Export questions to CSV format."""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Question', 'Option A', 'Option B', 'Option C', 'Option D', 
                           'Correct Answer', 'Category', 'Explanation'])
            
            # Questions
            for question in self.questions:
                options = question.options + [''] * (4 - len(question.options))  # Pad to 4 options
                correct_letter = chr(ord('A') + question.correct_index)
                
                writer.writerow([
                    question.text,
                    options[0] if len(options) > 0 else '',
                    options[1] if len(options) > 1 else '',
                    options[2] if len(options) > 2 else '',
                    options[3] if len(options) > 3 else '',
                    correct_letter,
                    question.category,
                    question.explanation
                ])
    
    def get_question_tuples(self) -> List[Tuple[str, List[str], int, str, str]]:
        """
        Get all questions as tuples for backwards compatibility.
        
        Returns:
            List[Tuple]: Questions in tuple format
        """
        return [q.to_tuple() for q in self.questions]
    
    def validate_all_questions(self) -> List[str]:
        """
        Validate all questions and return list of errors.
        
        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        
        for i, question in enumerate(self.questions):
            try:
                question._validate()
            except ValueError as e:
                errors.append(f"Question {i + 1}: {e}")
        
        return errors
    def create_question(session, question_text, options, correct_answer, category, difficulty):
        """Creates and saves a new question to the database."""
        question = Question(question_text, options, correct_answer, category, difficulty)
        session.add(question)
        session.commit()
        return question

    def get_question_by_id(session, question_id):
        """Retrieves a specific question by ID."""
        return session.query(Question).filter(Question.id == question_id).first()

    def update_question(session, question_id, **kwargs):
        """Updates a question with the provided fields."""
        question = session.query(Question).filter(Question.id == question_id).first()
        if question:
            for key, value in kwargs.items():
                if hasattr(question, key):
                    setattr(question, key, value)
            session.commit()
        return question

    def delete_question(session, question_id):
        """Deletes a question from the database."""
        question = session.query(Question).filter(Question.id == question_id).first()
        if question:
            session.delete(question)
            session.commit()
            return True
        return False