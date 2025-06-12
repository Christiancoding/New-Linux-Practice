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

        # Add caching to reduce lag
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # Cache static files for 5 minutes
        self.app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable template auto-reload in production
        
        # Session configuration for better performance
        self.app.secret_key = 'your-secret-key-here'  # Add a proper secret key
        self.app.config['SESSION_TYPE'] = 'filesystem'
        self.app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

        from controllers.quiz_controller import QuizController
        from controllers.stats_controller import StatsController
        
        self.quiz_controller = QuizController(game_state)
        self.stats_controller = StatsController(game_state)
        
        self.setup_routes()
    # Add these methods to the LinuxPlusStudyWeb class after __init__

    def toggle_fullscreen(self, enable=True):
        """Toggle application window fullscreen."""
        try:
            if hasattr(self, 'window') and self.window:
                self.window.fullscreen = enable
                return {'success': True, 'fullscreen': enable}
            return {'success': False, 'error': 'Window not available'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def is_fullscreen(self):
        """Check if window is in fullscreen mode."""
        try:
            if hasattr(self, 'window') and self.window:
                return {'success': True, 'fullscreen': getattr(self.window, 'fullscreen', False)}
            return {'success': False, 'fullscreen': False}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    def reset_quiz_state(self):
        """Reset quiz state variables."""
        self.quiz_active = False
        self.current_quiz_mode = None
        self.current_category_filter = None
        self.current_question_data = None
        self.current_question_index = -1
        self.current_streak = 0
        self.quick_fire_start_time = None
        self.quick_fire_questions_answered = 0
    def setup_routes(self):
        """Setup Flask routes for the web interface."""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/quiz')
        def quiz_page():
            return render_template('quiz.html')
        
        @self.app.route('/stats')
        def stats_page():
            return render_template('stats.html')
        
        @self.app.route('/achievements')
        def achievements_page():
            return render_template('achievements.html')
        
        @self.app.route('/review')
        def review_page():
            return render_template('review.html')
        
        @self.app.route('/settings')
        def settings_page():
            return render_template('settings.html')
        
        @self.app.route('/api/status')
        def api_status():
            try:
                # Use quiz controller as single source of truth
                status = self.quiz_controller.get_session_status()
                return jsonify({
                    'quiz_active': status['quiz_active'],
                    'total_questions': len(self.game_state.questions),
                    'categories': sorted(list(self.game_state.categories)),
                    'session_score': status['session_score'],
                    'session_total': status['session_total'],
                    'current_streak': status['current_streak'],
                    'total_points': self.game_state.achievements.get('points_earned', 0),
                    'session_points': self.game_state.session_points,
                    'quiz_mode': status['mode']
                })
            except Exception as e:
                return jsonify({
                    'quiz_active': False,
                    'total_questions': len(self.game_state.questions),
                    'categories': sorted(list(self.game_state.categories)),
                    'session_score': 0,
                    'session_total': 0,
                    'current_streak': 0,
                    'total_points': 0,
                    'session_points': 0,
                    'quiz_mode': None,
                    'error': str(e)
                })
        
        @self.app.route('/api/start_quiz', methods=['POST'])
        def api_start_quiz():
            try:
                data = request.get_json()
                quiz_mode = data.get('mode', 'standard')
                category = data.get('category')
                
                # Force end any existing session to ensure clean state
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(
                    mode=quiz_mode,
                    category_filter=None if category == "All Categories" else category
                )
                
                if result.get('session_active'):
                    return jsonify({'success': True, **result})
                else:
                    return jsonify({'success': False, 'error': 'Failed to start quiz session'})
                    
            except Exception as e:
                print(f"Error starting quiz: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/get_question')
        def api_get_question():
            try:
                # Validate session state
                if not self.quiz_controller.quiz_active:
                    return jsonify({'quiz_complete': True, 'error': 'No active quiz session'})
                
                # Check if we have a cached current question first
                cached_question = self.quiz_controller.get_current_question()
                if cached_question:
                    # Return cached question data
                    q_text, options, _, category, _ = cached_question['question_data']
                    return jsonify({
                        'question': q_text,
                        'options': options,
                        'category': category,
                        'question_number': cached_question.get('question_number', 1),
                        'streak': cached_question.get('streak', 0),
                        'mode': self.quiz_controller.current_quiz_mode,
                        'is_single_question': self.quiz_controller.current_quiz_mode in ['daily_challenge', 'pop_quiz'],
                        'quiz_complete': False,
                        'quick_fire_remaining': cached_question.get('quick_fire_remaining'),
                        'from_cache': True  # Debug flag
                    })
                
                # Get new question
                result = self.quiz_controller.get_next_question(
                    self.quiz_controller.category_filter if hasattr(self.quiz_controller, 'category_filter') else None
                )
                
                if result is None:
                    # Session complete
                    session_results = self.quiz_controller.force_end_session()
                    return jsonify({'quiz_complete': True, **session_results})
                
                # Format response for web interface
                q_text, options, _, category, _ = result['question_data']
                
                return jsonify({
                    'question': q_text,
                    'options': options,
                    'category': category,
                    'question_number': result.get('question_number', 1),
                    'streak': result.get('streak', 0),
                    'mode': self.quiz_controller.current_quiz_mode,
                    'is_single_question': self.quiz_controller.current_quiz_mode in ['daily_challenge', 'pop_quiz'],
                    'quiz_complete': False,
                    'quick_fire_remaining': result.get('quick_fire_remaining'),
                    'from_cache': False  # Debug flag
                })
                
            except Exception as e:
                print(f"Error in get_question: {e}")
                # Force end session on error to prevent stuck state
                try:
                    self.quiz_controller.force_end_session()
                except:
                    pass
                return jsonify({'error': str(e), 'quiz_complete': True})

        @self.app.route('/api/submit_answer', methods=['POST'])
        def api_submit_answer():
            try:
                data = request.get_json()
                user_answer_index = data.get('answer_index')
                
                # Validate session and question state
                if not self.quiz_controller.quiz_active:
                    return jsonify({'error': 'No active quiz session'})
                
                # Get current question from controller
                current_question = self.quiz_controller.get_current_question()
                if current_question is None:
                    return jsonify({'error': 'No current question available'})
                
                question_data = current_question['question_data']
                question_index = current_question['original_index']
                
                result = self.quiz_controller.submit_answer(
                    question_data, 
                    user_answer_index, 
                    question_index
                )
                
                # Clear current question cache after processing
                self.quiz_controller.clear_current_question_cache()
                
                return jsonify(result)
                
            except Exception as e:
                print(f"Error in submit_answer: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/end_quiz', methods=['POST'])
        def api_end_quiz():
            try:
                if not self.quiz_controller.quiz_active:
                    return jsonify({'success': True, 'message': 'No active quiz session'})
                
                result = self.quiz_controller.force_end_session()
                
                return jsonify({'success': True, **result})
                
            except Exception as e:
                print(f"Error in end_quiz: {e}")
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/quick_fire_status')
        def api_quick_fire_status():
            try:
                if self.quiz_controller.quick_fire_active:
                    result = self.quiz_controller.check_quick_fire_status()
                    return jsonify(result)
                else:
                    return jsonify({'active': False})
            except Exception as e:
                return jsonify({'active': False, 'error': str(e)})
        
        # Special mode starters - simplified
        @self.app.route('/api/start_quick_fire', methods=['POST'])
        def api_start_quick_fire():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="quick_fire")
                self.current_quiz_mode = "quick_fire"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/start_daily_challenge', methods=['POST'])
        def api_start_daily_challenge():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="daily_challenge")
                self.current_quiz_mode = "daily_challenge"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/start_pop_quiz', methods=['POST'])
        def api_start_pop_quiz():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="pop_quiz")
                self.current_quiz_mode = "pop_quiz"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/start_mini_quiz', methods=['POST'])
        def api_start_mini_quiz():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="mini_quiz")
                self.current_quiz_mode = "mini_quiz"
                self.current_category_filter = None
                
                return jsonify({'success': True, **result})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # Other API routes remain the same...
        @self.app.route('/api/statistics')
        def api_statistics():
            try:
                return jsonify(self.stats_controller.get_detailed_statistics())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/achievements')
        def api_achievements():
            try:
                return jsonify(self.stats_controller.get_achievements_data())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/leaderboard')
        def api_leaderboard():
            try:
                return jsonify(self.stats_controller.get_leaderboard_data())
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/clear_statistics', methods=['POST'])
        def api_clear_statistics():
            try:
                success = self.stats_controller.clear_statistics()
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/review_incorrect')
        def api_review_incorrect():
            try:
                return jsonify(self.stats_controller.get_review_questions_data())
            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/remove_from_review', methods=['POST'])
        def api_remove_from_review():
            try:
                data = request.get_json()
                question_text = data.get('question_text')
                if not question_text:
                    return jsonify({'success': False, 'error': 'No question text provided'})
                
                success = self.stats_controller.remove_from_review_list(question_text)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/export_history')
        def api_export_history():
            try:
                from flask import make_response
                
                export_data = self.game_state.study_history.copy()
                export_data["export_metadata"] = {
                    "export_date": datetime.now().isoformat(),
                    "total_questions_in_pool": len(self.game_state.questions),
                    "categories_available": list(self.game_state.categories)
                }
                
                response = make_response(json.dumps(export_data, indent=2))
                response.headers['Content-Type'] = 'application/json'
                response.headers['Content-Disposition'] = f'attachment; filename=linux_plus_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                
                return response
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.errorhandler(404)
        def not_found_error(error):
            return render_template('error.html', error="Page not found"), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return render_template('error.html', error="Internal server error"), 500
        
        @self.app.route('/api/save_settings', methods=['POST'])
        def api_save_settings():
            try:
                data = request.get_json()
                settings = {
                    'focusMode': data.get('focusMode', False),
                    'breakReminder': data.get('breakReminder', 10),
                    'timestamp': time.time()
                }
                
                # Save to a simple file (you could also use the game_state)
                import json
                with open('web_settings.json', 'w') as f:
                    json.dump(settings, f)
                
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/load_settings')
        def api_load_settings():
            try:
                import json
                try:
                    with open('web_settings.json', 'r') as f:
                        settings = json.load(f)
                    return jsonify({'success': True, 'settings': settings})
                except FileNotFoundError:
                    # Return defaults
                    return jsonify({'success': True, 'settings': {'focusMode': False, 'breakReminder': 10}})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        # Add these routes in the setup_routes method after the existing routes

        @self.app.route('/api/set_fullscreen', methods=['POST'])
        def api_set_fullscreen():
            try:
                data = request.get_json()
                enable = data.get('enable', True)
                result = self.toggle_fullscreen(enable)
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/get_fullscreen_status')
        def api_get_fullscreen_status():
            try:
                result = self.is_fullscreen()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
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
        window = webview.create_window(
            title='Linux+ Study Game',
            url='http://127.0.0.1:5000',
            width=1200,
            height=900,
            min_size=(800, 600),
            resizable=True
        )
        
        # Store window reference for fullscreen control
        self.window = window
        
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