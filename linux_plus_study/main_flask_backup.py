#!/usr/bin/env python3
"""
Linux+ Study Game - Main Entry Point

A comprehensive study tool for CompTIA Linux+ certification preparation
featuring both CLI and web interfaces with gamification elements.
"""

import sys
import traceback
import signal
import sys
# Ensure the script is run with Python 3
if sys.version_info < (3, 0):
    print("This script requires Python 3. Please run with python3.")
    sys.exit(1)
import os

# Import configuration and utilities
from utils.config import *
from models.game_state import GameState
from views.cli_view import LinuxPlusStudyCLI
import views.cli_view as cli_view
from views.web_view import LinuxPlusStudyWeb

def detect_interface_preference():
    """
    Detect if we should force CLI mode based on environment or arguments.
    
    Returns:
        str: 'cli', or 'ask' for user choice
    """
    # Check for command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == 'cli':
            return 'cli'
    
    # Detect non-interactive environment
    if not sys.stdin.isatty():
        return 'cli'
    
    # Interactive environment - ask user
    return 'ask'

def get_user_interface_choice_with_web():
    """
    Prompt user to choose between CLI orweb interfaces.
    
    Returns:
        str: 'cli', or 'web'
    """
    while True:
        try:
            prompt_text = f"{COLOR_PROMPT}Choose interface ({COLOR_OPTIONS}CLI{COLOR_PROMPT} or {COLOR_OPTIONS}web{COLOR_PROMPT}): {COLOR_INPUT}"
            print(prompt_text, end='')
            sys.stdout.flush()
            
            choice = input().lower().strip()
            print(COLOR_RESET, end='')
            
            if choice in ['cli', 'web']:
                return choice
            else:
                print(f"{COLOR_INFO} Invalid choice. Please type 'cli', or 'web'. {COLOR_RESET}")
                
        except EOFError:
            print(f"\n{COLOR_ERROR} Input interrupted. Defaulting to CLI. {COLOR_RESET}")
            return 'cli'
        except KeyboardInterrupt:
            print(f"\n{COLOR_WARNING} Operation cancelled by user. Exiting. {COLOR_RESET}")
            sys.exit(0)

def get_user_interface_choice():
    """
    Prompt user to choose between CLI and web interfaces.
    
    Returns:
        str: 'cli' or 'web'
    """
    while True:
        try:
            prompt_text = f"{COLOR_PROMPT}Choose interface ({COLOR_OPTIONS}CLI{COLOR_PROMPT} or {COLOR_OPTIONS}web{COLOR_PROMPT}): {COLOR_INPUT}"
            print(prompt_text, end='')
            sys.stdout.flush()
            
            choice = input().lower().strip()
            print(COLOR_RESET, end='')
            
            if choice in ['cli', 'web']:
                return choice
            else:
                print(f"{COLOR_INFO} Invalid choice. Please type 'cli' or 'web'. {COLOR_RESET}")
                
        except EOFError:
            print(f"\n{COLOR_ERROR} Input interrupted. Defaulting to CLI. {COLOR_RESET}")
            return 'cli'
        except KeyboardInterrupt:
            print(f"\n{COLOR_WARNING} Operation cancelled by user. Exiting. {COLOR_RESET}")
            sys.exit(0)


def launch_cli_interface(game_state):
    """
    Launch the CLI interface.
    
    Args:
        game_state: GameState instance
    """
    try:
        cli_view = LinuxPlusStudyCLI(game_state)
        cli_view.display_welcome_message()
        cli_view.main_menu()
    except KeyboardInterrupt:
        print(f"\n{COLOR_WARNING} Keyboard interrupt detected. Saving progress and exiting. {COLOR_RESET}")
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(0)
    except Exception as e:
        print(f"\n{COLOR_ERROR} An unexpected error occurred in CLI mode: {e} {COLOR_RESET}")
        print(f"{COLOR_INFO} Attempting to save progress before exiting... {COLOR_RESET}")
        game_state.save_history()
        game_state.save_achievements()
        traceback.print_exc()
        sys.exit(1)
