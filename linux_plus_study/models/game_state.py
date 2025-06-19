"""
Enhanced Game State Model with SQLite integration and advanced analytics.

This module manages quiz sessions, user progress, and learning analytics
with improved database integration and spaced repetition algorithms.
"""

import json
import sqlite3
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import random
from collections import defaultdict, Counter

from utils.database import DatabaseManager
from utils.config import (
    ACHIEVEMENTS_FILE, 
    HISTORY_FILE, 
    QUESTION_CATEGORIES,
    POINTS_PER_CORRECT,
    POINTS_PER_INCORRECT,
    STREAK_BONUS_THRESHOLD,
    STREAK_BONUS_MULTIPLIER,
    QUIZ_SETTINGS,
    ACHIEVEMENT_SETTINGS
)

logger = logging.getLogger(__name__)

class GameState:
    """
    Enhanced game state manager with SQLite integration and advanced analytics.
    
    Features:
    - Session-based question tracking
    - Spaced repetition algorithm
    - Advanced performance analytics
    - Category-based learning insights
    - Adaptive difficulty adjustment
    - Streak and achievement tracking
    """
    
    def __init__(self, db_manager, achievements_file=ACHIEVEMENTS_FILE, history_file=HISTORY_FILE):
        """Initialize GameState with database manager and load history."""
        self.db_manager = db_manager
        self.questions = self.db_manager.load_questions()
        
        # Initialize other attributes
        self.asked_questions = set()
        self.current_session_history = []
        self.session_points = 0
        self.current_streak = 0
        self.quiz_active = False
        
        # Load persistent data
        self.achievements_file = achievements_file
        self.history_file = history_file
        self.achievements = self.load_achievements()
        self.history = self.load_history()
        
        # Create categories set from loaded questions
        self.categories = set(q.get('category', 'General') for q in self.questions)
        
        logger.info(f"GameState initialized with {len(self.questions)} questions")
    def load_history(self):
        """Load question history using database manager."""
        try:
            history = self.db_manager.load_history()
            if history:
                return history
            else:
                # Try loading from JSON as fallback
                return self.db_manager.load_json_file(self.history_file)
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return {}
    
    def load_questions(self):
        """Reload questions from database manager."""
        try:
            self.questions = self.db_manager.load_questions()
            self.categories = set(q.get('category', 'General') for q in self.questions)
            logger.info(f"Reloaded {len(self.questions)} questions")
            return self.questions
        except Exception as e:
            logger.error(f"Failed to reload questions: {e}")
            return self.questions  # Return existing questions if reload fails
    
    def _load_achievements(self) -> Dict[str, Any]:
        """Load user achievements."""
        if self.use_database and self.db_manager:
            return self._load_achievements_sqlite()
        else:
            return self._load_achievements_json()
    
    def _load_achievements_sqlite(self) -> Dict[str, Any]:
        """Load achievements from SQLite database."""
        achievements = {
            'badges': [],
            'points_earned': 0,
            'milestones': {},
            'streaks': {'best': 0, 'current': 0}
        }
        
        try:
            with self.db_manager._get_db_connection() as conn:
                # Load badges
                cursor = conn.execute('SELECT achievement_name FROM achievements WHERE achievement_type = ?', ('badge',))
                achievements['badges'] = [row[0] for row in cursor.fetchall()]
                
                # Load points
                cursor = conn.execute('SELECT stat_value FROM user_stats WHERE stat_name = ?', ('total_points',))
                row = cursor.fetchone()
                if row:
                    achievements['points_earned'] = int(row[0])
                
                # Load streaks
                cursor = conn.execute('SELECT stat_value FROM user_stats WHERE stat_name = ?', ('best_streak',))
                row = cursor.fetchone()
                if row:
                    achievements['streaks']['best'] = int(row[0])
        
        except Exception as e:
            logger.error(f"Error loading achievements from SQLite: {e}")
        
        return achievements
    
    def _load_achievements_json(self) -> Dict[str, Any]:
        """Load achievements from JSON file (legacy)."""
        try:
            from utils.database import load_json_file
            return load_json_file('linux_plus_achievements.json')
        except Exception as e:
            logger.warning(f"Could not load achievements from JSON: {e}")
            return {'badges': [], 'points_earned': 0, 'milestones': {}, 'streaks': {'best': 0, 'current': 0}}
    
    def _load_user_stats(self) -> Dict[str, Any]:
        """Load comprehensive user statistics."""
        if self.use_database and self.db_manager:
            return self._load_user_stats_sqlite()
        else:
            return self._load_user_stats_json()
    
    def _load_user_stats_sqlite(self) -> Dict[str, Any]:
        """Load user stats from SQLite database."""
        stats = {}
        
        try:
            with self.db_manager._get_db_connection() as conn:
                cursor = conn.execute('SELECT stat_name, stat_value FROM user_stats')
                for row in cursor.fetchall():
                    try:
                        # Try to parse as JSON first, fallback to string
                        stats[row[0]] = json.loads(row[1])
                    except json.JSONDecodeError:
                        stats[row[0]] = row[1]
        
        except Exception as e:
            logger.error(f"Error loading user stats from SQLite: {e}")
        
        return stats
    
    def _load_user_stats_json(self) -> Dict[str, Any]:
        """Load user stats from JSON files (legacy)."""
        stats = {}
        try:
            from utils.database import load_json_file
            # Could load from multiple JSON files if needed
            history = load_json_file('linux_plus_history.json')
            # Process history to extract stats
            stats['history_loaded'] = len(history)
        except Exception as e:
            logger.warning(f"Could not load user stats from JSON: {e}")
        
        return stats
    
    def _load_and_calculate_stats(self):
        """Load historical data and calculate current statistics."""
        if self.use_database and self.db_manager:
            self._calculate_stats_from_sqlite()
        else:
            self._calculate_stats_from_json()
    
    def _calculate_stats_from_sqlite(self):
        """Calculate statistics from SQLite history."""
        try:
            with self.db_manager._get_db_connection() as conn:
                # Get total statistics
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM user_history
                ''')
                row = cursor.fetchone()
                if row:
                    self.total_answered = row[0]
                    self.total_correct = row[1]
                
                # Calculate current streak
                self.current_streak = self._calculate_current_streak_sqlite(conn)
                
                # Get best streak
                cursor = conn.execute('SELECT stat_value FROM user_stats WHERE stat_name = ?', ('best_streak',))
                row = cursor.fetchone()
                if row:
                    self.best_streak = int(row[0])
                
                # Calculate category statistics
                self._calculate_category_stats_sqlite(conn)
        
        except Exception as e:
            logger.error(f"Error calculating stats from SQLite: {e}")
    
    def _calculate_current_streak_sqlite(self, conn: sqlite3.Connection) -> int:
        """Calculate current correct answer streak from SQLite."""
        cursor = conn.execute('''
            SELECT is_correct FROM user_history 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        
        streak = 0
        for row in cursor.fetchall():
            if row[0]:  # is_correct
                streak += 1
            else:
                break
        
        return streak
    
    def _calculate_category_stats_sqlite(self, conn: sqlite3.Connection):
        """Calculate per-category statistics from SQLite."""
        cursor = conn.execute('''
            SELECT 
                q.category,
                COUNT(*) as total,
                SUM(CASE WHEN h.is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM user_history h
            LEFT JOIN questions q ON h.question_id = q.id
            WHERE q.category IS NOT NULL
            GROUP BY q.category
        ''')
        
        for row in cursor.fetchall():
            category = row[0]
            self.category_stats[category] = {
                'total': row[1],
                'correct': row[2],
                'accuracy': (row[2] / row[1] * 100) if row[1] > 0 else 0,
                'streak': 0  # Would need more complex query for streak
            }
    
    def _calculate_stats_from_json(self):
        """Calculate statistics from JSON history (legacy)."""
        try:
            from utils.database import load_json_file
            history = load_json_file('linux_plus_history.json')
            
            total_answered = 0
            total_correct = 0
            current_streak = 0
            
            # Process each question's history
            for question_text, data in history.items():
                question_history = data.get('history', [])
                total_answered += len(question_history)
                total_correct += data.get('correct', 0)
                
                # Calculate category from question (simplified)
                category = 'General'  # Would need better category detection
                self.category_stats[category]['total'] += len(question_history)
                self.category_stats[category]['correct'] += data.get('correct', 0)
            
            # Calculate current streak (simplified - from recent entries)
            recent_answers = []
            for data in history.values():
                recent_answers.extend(data.get('history', []))
            
            # Sort by timestamp and get recent streak
            recent_answers.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            for answer in recent_answers[:20]:  # Check last 20 answers
                if answer.get('correct', False):
                    current_streak += 1
                else:
                    break
            
            self.total_answered = total_answered
            self.total_correct = total_correct
            self.current_streak = current_streak
            
        except Exception as e:
            logger.error(f"Error calculating stats from JSON: {e}")
    
    def select_question(self, category: Optional[str] = None, difficulty: Optional[str] = None, 
                       use_spaced_repetition: bool = True) -> Optional[Dict[str, Any]]:
        """
        Select a question using advanced algorithms.
        
        Args:
            category: Filter by category (optional)
            difficulty: Filter by difficulty (optional)
            use_spaced_repetition: Use spaced repetition algorithm
            
        Returns:
            Selected question dictionary or None if no questions available
        """
        available_questions = self._get_available_questions(category, difficulty)
        
        if not available_questions:
            logger.warning("No available questions found")
            return None
        
        # Use spaced repetition or random selection
        if use_spaced_repetition and self.use_database:
            selected = self._select_question_spaced_repetition(available_questions)
        else:
            selected = self._select_question_random(available_questions)
        
        # Mark as asked and set as current
        if selected:
            question_key = self._get_question_key(selected)
            self.asked_questions.add(question_key)
            self.current_question = selected
        
        return selected
    
    def _get_available_questions(self, category: Optional[str] = None, 
                                difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available questions based on filters."""
        available = []
        
        for question in self.questions:
            # Skip already asked questions in this session
            question_key = self._get_question_key(question)
            if question_key in self.asked_questions:
                continue
            
            # Apply category filter
            if category and question.get('category', '') != category:
                continue
            
            # Apply difficulty filter
            if difficulty and question.get('difficulty', '') != difficulty:
                continue
            
            available.append(question)
        
        return available
    
    def _select_question_spaced_repetition(self, available_questions: List[Dict]) -> Optional[Dict]:
        """Select question using spaced repetition algorithm."""
        if not self.db_manager:
            return self._select_question_random(available_questions)
        
        try:
            with self.db_manager._get_db_connection() as conn:
                # Get question performance data
                question_scores = {}
                
                for question in available_questions:
                    question_text = question.get('question_text', question.get('question', ''))
                    
                    # Calculate priority score based on:
                    # 1. Accuracy (lower accuracy = higher priority)
                    # 2. Time since last seen
                    # 3. Number of times seen
                    cursor = conn.execute('''
                        SELECT 
                            COUNT(*) as attempts,
                            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
                            MAX(timestamp) as last_seen
                        FROM user_history 
                        WHERE question_text = ?
                    ''', (question_text,))
                    
                    row = cursor.fetchone()
                    attempts = row[0] if row else 0
                    correct = row[1] if row else 0
                    last_seen = row[2] if row else None
                    
                    # Calculate priority score
                    accuracy = (correct / attempts) if attempts > 0 else 0.5
                    
                    # Time factor (longer time since last seen = higher priority)
                    time_factor = 1.0
                    if last_seen:
                        try:
                            last_datetime = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                            days_since = (datetime.now() - last_datetime).days
                            time_factor = min(days_since / 7, 2.0)  # Max 2x boost for 1+ week old
                        except Exception:
                            pass
                    
                    # Difficulty factor (prioritize harder questions)
                    difficulty_factor = 1.0
                    difficulty = question.get('difficulty', 'Intermediate')
                    if difficulty == 'Advanced':
                        difficulty_factor = 1.2
                    elif difficulty == 'Expert':
                        difficulty_factor = 1.4
                    
                    # Combined priority score (lower accuracy and older questions get higher scores)
                    priority_score = (1 - accuracy) * time_factor * difficulty_factor
                    
                    # Add some randomness to prevent predictability
                    priority_score += random.uniform(-0.1, 0.1)
                    
                    question_scores[question_text] = priority_score
                
                # Select question with highest priority, but use weighted random selection
                # to add some variety
                if question_scores:
                    questions_with_scores = [(q, question_scores[self._get_question_text(q)]) 
                                           for q in available_questions]
                    questions_with_scores.sort(key=lambda x: x[1], reverse=True)
                    
                    # Use weighted selection from top 5 candidates
                    top_candidates = questions_with_scores[:5]
                    weights = [score for _, score in top_candidates]
                    
                    if weights:
                        selected_question = random.choices(
                            [q for q, _ in top_candidates], 
                            weights=weights, 
                            k=1
                        )[0]
                        return selected_question
        
        except Exception as e:
            logger.error(f"Error in spaced repetition selection: {e}")
        
        # Fallback to random selection
        return self._select_question_random(available_questions)
    
    def _select_question_random(self, available_questions: List[Dict]) -> Optional[Dict]:
        """Select a random question from available questions."""
        if not available_questions:
            return None
        
        # Shuffle questions if enabled in settings
        if QUIZ_SETTINGS.get('shuffle_questions', True):
            return random.choice(available_questions)
        else:
            return available_questions[0]
    
    def _get_question_key(self, question: Dict[str, Any]) -> str:
        """Get unique key for a question."""
        return question.get('question_text', question.get('question', str(question.get('id', ''))))
    
    def _get_question_text(self, question: Dict[str, Any]) -> str:
        """Get question text from question dict."""
        return question.get('question_text', question.get('question', ''))
    
    def update_history(self, question: Dict[str, Any], is_correct: bool, 
                      user_answer: Optional[int] = None, time_taken: Optional[int] = None) -> Dict[str, Any]:
        """
        Update question history with enhanced tracking.
        
        Args:
            question: Question dictionary
            is_correct: Whether the answer was correct
            user_answer: Index of user's selected answer
            time_taken: Time taken to answer in seconds
            
        Returns:
            Dictionary with updated statistics and achievements
        """
        # Update session tracking
        self.total_answered += 1
        if is_correct:
            self.total_correct += 1
            self.current_streak += 1
            self.session_points += ACHIEVEMENT_SETTINGS.get('points_per_correct', 10)
            
            # Apply streak bonus
            if self.current_streak >= ACHIEVEMENT_SETTINGS.get('streak_threshold', 5):
                bonus = int(ACHIEVEMENT_SETTINGS.get('points_per_correct', 10) * 
                          ACHIEVEMENT_SETTINGS.get('bonus_streak_multiplier', 1.5))
                self.session_points += bonus
        else:
            self.current_streak = 0
        
        # Update best streak
        if self.current_streak > self.best_streak:
            self.best_streak = self.current_streak
        
        # Update category stats
        category = question.get('category', 'General')
        self.category_stats[category]['total'] += 1
        if is_correct:
            self.category_stats[category]['correct'] += 1
        
        # Add to session questions
        self.session_questions_answered.append({
            'question': question,
            'is_correct': is_correct,
            'user_answer': user_answer,
            'time_taken': time_taken,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save to database/file
        if self.use_database and self.db_manager:
            self._save_history_sqlite(question, is_correct, user_answer, time_taken)
        else:
            self._save_history_json(question, is_correct)
        
        # Check for new achievements
        new_achievements = self._check_achievements()
        
        # Return results
        return {
            'is_correct': is_correct,
            'current_streak': self.current_streak,
            'total_correct': self.total_correct,
            'total_answered': self.total_answered,
            'session_points': self.session_points,
            'new_achievements': new_achievements,
            'accuracy': (self.total_correct / self.total_answered * 100) if self.total_answered > 0 else 0
        }
    
    def _save_history_sqlite(self, question: Dict[str, Any], is_correct: bool,
                           user_answer: Optional[int] = None, time_taken: Optional[int] = None):
        """Save question history to SQLite database."""
        try:
            with self.db_manager._get_db_connection() as conn:
                question_text = self._get_question_text(question)
                correct_answer = question.get('correct_answer_index', 0)
                
                conn.execute('''
                    INSERT INTO user_history 
                    (question_id, question_text, user_answer, correct_answer, is_correct, 
                     timestamp, session_id, time_taken)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    question.get('id'),
                    question_text,
                    user_answer,
                    correct_answer,
                    is_correct,
                    datetime.now().isoformat(),
                    self.session_id,
                    time_taken
                ))
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving history to SQLite: {e}")
    
    def _save_history_json(self, question: Dict[str, Any], is_correct: bool):
        """Save question history to JSON file (legacy)."""
        try:
            from utils.database import load_json_file, save_json_file
            
            history_file = 'linux_plus_history.json'
            history = load_json_file(history_file)
            
            question_text = self._get_question_text(question)
            
            if question_text not in history:
                history[question_text] = {'correct': 0, 'attempts': 0, 'history': []}
            
            history[question_text]['attempts'] += 1
            if is_correct:
                history[question_text]['correct'] += 1
            
            history[question_text]['history'].append({
                'timestamp': datetime.now().isoformat(),
                'correct': is_correct
            })
            
            save_json_file(history_file, history)
        
        except Exception as e:
            logger.error(f"Error saving history to JSON: {e}")
    
    def get_incorrectly_answered(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get questions that were answered incorrectly, prioritized by poor performance.
        
        Args:
            limit: Maximum number of questions to return
            
        Returns:
            List of questions with performance metadata
        """
        if self.use_database and self.db_manager:
            return self._get_incorrect_questions_sqlite(limit)
        else:
            return self._get_incorrect_questions_json(limit)
    
    def _get_incorrect_questions_sqlite(self, limit: int) -> List[Dict[str, Any]]:
        """Get incorrect questions from SQLite with detailed analytics."""
        incorrect_questions = []
        
        try:
            with self.db_manager._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        h.question_text,
                        COUNT(*) as attempts,
                        SUM(CASE WHEN h.is_correct = 1 THEN 1 ELSE 0 END) as correct,
                        AVG(CASE WHEN h.time_taken IS NOT NULL THEN h.time_taken END) as avg_time,
                        MAX(h.timestamp) as last_attempt,
                        q.category,
                        q.difficulty
                    FROM user_history h
                    LEFT JOIN questions q ON h.question_id = q.id
                    GROUP BY h.question_text
                    HAVING correct < attempts  -- Has at least one incorrect answer
                    ORDER BY (correct * 1.0 / attempts) ASC, attempts DESC
                    LIMIT ?
                ''', (limit,))
                
                for row in cursor.fetchall():
                    accuracy = (row[2] / row[1]) * 100 if row[1] > 0 else 0
                    
                    # Find the actual question object
                    question_obj = None
                    for q in self.questions:
                        if self._get_question_text(q) == row[0]:
                            question_obj = q.copy()
                            break
                    
                    if question_obj:
                        question_obj.update({
                            'attempts': row[1],
                            'correct_count': row[2],
                            'accuracy': accuracy,
                            'avg_time': row[3],
                            'last_attempt': row[4],
                            'performance_category': 'Needs Review' if accuracy < 50 else 'Improving'
                        })
                        incorrect_questions.append(question_obj)
        
        except Exception as e:
            logger.error(f"Error getting incorrect questions from SQLite: {e}")
        
        return incorrect_questions
    
    def _get_incorrect_questions_json(self, limit: int) -> List[Dict[str, Any]]:
        """Get incorrect questions from JSON (legacy)."""
        incorrect_questions = []
        
        try:
            from utils.database import load_json_file
            history = load_json_file('linux_plus_history.json')
            
            # Analyze each question's performance
            question_performance = []
            for question_text, data in history.items():
                attempts = data.get('attempts', 0)
                correct = data.get('correct', 0)
                
                if attempts > 0 and correct < attempts:  # Has incorrect answers
                    accuracy = (correct / attempts) * 100
                    question_performance.append({
                        'question_text': question_text,
                        'accuracy': accuracy,
                        'attempts': attempts,
                        'correct_count': correct
                    })
            
            # Sort by worst performance first
            question_performance.sort(key=lambda x: (x['accuracy'], -x['attempts']))
            
            # Find actual question objects
            for perf in question_performance[:limit]:
                for question in self.questions:
                    if self._get_question_text(question) == perf['question_text']:
                        question_copy = question.copy()
                        question_copy.update(perf)
                        incorrect_questions.append(question_copy)
                        break
        
        except Exception as e:
            logger.error(f"Error getting incorrect questions from JSON: {e}")
        
        return incorrect_questions
    
    def get_correct_streak(self) -> int:
        """Get current correct answer streak."""
        return self.current_streak
    
    def get_total_correct(self) -> int:
        """Get total number of correct answers."""
        return self.total_correct
    
    def get_total_answered(self) -> int:
        """Get total number of questions answered."""
        return self.total_answered
    
    def get_category_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed performance statistics by category."""
        performance = {}
        
        for category, stats in self.category_stats.items():
            total = stats['total']
            correct = stats['correct']
            accuracy = (correct / total * 100) if total > 0 else 0
            
            performance[category] = {
                'total': total,
                'correct': correct,
                'accuracy': accuracy,
                'status': self._get_performance_status(accuracy),
                'needs_review': accuracy < 70,  # Below 70% needs review
                'mastery_level': self._get_mastery_level(accuracy, total)
            }
        
        return performance
    
    def _get_performance_status(self, accuracy: float) -> str:
        """Get performance status based on accuracy."""
        if accuracy >= 90:
            return 'Excellent'
        elif accuracy >= 80:
            return 'Good'
        elif accuracy >= 70:
            return 'Fair'
        elif accuracy >= 60:
            return 'Needs Improvement'
        else:
            return 'Needs Review'
    
    def _get_mastery_level(self, accuracy: float, total_questions: int) -> str:
        """Determine mastery level based on accuracy and experience."""
        if total_questions < 5:
            return 'Beginner'
        elif accuracy >= 85 and total_questions >= 20:
            return 'Master'
        elif accuracy >= 75 and total_questions >= 10:
            return 'Proficient'
        elif accuracy >= 65:
            return 'Developing'
        else:
            return 'Novice'
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Generate personalized learning insights and recommendations."""
        insights = {
            'overall_performance': self._calculate_overall_performance(),
            'weak_areas': self._identify_weak_areas(),
            'strong_areas': self._identify_strong_areas(),
            'recommended_focus': self._get_recommended_focus(),
            'study_schedule': self._generate_study_schedule(),
            'progress_trend': self._calculate_progress_trend()
        }
        
        return insights
    
    def _calculate_overall_performance(self) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        accuracy = (self.total_correct / self.total_answered * 100) if self.total_answered > 0 else 0
        
        return {
            'accuracy': accuracy,
            'total_questions': self.total_answered,
            'current_streak': self.current_streak,
            'best_streak': self.best_streak,
            'performance_level': self._get_performance_status(accuracy),
            'estimated_exam_readiness': min(accuracy * 1.2, 100)  # Rough estimate
        }
    
    def _identify_weak_areas(self) -> List[Dict[str, Any]]:
        """Identify categories that need more attention."""
        weak_areas = []
        
        for category, stats in self.category_stats.items():
            if stats['total'] > 0:
                accuracy = stats['correct'] / stats['total'] * 100
                if accuracy < 70 or stats['total'] < 5:  # Low accuracy or insufficient practice
                    weak_areas.append({
                        'category': category,
                        'accuracy': accuracy,
                        'questions_answered': stats['total'],
                        'priority': 'High' if accuracy < 50 else 'Medium'
                    })
        
        # Sort by priority (lowest accuracy first)
        weak_areas.sort(key=lambda x: x['accuracy'])
        return weak_areas
    
    def _identify_strong_areas(self) -> List[Dict[str, Any]]:
        """Identify categories where user performs well."""
        strong_areas = []
        
        for category, stats in self.category_stats.items():
            if stats['total'] >= 5:  # Sufficient data
                accuracy = stats['correct'] / stats['total'] * 100
                if accuracy >= 80:
                    strong_areas.append({
                        'category': category,
                        'accuracy': accuracy,
                        'questions_answered': stats['total'],
                        'mastery_level': self._get_mastery_level(accuracy, stats['total'])
                    })
        
        # Sort by accuracy (highest first)
        strong_areas.sort(key=lambda x: x['accuracy'], reverse=True)
        return strong_areas
    
    def _get_recommended_focus(self) -> Dict[str, Any]:
        """Generate study recommendations based on performance."""
        weak_areas = self._identify_weak_areas()
        
        if not weak_areas:
            return {
                'focus_type': 'maintenance',
                'recommendation': 'Continue practicing all areas to maintain proficiency',
                'priority_categories': []
            }
        
        # Focus on worst performing categories
        priority_categories = weak_areas[:3]  # Top 3 weak areas
        
        return {
            'focus_type': 'improvement',
            'recommendation': f"Focus on {len(priority_categories)} categories that need the most attention",
            'priority_categories': priority_categories,
            'estimated_study_time': len(priority_categories) * 15  # 15 minutes per category
        }
    
    def _generate_study_schedule(self) -> Dict[str, Any]:
        """Generate a personalized study schedule."""
        weak_areas = self._identify_weak_areas()
        total_questions = len(self.questions)
        
        # Calculate recommended daily questions
        if self.total_answered < 50:
            daily_questions = 10  # Beginner pace
        elif self.total_answered < 200:
            daily_questions = 15  # Intermediate pace
        else:
            daily_questions = 20  # Advanced pace
        
        schedule = {
            'daily_questions': daily_questions,
            'focus_rotation': [],
            'weekly_goals': {
                'total_questions': daily_questions * 7,
                'accuracy_target': 75,
                'categories_to_improve': len(weak_areas)
            }
        }
        
        # Create focus rotation for the week
        if weak_areas:
            for i in range(7):  # 7 days
                focus_category = weak_areas[i % len(weak_areas)]['category']
                schedule['focus_rotation'].append({
                    'day': i + 1,
                    'focus_category': focus_category,
                    'question_count': daily_questions
                })
        
        return schedule
    
    def _calculate_progress_trend(self) -> Dict[str, Any]:
        """Calculate learning progress trend over time."""
        # This would require more detailed historical analysis
        # For now, return a simplified trend based on recent performance
        
        recent_accuracy = self.current_streak / max(self.current_streak + 5, 10) * 100
        overall_accuracy = (self.total_correct / self.total_answered * 100) if self.total_answered > 0 else 0
        
        if recent_accuracy > overall_accuracy + 5:
            trend = 'improving'
        elif recent_accuracy < overall_accuracy - 5:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'recent_accuracy': recent_accuracy,
            'overall_accuracy': overall_accuracy,
            'trend_strength': abs(recent_accuracy - overall_accuracy)
        }
    
    def _check_achievements(self) -> List[str]:
        """Check for newly earned achievements."""
        new_achievements = []
        
        # Current achievement checks
        if self.current_streak >= 10 and 'streak_10' not in self.achievements.get('badges', []):
            new_achievements.append('streak_10')
        
        if self.current_streak >= 25 and 'streak_25' not in self.achievements.get('badges', []):
            new_achievements.append('streak_25')
        
        if self.total_correct >= 100 and 'questions_100' not in self.achievements.get('badges', []):
            new_achievements.append('questions_100')
        
        if self.total_correct >= 500 and 'questions_500' not in self.achievements.get('badges', []):
            new_achievements.append('questions_500')
        
        # Category mastery achievements
        for category, stats in self.category_stats.items():
            if stats['total'] >= 20 and (stats['correct'] / stats['total']) >= 0.9:
                achievement_name = f'master_{category.lower().replace(" ", "_")}'
                if achievement_name not in self.achievements.get('badges', []):
                    new_achievements.append(achievement_name)
        
        # Save new achievements
        if new_achievements:
            self._save_achievements(new_achievements)
        
        return new_achievements
    
    def _save_achievements(self, new_achievements: List[str]):
        """Save newly earned achievements."""
        # Add to current achievements
        if 'badges' not in self.achievements:
            self.achievements['badges'] = []
        
        self.achievements['badges'].extend(new_achievements)
        self.achievements['points_earned'] += len(new_achievements) * 50  # 50 points per achievement
        
        # Update best streak
        if self.current_streak > self.achievements.get('streaks', {}).get('best', 0):
            if 'streaks' not in self.achievements:
                self.achievements['streaks'] = {}
            self.achievements['streaks']['best'] = self.current_streak
        
        # Save to database or file
        if self.use_database and self.db_manager:
            self._save_achievements_sqlite(new_achievements)
        else:
            self._save_achievements_json()
    
    def _save_achievements_sqlite(self, new_achievements: List[str]):
        """Save achievements to SQLite database."""
        try:
            with self.db_manager._get_db_connection() as conn:
                # Save new badges
                for achievement in new_achievements:
                    conn.execute('''
                        INSERT OR IGNORE INTO achievements 
                        (achievement_type, achievement_name, points_value)
                        VALUES (?, ?, ?)
                    ''', ('badge', achievement, 50))
                
                # Update total points
                conn.execute('''
                    INSERT OR REPLACE INTO user_stats (stat_name, stat_value)
                    VALUES (?, ?)
                ''', ('total_points', str(self.achievements['points_earned'])))
                
                # Update best streak
                conn.execute('''
                    INSERT OR REPLACE INTO user_stats (stat_name, stat_value)
                    VALUES (?, ?)
                ''', ('best_streak', str(self.best_streak)))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving achievements to SQLite: {e}")
    
    def _save_achievements_json(self):
        """Save achievements to JSON file (legacy)."""
        try:
            from utils.database import save_json_file
            save_json_file('linux_plus_achievements.json', self.achievements)
        except Exception as e:
            logger.error(f"Error saving achievements to JSON: {e}")
    
    def save_history(self):
        """Save question history using database manager."""
        try:
            self.db_manager.save_history(self.history)
            logger.info("History saved successfully")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            # Fallback to JSON if database save fails
            try:
                self.db_manager.save_json_file(self.history_file, self.history)
                logger.warning("History saved to JSON fallback")
            except Exception as json_error:
                logger.error(f"Failed to save history to JSON: {json_error}")
    
    def _save_session_summary_sqlite(self):
        """Save session summary to database."""
        try:
            with self.db_manager._get_db_connection() as conn:
                session_data = {
                    'session_id': self.session_id,
                    'questions_answered': len(self.session_questions_answered),
                    'points_earned': self.session_points,
                    'start_time': self.session_start_time.isoformat(),
                    'end_time': datetime.now().isoformat()
                }
                
                conn.execute('''
                    INSERT OR REPLACE INTO user_stats (stat_name, stat_value)
                    VALUES (?, ?)
                ''', (f'session_{self.session_id}', json.dumps(session_data)))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error saving session summary: {e}")
    
    def save_achievements(self):
        """Save achievements data."""
        # Achievements are saved in real-time, this is for compatibility
        pass
    
    def reset_session(self):
        """Reset current session state."""
        self.session_id = str(uuid.uuid4())
        self.session_start_time = datetime.now()
        self.session_points = 0
        self.session_questions_answered = []
        self.asked_questions.clear()
        self.current_question = None
        
        logger.info(f"New session started: {self.session_id}")