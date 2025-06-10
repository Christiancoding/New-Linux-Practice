#!/usr/bin/env python3
"""
Web View for the Linux+ Study Game using Flask + pywebview.
Creates a desktop app with modern web interface.
"""

import webview
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, session
import os
import json
from datetime import datetime
import hashlib
import time
import logging
import traceback
from utils.config import (
    QUICK_FIRE_QUESTIONS, QUICK_FIRE_TIME_LIMIT, MINI_QUIZ_QUESTIONS,
    POINTS_PER_CORRECT, POINTS_PER_INCORRECT, STREAK_BONUS_THRESHOLD, STREAK_BONUS_MULTIPLIER
)


class LinuxPlusStudyWeb:
    """Web interface using Flask + pywebview for desktop app experience."""
    
    def __init__(self, game_state, debug=False):
        self.game_state = game_state
        self.app = Flask(__name__, 
                         template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
                         static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
        self.debug = debug
        self.window = None
        
        self.game_state = game_state
        self.app = Flask(__name__, ...)
        self.debug = debug
        self.window = None

        from controllers.quiz_controller import QuizController
        from controllers.stats_controller import StatsController
        
        self.quiz_controller = QuizController(game_state)
        self.stats_controller = StatsController(game_state)
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes for the web interface."""
        
        @self.app.route('/')
        def index():
            """Main page."""
            return render_template('index.html')
        
        @self.app.route('/quiz')
        def quiz_page():
            """Quiz interface page."""
            return render_template('quiz.html')
        
        @self.app.route('/stats')
        def stats_page():
            """Statistics page."""
            return render_template('stats.html')
        
        @self.app.route('/achievements')
        def achievements_page():
            """Achievements page."""
            return render_template('achievements.html')
        
        # API Routes
        @self.app.route('/api/status')
        def api_status():
            """Get current game status."""
            return jsonify({
                'quiz_active': self.quiz_active,
                'total_questions': len(self.game_state.questions),
                'categories': sorted(list(self.game_state.categories)),
                'session_score': self.game_state.score,
                'session_total': self.game_state.total_questions_session,
                'current_streak': self.current_streak,
                'total_points': self.game_state.achievements.get('points_earned', 0),
                'session_points': self.game_state.session_points
            })
        
        @self.app.route('/api/start_quiz', methods=['POST'])
        def api_start_quiz():
            data = request.get_json()
            quiz_mode = data.get('mode', 'standard')
            category = data.get('category')
            
            result = self.quiz_controller.start_quiz_session(
                mode=quiz_mode,
                category_filter=None if category == "All Categories" else category
            )
            
            return jsonify(result)
        @self.app.route('/api/get_question')
        def api_get_question():
            result = self.quiz_controller.get_next_question()
            if result is None:
                return jsonify({'quiz_complete': True})
            return jsonify(result)

        @self.app.route('/api/submit_answer', methods=['POST'])
        def api_submit_answer():
            data = request.get_json()
            user_answer_index = data.get('answer_index')
            
            if not self.quiz_controller.quiz_active:
                return jsonify({'error': 'No active quiz session'})
            
            # Get current question from controller
            question_data = self.quiz_controller.current_question_data
            original_index = self.quiz_controller.current_question_index
            
            result = self.quiz_controller.submit_answer(
                question_data, user_answer_index, original_index
            )
            
            return jsonify(result)
        
        @self.app.route('/api/end_quiz', methods=['POST'])
        def api_end_quiz():
            """End the current quiz session."""
            if not self.quiz_active:
                return jsonify({'error': 'No active quiz session'})
            
            self.quiz_active = False
            
            # Calculate final stats
            accuracy = (self.game_state.score / self.game_state.total_questions_session * 100) if self.game_state.total_questions_session > 0 else 0
            
            # Update leaderboard
            if self.game_state.total_questions_session > 0:
                self.game_state.update_leaderboard(
                    self.game_state.score,
                    self.game_state.total_questions_session,
                    self.game_state.session_points
                )
            
            # Check for perfect session
            if accuracy == 100 and self.game_state.total_questions_session >= 3:
                if "perfect_session" not in self.game_state.achievements["badges"]:
                    self.game_state.achievements["badges"].append("perfect_session")
            
            self.game_state.save_history()
            self.game_state.save_achievements()
            
            return jsonify({
                'session_score': self.game_state.score,
                'session_total': self.game_state.total_questions_session,
                'accuracy': accuracy,
                'session_points': self.game_state.session_points
            })
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """Get detailed statistics."""
            from controllers.stats_controller import StatsController
            stats_controller = StatsController(self.game_state)
            return jsonify(stats_controller.get_detailed_statistics())
        
        @self.app.route('/api/achievements')
        def api_achievements():
            """Get achievements data."""
            from controllers.stats_controller import StatsController
            stats_controller = StatsController(self.game_state)
            return jsonify(stats_controller.get_achievements_data())
        
        @self.app.route('/api/leaderboard')
        def api_leaderboard():
            """Get leaderboard data."""
            from controllers.stats_controller import StatsController
            stats_controller = StatsController(self.game_state)
            return jsonify(stats_controller.get_leaderboard_data())
        
        @self.app.route('/api/clear_statistics', methods=['POST'])
        def api_clear_statistics():
            """Clear all statistics."""
            try:
                from controllers.stats_controller import StatsController
                stats_controller = StatsController(self.game_state)
                success = stats_controller.clear_statistics()
                
                if success:
                    return jsonify({'success': True, 'message': 'Statistics cleared'})
                else:
                    return jsonify({'success': False, 'error': 'Failed to clear statistics'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        @self.app.route('/api/start_quick_fire', methods=['POST'])
        def api_start_quick_fire():
            """Start Quick Fire mode."""
            if self.quiz_active:
                return jsonify({'error': 'Quiz already active'})
            
            # Initialize Quick Fire session
            self.game_state.score = 0
            self.game_state.total_questions_session = 0
            self.game_state.answered_indices_session = []
            self.game_state.session_points = 0
            self.current_streak = 0
            
            self.quiz_active = True
            self.current_quiz_mode = "quick_fire"
            self.current_category_filter = None
            self.quick_fire_start_time = time.time()
            self.quick_fire_questions_answered = 0
            
            return jsonify({
                'success': True, 
                'mode': 'quick_fire',
                'time_limit': QUICK_FIRE_TIME_LIMIT,
                'question_limit': QUICK_FIRE_QUESTIONS,
                'start_time': self.quick_fire_start_time
            })

        @self.app.route('/api/quick_fire_status')
        def api_quick_fire_status():
            """Get Quick Fire mode status."""
            if not self.quiz_active or self.current_quiz_mode != "quick_fire":
                return jsonify({'active': False})
            
            elapsed = time.time() - self.quick_fire_start_time
            time_remaining = max(0, QUICK_FIRE_TIME_LIMIT - elapsed)
            questions_remaining = max(0, QUICK_FIRE_QUESTIONS - self.quick_fire_questions_answered)
            
            # Check if Quick Fire should end
            time_up = elapsed >= QUICK_FIRE_TIME_LIMIT
            questions_complete = self.quick_fire_questions_answered >= QUICK_FIRE_QUESTIONS
            
            return jsonify({
                'active': True,
                'elapsed_time': elapsed,
                'time_remaining': time_remaining,
                'questions_answered': self.quick_fire_questions_answered,
                'questions_remaining': questions_remaining,
                'time_up': time_up,
                'questions_complete': questions_complete,
                'should_end': time_up or questions_complete
            })

        @self.app.route('/api/start_daily_challenge', methods=['POST'])
        def api_start_daily_challenge():
            """Start daily challenge."""
            if self.quiz_active:
                return jsonify({'error': 'Quiz already active'})
            
            today_iso = datetime.now().date().isoformat()
            
            # Check if already completed today
            if (self.last_daily_challenge_date == today_iso and 
                self.daily_challenge_completed):
                return jsonify({'error': 'Daily challenge already completed today'})
            
            # Get daily question using date-based seeding
            date_hash = int(hashlib.md5(today_iso.encode()).hexdigest()[:8], 16)
            if not self.game_state.questions:
                return jsonify({'error': 'No questions available'})
            
            question_index = date_hash % len(self.game_state.questions)
            question_data = self.game_state.questions[question_index]
            
            # Initialize session
            self.game_state.score = 0
            self.game_state.total_questions_session = 0
            self.game_state.answered_indices_session = []
            self.game_state.session_points = 0
            self.current_streak = 0
            
            self.quiz_active = True
            self.current_quiz_mode = "daily_challenge"
            self.current_category_filter = None
            self.current_question_data = question_data
            self.current_question_index = question_index
            self.last_daily_challenge_date = today_iso
            
            q_text, options, correct_idx, category, explanation = question_data
            
            return jsonify({
                'success': True,
                'mode': 'daily_challenge',
                'question': q_text,
                'options': options,
                'category': category,
                'date': today_iso
            })

        @self.app.route('/api/start_pop_quiz', methods=['POST'])
        def api_start_pop_quiz():
            """Start pop quiz (single random question)."""
            if self.quiz_active:
                return jsonify({'error': 'Quiz already active'})
            
            # Get random question
            question_data, original_index = self.game_state.select_question(None)
            if question_data is None:
                return jsonify({'error': 'No questions available'})
            
            # Initialize session
            self.game_state.score = 0
            self.game_state.total_questions_session = 0
            self.game_state.answered_indices_session = []
            self.game_state.session_points = 0
            self.current_streak = 0
            
            self.quiz_active = True
            self.current_quiz_mode = "pop_quiz"
            self.current_category_filter = None
            self.current_question_data = question_data
            self.current_question_index = original_index
            
            q_text, options, correct_idx, category, explanation = question_data
            
            return jsonify({
                'success': True,
                'mode': 'pop_quiz',
                'question': q_text,
                'options': options,
                'category': category
            })

        @self.app.route('/api/start_mini_quiz', methods=['POST'])
        def api_start_mini_quiz():
            """Start mini quiz (3 questions)."""
            if self.quiz_active:
                return jsonify({'error': 'Quiz already active'})
            
            # Initialize session
            self.game_state.score = 0
            self.game_state.total_questions_session = 0
            self.game_state.answered_indices_session = []
            self.game_state.session_points = 0
            self.current_streak = 0
            
            self.quiz_active = True
            self.current_quiz_mode = "mini_quiz"
            self.current_category_filter = None
            
            return jsonify({
                'success': True, 
                'mode': 'mini_quiz',
                'question_limit': MINI_QUIZ_QUESTIONS
            })
        @self.app.route('/api/review_incorrect')
        def api_review_incorrect():
            """Get incorrect questions for review."""
            from controllers.stats_controller import StatsController
            stats_controller = StatsController(self.game_state)
            return jsonify(stats_controller.get_review_questions_data())

        @self.app.route('/api/remove_from_review', methods=['POST'])
        def api_remove_from_review():
            """Remove question from review list."""
            data = request.get_json()
            question_text = data.get('question_text')
            if not question_text:
                return jsonify({'success': False, 'error': 'No question text provided'})
            
            from controllers.stats_controller import StatsController
            stats_controller = StatsController(self.game_state)
            success = stats_controller.remove_from_review_list(question_text)
            
            return jsonify({'success': success})

        @self.app.route('/api/export_history')
        def api_export_history():
            """Export study history as JSON download."""
            from flask import make_response
            import json
            from datetime import datetime
            
            try:
                # Create export data
                export_data = self.game_state.study_history.copy()
                export_data["export_metadata"] = {
                    "export_date": datetime.now().isoformat(),
                    "total_questions_in_pool": len(self.game_state.questions),
                    "categories_available": list(self.game_state.categories)
                }
                
                # Create response
                response = make_response(json.dumps(export_data, indent=2))
                response.headers['Content-Type'] = 'application/json'
                response.headers['Content-Disposition'] = f'attachment; filename=linux_plus_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                
                return response
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        @self.app.route('/review')
        def review_page():
            """Review incorrect answers page."""
            return render_template('review.html')
        @self.app.errorhandler(404)
        def not_found_error(error):
            return render_template('error.html', error="Page not found"), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return render_template('error.html', error="Internal server error"), 500
        @self.app.route('/settings')
        def settings_page():
            """Settings page."""
            return render_template('settings.html')
    def handle_api_errors(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logging.error(f"API Error in {f.__name__}: {str(e)}")
                logging.error(traceback.format_exc())
                return jsonify({
                    'error': f'Server error: {str(e)}',
                    'success': False
                }), 500
        wrapper.__name__ = f.__name__
        return wrapper
    
    def run_flask_app(self):
        """Run the Flask app in a separate thread."""
        self.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    
    def start(self):
        """Start the web interface in a desktop window."""
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=self.run_flask_app, daemon=True)
        flask_thread.start()
        
        # Wait a moment for Flask to start
        time.sleep(1)
        
        # Create the desktop window
        self.window = webview.create_window(
            title='Linux+ Study Game',
            url='http://127.0.0.1:5000',
            width=1200,
            height=900,
            min_size=(800, 600),
            resizable=True
        )
        
        # Start the webview (this blocks until window is closed)
        webview.start(debug=self.debug)
    
    def quit_app(self):
        """Clean shutdown of the application."""
        # Save any pending data
        self.game_state.save_history()
        self.game_state.save_achievements()
        
        # Close the webview window
        if self.window:
            self.window.destroy()