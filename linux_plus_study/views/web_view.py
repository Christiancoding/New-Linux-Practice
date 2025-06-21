#!/usr/bin/env python3
"""
FastAPI Web View for the Linux+ Study Game.
Modern ASGI-based web interface with async support.
"""

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
import logging
import asyncio
import time
from datetime import datetime
import traceback
from pathlib import Path
import re

# Import your existing controllers and utilities
from utils.cli_playground import get_cli_playground
from utils.config import (
    QUICK_FIRE_QUESTIONS, QUICK_FIRE_TIME_LIMIT, MINI_QUIZ_QUESTIONS,
    POINTS_PER_CORRECT, POINTS_PER_INCORRECT, STREAK_BONUS_THRESHOLD, STREAK_BONUS_MULTIPLIER
)

# Pydantic models for request/response validation
class QuizStartRequest(BaseModel):
    mode: str = "standard"
    category: Optional[str] = None

class AnswerSubmissionRequest(BaseModel):
    answer_index: int  # Changed from 'answer' to 'answer_index' to match frontend
    question_id: Optional[str] = None

class SettingsRequest(BaseModel):
    focusMode: bool = False
    breakReminder: int = 10

class CLICommandRequest(BaseModel):
    command: str

class FullscreenRequest(BaseModel):
    enable: bool = True

