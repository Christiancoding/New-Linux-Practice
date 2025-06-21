#!/usr/bin/env python3
"""
FastAPI Web View for the Linux+ Study Game.
Modern ASGI-based web interface with async support.
"""

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
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
    answer: str
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
                    results = self.quiz_controller.force_end_session()
                    return {
                        "quiz_complete": True,
                        "final_results": results
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
                
                result = self.quiz_controller.submit_answer(answer_request.answer)
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/end_quiz")
        async def api_end_quiz():
            try:
                result = self.quiz_controller.end_session()
                return result
            except Exception as e:
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
        
        @self.app.get("/api/cli/commands")
        async def api_cli_commands():
            try:
                commands = list(self.cli_playground.safe_commands.keys())
                return {"commands": commands, "success": True}
            except Exception as e:
                return {"commands": [], "success": False, "error": str(e)}
        
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
        
        # Question count endpoint
        @self.app.get("/api/question-count")
        async def get_question_count():
            try:
                count = len(self.game_state.questions)
                return {"success": True, "count": count}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Import/Export endpoints
        @self.app.get("/import/questions", response_class=HTMLResponse)
        async def import_questions_page(request: Request):
            context = self.get_template_context(request)
            return self.templates.TemplateResponse("import.html", context)
    
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