def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🙏 Thanks for using Linux+ Study App!")
    print("📚 Keep practicing and good luck with your certification!")
    print("👋 Goodbye!\n")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def launch_web_interface(game_state):
    """
    Launch the FastAPI web interface with Uvicorn.
    
    Args:
        game_state: GameState instance
    """
    try:
        # Check for required web dependencies
        try:
            import uvicorn
            from fastapi import FastAPI
        except ImportError:
            print(f"{COLOR_ERROR}Error: FastAPI and Uvicorn are required for web mode.")
            print(f"{COLOR_INFO}Install with: pip install fastapi uvicorn[standard]")
            return
        
        try:
            from views.web_view import create_app
        except ImportError as e:
            print(f"{COLOR_ERROR}Error: Failed to import FastAPI web interface: {e}")
            print(f"{COLOR_INFO}Please check that all required packages are installed:")
            print(f"{COLOR_INFO}pip install fastapi uvicorn[standard] jinja2")
            return
        
        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, signal_handler)
        
        print("🚀 Starting Linux+ Study App with FastAPI...")
        print("📖 Modern ASGI web interface loading...")
        print("💡 Press Ctrl+C to exit gracefully")
        print("🌐 Server will be available at: http://127.0.0.1:5000")
        print("📚 API documentation: http://127.0.0.1:5000/api/docs")
        
        # Create FastAPI app
        app = create_app(game_state, debug=False)
        
        # Configure Uvicorn
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=5000,
            log_level="info",
            access_log=True,
            reload=False,  # Set to True for development
            loop="asyncio"
        )
        
        # Create and run server
        server = uvicorn.Server(config)
        server.run()
        
    except KeyboardInterrupt:
        signal_handler(None, None)
    except ImportError as e:
        print(f"{COLOR_ERROR}Error: Failed to initialize FastAPI web interface.")
        print(f"{COLOR_INFO}Missing required packages. Install with:")
        print(f"{COLOR_INFO}pip install fastapi uvicorn[standard] jinja2")
        print(f"{COLOR_ERROR}Error details: {e}")
        
        # Attempt to save before exiting
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n{COLOR_ERROR}An unexpected error occurred launching the web interface: {e}")
        print("Error details:")
        traceback.print_exc()
        print(f"{COLOR_INFO}Attempting to save progress...")
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(1)


# Also, add this new function for development mode with auto-reload:
def launch_web_interface_dev(game_state):
    """
    Launch the FastAPI web interface in development mode with auto-reload.
    
    Args:
        game_state: GameState instance
    """
    try:
        import uvicorn
        from views.web_view import create_app
        
        print("🚀 Starting Linux+ Study App in DEVELOPMENT mode...")
        print("🔄 Auto-reload enabled - changes will restart the server")
        print("📖 FastAPI web interface loading...")
        print("🌐 Server: http://127.0.0.1:5000")
        print("📚 API docs: http://127.0.0.1:5000/api/docs")
        print("📋 ReDoc: http://127.0.0.1:5000/api/redoc")
        
        # Create FastAPI app with debug mode
        app = create_app(game_state, debug=True)
        
        # Run with development settings
        uvicorn.run(
            "views.web_view:create_app",
            host="127.0.0.1",
            port=5000,
            reload=True,
            factory=True,
            log_level="debug",
            access_log=True
        )
        
    except Exception as e:
        print(f"Error in development mode: {e}")
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main entry point for the Linux+ Study Game."""
    
    # Initialize colorama if available
    try:
        if 'colorama' in sys.modules:
            import colorama
            colorama.init(autoreset=True)
    except Exception as e:
        print(f"Warning: Failed to initialize colorama: {e}")
    
    # Initialize game state
    try:
        game_state = GameState()
    except Exception as e:
        print(f"Fatal error: Failed to initialize game state: {e}")
        traceback.print_exc()
        sys.exit(1)
    print(f"{COLOR_INFO}Welcome to the Linux+ Study Game!{COLOR_RESET}")
    # Determine interface preference
    interface_preference = detect_interface_preference()
    
    if interface_preference == 'ask':
        interface_choice = get_user_interface_choice_with_web()  # Use new function
    else:
        interface_choice = interface_preference
    
    # Launch appropriate interface
    print(f"{COLOR_INFO}Starting Linux+ Study Game in {interface_choice.upper()} mode...{COLOR_RESET}")
    
    if interface_choice == 'web':
        launch_web_interface(game_state)
    else:
        launch_cli_interface(game_state)
def create_web_app():
    """
    Factory function to create FastAPI app for uvicorn.
    This is used when running with: uvicorn main:create_web_app --reload
    """
    try:
        from models.game_state import GameState
        from views.web_view import create_app
        
        # Initialize game state
        game_state = GameState()
        
        # Create and return FastAPI app
        return create_app(game_state, debug=True)
        
    except Exception as e:
        print(f"Error creating web app: {e}")
        traceback.print_exc()
        raise
if __name__ == "__main__":
    main()