class LinuxPlusStudyFastAPI:
    """FastAPI-based web interface with modern async capabilities."""
    
    def __init__(self, game_state, debug: bool = False):
        self.game_state = game_state
        self.debug = debug
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Linux+ Study Game",
            description="Interactive Linux+ certification preparation tool",
            version="2.0.0",
            docs_url="/api/docs",  # Always enable docs for testing
            redoc_url="/api/redoc"  # Always enable redoc
        )
        
        # Setup paths
        self.base_dir = Path(__file__).parent.parent
        self.template_dir = self.base_dir / "templates"
        self.static_dir = self.base_dir / "static"
        
        # Initialize templates
        self.templates = Jinja2Templates(directory=str(self.template_dir))
        
        # Initialize CLI playground
        self.cli_playground = get_cli_playground()
        
        # Import controllers
        from controllers.quiz_controller import QuizController
        from controllers.stats_controller import StatsController
        
        self.quiz_controller = QuizController(game_state)
        self.stats_controller = StatsController(game_state)
        
        # Initialize session state
        self.current_category_filter = None
        self.current_question_data = None
        self.current_question_index = -1
        
        # Setup middleware and routes
        self.setup_middleware()
        self.setup_static_files()
        self.setup_routes()
    
    def setup_middleware(self):
        """Configure FastAPI middleware."""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware for security
        self.app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["127.0.0.1", "localhost", "*.localhost"]
        )
    
    def setup_static_files(self):
        """Mount static file directories."""
        # Mount static files with proper configuration
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
    
    def setup_routes(self):
        """Setup all FastAPI routes."""
        
        # HTML page routes
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("index.html", context)
        
        @self.app.get("/quiz", response_class=HTMLResponse)
        async def quiz_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("quiz.html", context)
        
        @self.app.get("/stats", response_class=HTMLResponse)
        async def stats_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("stats.html", context)
        
        @self.app.get("/achievements", response_class=HTMLResponse)
        async def achievements_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("achievements.html", context)
        
        @self.app.get("/review", response_class=HTMLResponse)
        async def review_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("review.html", context)
        
        @self.app.get("/settings", response_class=HTMLResponse)
        async def settings_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("settings.html", context)
        
        @self.app.get("/cli-playground", response_class=HTMLResponse)
        async def cli_playground_page(request: Request):
            context = self.get_template_context(request)
            context.update({
                "title": "CLI Playground",
                "active_page": "cli_playground"
            })
            return self.templates.TemplateResponse("cli_playground.html", context)
        
        # API Status endpoint
        @self.app.get("/api/status")
        async def api_status():
            try:
                status = self.quiz_controller.get_session_status()
                return {
                    "quiz_active": status["quiz_active"],
                    "total_questions": len(self.game_state.questions),
                    "categories": sorted(list(self.game_state.categories)),
                    "session_score": status["session_score"],
                    "session_total": status["session_total"],
                    "current_streak": status["current_streak"],
                    "total_points": self.game_state.achievements.get("points_earned", 0),
                    "session_points": self.game_state.session_points,
                    "quiz_mode": status["mode"]
                }
            except Exception as e:
                return {
                    "quiz_active": False,
                    "total_questions": len(self.game_state.questions),
                    "categories": sorted(list(self.game_state.categories)),
                    "session_score": 0,
                    "session_total": 0,
                    "current_streak": 0,
                    "total_points": 0,
                    "session_points": 0,
                    "quiz_mode": None,
                    "error": str(e)
                }
        
        # Review incorrect answers endpoint
        @self.app.get("/api/review_incorrect")
        async def api_review_incorrect():
            try:
                incorrect = self.game_state.get_incorrectly_answered()
                return {
                    "success": True,
                    "questions": [q.to_dict() for q in incorrect],
                    "count": len(incorrect)
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Refresh data endpoint (helps with UI updates after import)
        @self.app.post("/api/refresh")
        async def refresh_data():
            try:
                # Categories are automatically managed by QuestionManager
                # No need to manually update them
                categories = sorted(list(self.game_state.categories))
                
                return {
                    "success": True,
                    "total_questions": len(self.game_state.questions),
                    "categories": categories,
                    "message": "Data refreshed successfully"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Quiz management endpoints
        @self.app.post("/api/start_quiz")
        async def api_start_quiz(quiz_request: QuizStartRequest):
            try:
                category_filter = None if quiz_request.category == "All Categories" else quiz_request.category
                
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(
                    mode=quiz_request.mode,
                    category_filter=category_filter
                )
                
                self.current_category_filter = category_filter
                
                if result.get("session_active"):
                    return {"success": True, **result}
                else:
                    raise HTTPException(status_code=400, detail="Failed to start quiz session")
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/get_question")
        async def api_get_question():
            try:
                if not self.quiz_controller.quiz_active:
                    return {"quiz_complete": True, "error": "No active quiz session"}
                
                # First, check if there's already a current question
                current_question = self.quiz_controller.get_current_question()
                
                if current_question is None:
                    # Get next question if no current question
                    current_question = self.quiz_controller.get_next_question(
                        self.current_category_filter
                    )
                
                if current_question is None:
                    # No more questions - quiz complete
                    results = self.quiz_controller.end_session()
                    return {
                        "quiz_complete": True,
                        "success": True,
                        "results": results
                    }
                
                # Format question for response
                question_data = current_question['question_data']
                q_text, options, _, category, _ = question_data
                
                return {
                    "question": q_text,
                    "options": options,
                    "category": category,
                    "question_number": current_question.get('question_number', 1),
                    "streak": current_question.get('streak', 0),
                    "mode": self.quiz_controller.current_quiz_mode,
                    "is_single_question": self.quiz_controller.current_quiz_mode in ['daily_challenge', 'pop_quiz'],
                    "quiz_complete": False,
                    "quick_fire_remaining": current_question.get('quick_fire_remaining'),
                    "success": True
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error getting question: {str(e)}")
        
        @self.app.post("/api/submit_answer")
        async def api_submit_answer(answer_request: AnswerSubmissionRequest):
            try:
                if not self.quiz_controller.quiz_active:
                    raise HTTPException(status_code=400, detail="No active quiz session")
                
                # Get current question from controller (like the Flask version)
                current_question = self.quiz_controller.get_current_question()
                if current_question is None:
                    raise HTTPException(status_code=400, detail="No current question available")
                
                question_data = current_question['question_data']
                question_index = current_question['original_index']
                
                # Submit answer using the same method as Flask version
                result = self.quiz_controller.submit_answer(
                    question_data, 
                    answer_request.answer_index, 
                    question_index
                )
                
                # Clear current question cache after processing
                self.quiz_controller.clear_current_question_cache()
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/end_quiz")
        async def api_end_quiz():
            try:
                if not self.quiz_controller.quiz_active:
                    return {"success": True, "message": "No active quiz session"}
                
                # Use the proper end_session method instead of force_end_session
                result = self.quiz_controller.end_session()
                
                if 'error' in result:
                    return {"success": False, "error": result['error']}
                
                return {"success": True, "results": result}
                
            except Exception as e:
                print(f"❌ Error ending quiz: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=str(e))
        
        # Quick fire and special modes
        @self.app.post("/api/start_quick_fire")
        async def api_start_quick_fire():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="quick_fire")
                return {"success": True, **result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/start_daily_challenge")
        async def api_start_daily_challenge():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="daily_challenge")
                return {"success": True, **result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/start_pop_quiz")
        async def api_start_pop_quiz():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="pop_quiz")
                return {"success": True, **result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/start_mini_quiz")
        async def api_start_mini_quiz():
            try:
                if self.quiz_controller.quiz_active:
                    self.quiz_controller.force_end_session()
                
                result = self.quiz_controller.start_quiz_session(mode="mini_quiz")
                return {"success": True, **result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/quick_fire_status")
        async def api_quick_fire_status():
            try:
                if self.quiz_controller.quick_fire_active:
                    result = self.quiz_controller.check_quick_fire_status()
                    return result
                else:
                    return {"active": False}
            except Exception as e:
                return {"active": False, "error": str(e)}
        
        # Statistics and achievements
        @self.app.get("/api/statistics")
        async def api_statistics():
            try:
                return self.stats_controller.get_detailed_statistics()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/achievements")
        async def api_achievements():
            try:
                return self.stats_controller.get_achievements_data()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/leaderboard")
        async def api_leaderboard():
            try:
                return self.stats_controller.get_leaderboard_data()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/clear_statistics")
        async def api_clear_statistics():
            try:
                success = self.stats_controller.clear_statistics()
                return {"success": success}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # CLI Playground endpoints
        @self.app.post("/api/cli/execute")
        async def api_cli_execute(command_request: CLICommandRequest):
            try:
                result = await self.execute_cli_command_async(command_request.command)
                return {"output": result, "success": True}
            except Exception as e:
                return {"output": f"Error: {str(e)}", "success": False}
        
        @self.app.get("/api/cli/help")
        async def api_cli_help():
            try:
                help_text = self.get_cli_help_text()
                return {"help": help_text, "success": True}
            except Exception as e:
                return {"help": "Help not available", "success": False, "error": str(e)}
        
        # CLI Playground endpoints with session management
        @self.app.post("/api/cli/execute")
        async def api_cli_execute(command_request: CLICommandRequest):
            try:
                result = await self.execute_cli_command_async(command_request.command)
                
                # Store command in history
                await self._add_to_cli_history(command_request.command)
                
                return {"output": result, "success": True}
            except Exception as e:
                return {"output": f"Error: {str(e)}", "success": False}
        
        @self.app.get("/api/cli/help")
        async def api_cli_help():
            try:
                help_text = self.get_cli_help_text()
                return {"help": help_text, "success": True}
            except Exception as e:
                return {"help": "Help not available", "success": False, "error": str(e)}
        
        @self.app.get("/api/cli/commands")
        async def api_cli_commands():
            try:
                # Return commands in the format expected by the JavaScript
                commands_list = []
                for cmd_name in self.cli_playground.safe_commands.keys():
                    commands_list.append({
                        "command": cmd_name,
                        "description": f"Execute {cmd_name} command"
                    })
                return {"commands": commands_list, "success": True}
            except Exception as e:
                return {"commands": [], "success": False, "error": str(e)}
        
        @self.app.post("/api/cli/clear")
        async def api_cli_clear():
            try:
                # Clear command history
                await self._clear_cli_history()
                return {"success": True, "message": "History cleared"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/cli/history")
        async def api_cli_history():
            try:
                history = await self._get_cli_history()
                return {"history": history, "success": True}
            except Exception as e:
                return {"history": [], "success": False, "error": str(e)}
        
        # Settings endpoints
        @self.app.post("/api/save_settings")
        async def api_save_settings(settings_request: SettingsRequest):
            try:
                settings = {
                    "focusMode": settings_request.focusMode,
                    "breakReminder": settings_request.breakReminder,
                    "timestamp": time.time()
                }
                
                async with asyncio.Lock():
                    with open("web_settings.json", "w") as f:
                        json.dump(settings, f)
                
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/load_settings")
        async def api_load_settings():
            try:
                try:
                    with open("web_settings.json", "r") as f:
                        settings = json.load(f)
                    return {"success": True, "settings": settings}
                except FileNotFoundError:
                    return {"success": True, "settings": {"focusMode": False, "breakReminder": 10}}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Question count endpoint with category refresh
        @self.app.get("/api/question-count")
        async def get_question_count():
            try:
                count = len(self.game_state.questions)
                categories = sorted(list(self.game_state.categories))
                
                return {
                    "success": True, 
                    "count": count,
                    "categories": categories
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Category cleanup endpoint
        @self.app.post("/api/cleanup_categories")
        async def cleanup_categories():
            try:
                print("🧹 Starting category cleanup...")
                
                # The QuestionManager handles categories automatically
                # We can't directly modify categories since it's a read-only property
                # But we can normalize questions and let the QuestionManager update categories
                
                updated_count = 0
                questions = self.game_state.question_manager.questions
                
                for i, question in enumerate(questions):
                    old_category = question.category
                    new_category = self._normalize_category_name(old_category)
                    
                    if old_category != new_category:
                        # Update the question object directly
                        question.category = new_category
                        updated_count += 1
                        print(f"🔄 Updated category: '{old_category}' → '{new_category}'")
                
                # Save changes
                try:
                    await self._save_questions_to_file()
                    print("✅ Categories cleaned up and saved")
                except Exception as save_error:
                    print(f"⚠️ Cleanup successful but save failed: {save_error}")
                
                # Get updated categories from QuestionManager
                categories = sorted(list(self.game_state.categories))
                
                return {
                    "success": True,
                    "message": f"Cleaned up {updated_count} categories",
                    "total_categories": len(categories),
                    "categories": categories
                }
                
            except Exception as e:
                print(f"❌ Category cleanup failed: {e}")
                return {"success": False, "error": str(e)}
        
        # Debug endpoint to help troubleshoot issues
        @self.app.get("/api/debug/game_state")
        async def debug_game_state():
            try:
                debug_info = {
                    "questions_count": len(self.game_state.questions) if hasattr(self.game_state, 'questions') else 0,
                    "questions_type": str(type(self.game_state.questions)) if hasattr(self.game_state, 'questions') else "Not found",
                    "has_categories": hasattr(self.game_state, 'categories'),
                    "categories_count": len(self.game_state.categories) if hasattr(self.game_state, 'categories') else 0,
                    "has_save_questions": hasattr(self.game_state, 'save_questions'),
                    "game_state_attributes": [attr for attr in dir(self.game_state) if not attr.startswith('_')],
                }
                
                # Sample question format if questions exist
                if hasattr(self.game_state, 'questions') and self.game_state.questions:
                    first_question = self.game_state.questions[0]
                    debug_info["sample_question_type"] = str(type(first_question))
                    debug_info["sample_question_format"] = str(first_question)[:200] if first_question else "None"
                
                return {"success": True, "debug_info": debug_info}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.post("/api/debug/preview_file")
        async def debug_preview_file(file: UploadFile = File(...)):
            """Preview first 50 lines of uploaded file for debugging."""
            try:
                content = await file.read()
                file_content = content.decode('utf-8')
                lines = file_content.split('\n')
                
                preview = {
                    "filename": file.filename,
                    "total_lines": len(lines),
                    "file_size": len(content),
                    "first_50_lines": lines[:50],
                    "sample_question_lines": [],
                    "sample_answer_lines": []
                }
                
                # Find sample question and answer lines
                for i, line in enumerate(lines[:200]):  # Check first 200 lines
                    if re.match(r'\*\*Q\d+\.\*\*', line):
                        preview["sample_question_lines"].append(f"Line {i+1}: {line}")
                    elif re.match(r'\*\*A\d+\.\*\*', line):
                        preview["sample_answer_lines"].append(f"Line {i+1}: {line}")
                
                return {"success": True, "preview": preview}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/debug/questions")
        async def debug_questions():
            """Debug endpoint to inspect current questions in memory."""
            try:
                if not hasattr(self.game_state, 'questions'):
                    return {"success": False, "error": "No questions attribute found"}
                
                questions = self.game_state.questions
                debug_info = {
                    "total_questions": len(questions),
                    "questions_type": str(type(questions)),
                    "sample_questions": []
                }
                
                # Show first 5 questions for inspection
                for i, question in enumerate(questions[:5]):
                    question_info = {
                        "index": i,
                        "type": str(type(question)),
                        "length": len(question) if hasattr(question, '__len__') else "N/A"
                    }
                    
                    if isinstance(question, tuple):
                        question_info["tuple_content"] = {
                            "question_text": question[0] if len(question) > 0 else "Missing",
                            "options_count": len(question[1]) if len(question) > 1 and isinstance(question[1], list) else "Not list",
                            "correct_answer": question[2] if len(question) > 2 else "Missing",
                            "category": question[3] if len(question) > 3 else "Missing",
                            "difficulty": question[4] if len(question) > 4 else "Missing"
                        }
                    elif hasattr(question, '__dict__'):
                        question_info["object_attributes"] = list(vars(question).keys())
                    else:
                        question_info["raw_content"] = str(question)[:200]
                    
                    debug_info["sample_questions"].append(question_info)
                
                return {"success": True, "debug_info": debug_info}
                
            except Exception as e:
                import traceback
                return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        
        # Import/Export endpoints
        @self.app.get("/import/questions", response_class=HTMLResponse)
        async def import_questions_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("import.html", context)
        
        @self.app.post("/import/questions")
        async def import_questions_post(file: UploadFile = File(...)):
            try:
                print(f"📁 Import started for file: {file.filename}")
                
                # File validation
                if not file.filename:
                    raise HTTPException(status_code=400, detail="No file was selected.")
                
                # Check file extension
                file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
                print(f"📄 File extension: {file_ext}")
                
                if file_ext not in ['json', 'md']:
                    raise HTTPException(
                        status_code=400, 
                        detail="Only JSON and Markdown (.md) files are supported."
                    )
                
                # Read file content
                content = await file.read()
                print(f"📊 File size: {len(content)} bytes")
                
                # Check file size (10MB limit)
                if len(content) > 10 * 1024 * 1024:
                    raise HTTPException(
                        status_code=400,
                        detail="File size too large. Maximum size is 10MB."
                    )
                
                # Decode content
                try:
                    file_content = content.decode('utf-8')
                    print(f"✅ File decoded successfully, length: {len(file_content)}")
                except UnicodeDecodeError as e:
                    print(f"❌ Unicode decode error: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail="File encoding error. Please ensure the file is UTF-8 encoded."
                    )
                
                # Parse questions based on file type
                print(f"🔍 Parsing {file_ext} file...")
                try:
                    if file_ext == 'json':
                        imported_questions = self._parse_json_questions(file_content)
                    elif file_ext == 'md':
                        imported_questions = self._parse_markdown_questions(file_content)
                    else:
                        imported_questions = []
                    
                    print(f"📝 Parsed {len(imported_questions)} questions")
                except Exception as parse_error:
                    print(f"❌ Parse error: {parse_error}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to parse file: {str(parse_error)}"
                    )
                
                if not imported_questions:
                    return {"success": False, "message": "No valid questions found in the uploaded file."}
                
                # Add questions to system
                print(f"💾 Adding questions to system...")
                total_added = 0
                errors = []
                
                # Get current questions count
                initial_count = len(self.game_state.questions) if hasattr(self.game_state, 'questions') else 0
                print(f"📊 Initial question count: {initial_count}")
                
                for i, question_data in enumerate(imported_questions):
                    try:
                        # Safe debug logging with type checking
                        question_text = question_data.get('question', '') if isinstance(question_data, dict) else str(question_data)
                        if isinstance(question_text, str):
                            debug_text = question_text[:50] + "..." if len(question_text) > 50 else question_text
                        else:
                            debug_text = f"Invalid question type: {type(question_text)}"
                        
                        print(f"🔄 Processing question {i+1}: {debug_text}")
                        
                        # Validate question_data is a dictionary
                        if not isinstance(question_data, dict):
                            errors.append(f"Question {i+1}: Invalid data format - got {type(question_data)}: {str(question_data)[:100]}")
                            continue
                        
                        # Validate question structure
                        question_text = question_data.get('question', '')
                        if not isinstance(question_text, str) or not question_text.strip():
                            errors.append(f"Question {i+1}: Empty or invalid question text")
                            continue
                        
                        options = question_data.get('options', [])
                        if not isinstance(options, list) or len(options) < 2:
                            errors.append(f"Question {i+1}: Invalid or insufficient options")
                            continue
                        
                        # Validate correct answer index
                        correct_idx = question_data.get('correct_answer_index', 0)
                        if not isinstance(correct_idx, int) or correct_idx < 0 or correct_idx >= len(options):
                            errors.append(f"Question {i+1}: Invalid correct answer index")
                            continue
                        
                        # Create Question object and add via QuestionManager
                        try:
                            from models.question import Question
                            
                            question_obj = Question(
                                text=question_text.strip(),
                                options=options,
                                correct_index=correct_idx,
                                category=self._normalize_category_name(question_data.get('category', 'General')),
                                explanation=question_data.get('explanation', '')
                            )
                            
                            # Add question via QuestionManager (this is the correct way)
                            question_index = self.game_state.question_manager.add_question(question_obj)
                            
                            # Debug: Verify the question was added
                            current_count = len(self.game_state.questions)
                            print(f"📝 Question {i+1} added via QuestionManager. Total count now: {current_count}")
                            print(f"    Question: {question_text[:50]}...")
                            print(f"    Options: {len(options)} items")
                            print(f"    Category: {question_obj.category}")
                            print(f"    Added at index: {question_index}")
                            
                            total_added += 1
                            
                        except Exception as add_error:
                            error_msg = f"Question {i+1}: Error adding to QuestionManager - {str(add_error)}"
                            print(f"❌ {error_msg}")
                            errors.append(error_msg)
                            continue
                        
                    except Exception as e:
                        error_msg = f"Question {i+1}: Error processing - {str(e)}"
                        print(f"❌ {error_msg}")
                        errors.append(error_msg)
                        continue
                
                # Report results
                final_count = len(self.game_state.questions) if hasattr(self.game_state, 'questions') else 0
                print(f"📊 Final question count: {final_count}")
                print(f"➕ Questions added: {total_added}")
                
                # Try to save (but don't fail if save doesn't work)
                try:
                    print("💾 Attempting to save questions...")
                    await self._save_questions_to_file()
                    print("✅ Questions saved successfully")
                except Exception as save_error:
                    error_msg = f"Warning: Could not save questions: {str(save_error)}"
                    print(f"⚠️ {error_msg}")
                    errors.append(error_msg)
                
                response_message = f'Successfully imported {total_added} questions from {file.filename}.'
                if errors:
                    response_message += f' {len(errors)} issues encountered.'
                
                print(f"🎉 Import completed: {response_message}")
                
                return {
                    "success": True,
                    "message": response_message,
                    "total_added": total_added,
                    "errors": errors[:10] if errors else [],  # Limit errors shown
                    "debug_info": {
                        "initial_count": initial_count,
                        "final_count": final_count,
                        "parsed_questions": len(imported_questions)
                    }
                }
                
            except HTTPException:
                raise
            except Exception as e:
                error_msg = f"Import failed: {str(e)}"
                print(f"💥 {error_msg}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=error_msg)
        
        # Break reminder endpoints
        @self.app.post("/api/acknowledge_break")
        async def api_acknowledge_break():
            try:
                # Reset break counter (if this method exists)
                if hasattr(self.quiz_controller, 'reset_break_counter'):
                    self.quiz_controller.reset_break_counter()
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def execute_cli_command_async(self, command: str) -> str:
        """Execute CLI command asynchronously."""
        try:
            # Run CLI command in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.cli_playground.process_command, command)
            return result
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def get_cli_help_text(self) -> str:
        """Get CLI help text."""
        help_func = self.cli_playground.safe_commands.get("help", lambda args: "No help available")
        return help_func([])
    
    # CLI History management (simple in-memory storage for now)
    cli_history = []
    
    async def _add_to_cli_history(self, command: str):
        """Add command to CLI history."""
        if command.strip() and command not in self.cli_history[-5:]:  # Avoid duplicates in recent history
            self.cli_history.append(command)
            # Keep only last 50 commands
            if len(self.cli_history) > 50:
                self.cli_history = self.cli_history[-50:]
    
    async def _get_cli_history(self) -> List[str]:
        """Get CLI command history."""
        return self.cli_history[-20:]  # Return last 20 commands
    
    async def _clear_cli_history(self):
        """Clear CLI command history."""
        self.cli_history.clear()
    
    async def _save_questions_to_file(self):
        """Save current questions to the JSON file using QuestionManager."""
        try:
            questions_data = []
            
            # Use QuestionManager's questions directly
            questions = self.game_state.question_manager.questions
            print(f"💾 Saving {len(questions)} questions to file...")
            
            for i, question in enumerate(questions):
                try:
                    # Convert Question object to dict
                    question_dict = {
                        "question_text": question.text,
                        "options": question.options,
                        "correct_answer": question.correct_index,
                        "category": question.category,
                        "difficulty": getattr(question, 'difficulty', 'Intermediate'),
                        "explanation": getattr(question, 'explanation', '')
                    }
                    questions_data.append(question_dict)
                        
                except Exception as e:
                    print(f"❌ Error processing question {i+1} for save: {e}")
                    continue
            
            print(f"📝 Prepared {len(questions_data)} questions for saving")
            
            # Write to file
            questions_file = Path('data/questions.json')
            questions_file.parent.mkdir(exist_ok=True)
            
            with open(questions_file, 'w', encoding='utf-8') as f:
                json.dump(questions_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Successfully saved {len(questions_data)} questions to {questions_file}")
            
            # Verify the save worked
            try:
                with open(questions_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                print(f"✅ Verification: File contains {len(saved_data)} questions")
                
                # Verify categories are preserved
                saved_categories = set(q.get('category', 'General') for q in saved_data)
                print(f"✅ Verification: {len(saved_categories)} categories preserved")
                
            except Exception as verify_error:
                print(f"⚠️ Could not verify save: {verify_error}")
            
        except Exception as e:
            print(f"❌ Error saving questions: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_template_context(self, request: Request) -> Dict[str, Any]:
        """Get template context with FastAPI-compatible url_for function."""
        def url_for(name: str, **params) -> str:
            """FastAPI-compatible url_for function."""
            if name == "static":
                filename = params.get("filename", "")
                return f"/static/{filename}"
            # For other routes, use Starlette's url_path_for
            try:
                return str(request.url_for(name, **params))
            except:
                # Fallback for static files or unknown routes
                return f"/{name}"
        
        return {
            "request": request,
            "url_for": url_for
        }
    
    def _normalize_category_name(self, category: str) -> str:
        """Normalize category name to avoid duplicates."""
        if not category:
            return "General"
        
        # Clean up the category name
        category = category.strip()
        
        # Fix common formatting issues
        if category.endswith("(") or category.endswith(" ("):
            category = category.rstrip("( ")
        
        # Ensure parentheses are balanced
        open_parens = category.count("(")
        close_parens = category.count(")")
        
        if open_parens > close_parens:
            category += ")" * (open_parens - close_parens)
        
        return category
    
    def _parse_json_questions(self, file_content: str) -> List[Dict]:
        """Parse questions from JSON format."""
        try:
            data = json.loads(file_content)
            questions = []
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Direct list of questions
                for item in data:
                    if isinstance(item, dict) and 'question' in item:
                        questions.append(item)
            elif isinstance(data, dict):
                # Check for questions key
                if 'questions' in data:
                    questions = data['questions']
                elif 'question' in data:
                    # Single question
                    questions = [data]
            
            # Normalize question format
            normalized = []
            for q in questions:
                if isinstance(q, dict):
                    normalized_q = {
                        'question': q.get('question_text', q.get('question', '')),
                        'options': q.get('options', []),
                        'correct_answer_index': q.get('correct_answer_index', q.get('correct_answer', 0)),
                        'category': self._normalize_category_name(q.get('category', 'General')),
                        'explanation': q.get('explanation', ''),
                        'difficulty': q.get('difficulty', 'Intermediate')
                    }
                    if normalized_q['question'] and normalized_q['options']:
                        normalized.append(normalized_q)
            
            return normalized
            
        except json.JSONDecodeError:
            return []
        except Exception:
            return []
    
    def _parse_markdown_questions(self, file_content: str) -> List[Dict]:
        """Parse questions from Markdown format with improved parsing."""
        try:
            questions = []
            lines = file_content.split('\n')
            
            current_question = None
            current_options = []
            current_category = 'General'
            in_questions_section = False
            in_answers_section = False
            answers_map = {}  # Map question numbers to correct answers
            
            print(f"🔍 Markdown parser: Processing {len(lines)} lines")
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Section headers
                if line.lower().startswith('# questions'):
                    in_questions_section = True
                    in_answers_section = False
                    print("📝 Found Questions section")
                    continue
                elif line.lower().startswith('# answers'):
                    in_questions_section = False
                    in_answers_section = True
                    print("📝 Found Answers section")
                    continue
                elif line.startswith('---') or line.startswith('==='):
                    continue
                
                if in_questions_section:
                    # Question pattern: **Q1.** (Category) Question text
                    # Also handle: **Q1.** Question text without category
                    # Updated regex to capture more patterns
                    q_match = re.match(r'\*\*Q(\d+)\.\*\*\s*(?:\(([^)]+)\))?\s*(.*)', line)
                    if q_match:
                        # Save previous question if it exists
                        if current_question and current_options:
                            questions.append({
                                'question': current_question['text'].strip(),
                                'options': current_options[:],
                                'category': current_question.get('category', 'General'),
                                'correct_answer_index': 0,  # Will be updated from answers
                                'explanation': '',
                                'difficulty': 'Intermediate'
                            })
                        
                        # Start new question
                        question_num = int(q_match.group(1))
                        category = self._normalize_category_name(q_match.group(2) if q_match.group(2) else current_category)
                        question_text = q_match.group(3).strip()
                        
                        # Handle the case where question text might be on the next line
                        if not question_text:
                            question_text = ""
                        
                        current_question = {
                            'number': question_num,
                            'text': question_text,
                            'category': category
                        }
                        current_options = []
                        current_category = category  # Update current category
                        
                        print(f"📝 Found question {question_num}: {question_text[:50]}...")
                        continue
                    
                    # Option pattern: A. Option text, B. Option text, etc.
                    option_match = re.match(r'\s*([A-Z])\.\s+(.+)', line)
                    if option_match and current_question:
                        option_letter = option_match.group(1)
                        option_text = option_match.group(2).strip()
                        current_options.append(option_text)
                        continue
                    
                    # If we have current_question but line doesn't match option pattern,
                    # it might be a continuation of the question text or the actual question text
                    if current_question and not option_match and not q_match:
                        line_stripped = line.strip()
                        if line_stripped:  # Only add non-empty lines
                            if current_question['text']:
                                current_question['text'] += ' ' + line_stripped
                            else:
                                # This might be the actual question text if it was empty before
                                current_question['text'] = line_stripped
                        continue
                
                elif in_answers_section:
                    # Answer pattern: **A1.** A. Correct option
                    # or: **A1.** A
                    a_match = re.match(r'\*\*A(\d+)\.\*\*\s*([A-Z])(?:\.\s*(.*))?', line)
                    if a_match:
                        question_num = int(a_match.group(1))
                        correct_letter = a_match.group(2)
                        # Convert letter to index (A=0, B=1, C=2, D=3)
                        correct_index = ord(correct_letter) - ord('A')
                        answers_map[question_num] = correct_index
                        print(f"📝 Answer for Q{question_num}: {correct_letter} (index {correct_index})")
                        continue
            
            # Add the last question if it exists
            if current_question and current_options:
                questions.append({
                    'question': current_question['text'].strip(),
                    'options': current_options,
                    'category': current_question.get('category', 'General'),
                    'correct_answer_index': 0,
                    'explanation': '',
                    'difficulty': 'Intermediate'
                })
            
            # Update correct answer indices based on answers section
            for i, question in enumerate(questions):
                question_num = i + 1  # Assuming sequential numbering
                if question_num in answers_map:
                    correct_idx = answers_map[question_num]
                    if 0 <= correct_idx < len(question['options']):
                        question['correct_answer_index'] = correct_idx
                    else:
                        print(f"⚠️ Invalid answer index {correct_idx} for question {question_num}")
            
            print(f"✅ Markdown parser: Successfully parsed {len(questions)} questions")
            
            # Debug: Show first few questions
            for i, q in enumerate(questions[:3]):
                question_text = q.get('question', 'NO_QUESTION')
                print(f"🔍 Sample Q{i+1}: {question_text[:50]}...")
                print(f"    Options: {len(q.get('options', []))} items")
                print(f"    Category: {q.get('category', 'NO_CATEGORY')}")
                print(f"    Correct: {q.get('correct_answer_index', 'NO_INDEX')}")
            
            return questions
            
        except Exception as e:
            print(f"❌ Markdown parsing error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def reset_quiz_state(self):
        """Reset quiz state variables."""
        self.current_category_filter = None
        self.current_question_data = None
        self.current_question_index = -1
    
    async def startup_event(self):
        """Application startup event."""
        logging.info("Linux+ Study FastAPI application starting up...")
    
    async def shutdown_event(self):
        """Application shutdown event."""
        logging.info("Linux+ Study FastAPI application shutting down...")
        # Save any pending data
        self.game_state.save_history()
        self.game_state.save_achievements()

    def start_desktop_app(self):
        """Start the FastAPI application in a desktop window using pywebview."""
        try:
            import webview
            import threading
            import uvicorn
            
            print("🖥️  Starting Desktop Application with pywebview...")
            print("🚀 FastAPI backend initializing...")
            
            # Create FastAPI app
            app = self.app
            
            # Configure uvicorn server
            config = uvicorn.Config(
                app=app,
                host="127.0.0.1",
                port=5000,
                log_level="warning",  # Reduce log noise in desktop mode
                access_log=False
            )
            
            server = uvicorn.Server(config)
            
            # Start server in background thread
            def run_server():
                import asyncio
                asyncio.run(server.serve())
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            import time
            time.sleep(2)
            
            # Create desktop window
            window = webview.create_window(
                title='Linux+ Study Game',
                url='http://127.0.0.1:5000',
                width=1200,
                height=900,
                min_size=(800, 600),
                resizable=True
            )
            
            print("🎯 Desktop app window opening...")
            print("💡 Close the window or press Ctrl+C to exit")
            
            # Start the webview (this blocks until window is closed)
            webview.start(debug=self.debug)
            
        except ImportError:
            print("❌ pywebview not available. Install with: pip install pywebview")
            print("🌐 Falling back to web browser mode...")
            return False
        except Exception as e:
            print(f"❌ Error starting desktop app: {e}")
            return False
        
        return True

# Add startup and shutdown event handlers
app_instance = None

def create_app(game_state, debug: bool = False) -> FastAPI:
    """Factory function to create FastAPI app instance."""
    global app_instance
    app_instance = LinuxPlusStudyFastAPI(game_state, debug)
    
    # Add event handlers
    @app_instance.app.on_event("startup")
    async def startup():
        await app_instance.startup_event()
    
    @app_instance.app.on_event("shutdown")
    async def shutdown():
        await app_instance.shutdown_event()
    
    return app_instance.app