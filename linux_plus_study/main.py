#!/usr/bin/env python3
"""
Main entry point for the Linux+ Study Game.
Supports both CLI and FastAPI web modes.
"""

import sys
import os
import signal
import traceback
from pathlib import Path

# Import CLI-related classes
from views.cli_view import LinuxPlusStudyCLI
from models.game_state import GameState

# Color constants for terminal output
COLOR_RESET = "\033[0m"
COLOR_INFO = "\033[1;34m"   # Bold Blue
COLOR_SUCCESS = "\033[1;32m" # Bold Green
COLOR_WARNING = "\033[1;33m" # Bold Yellow
COLOR_ERROR = "\033[1;31m"   # Bold Red


def detect_interface_preference():
    """
    Detect user interface preference based on environment and arguments.
    
    Returns:
        str: 'cli', 'web', or 'ask'
    """
    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['cli', 'terminal', 'console']:
            return 'cli'
        elif arg in ['web', 'browser', 'gui']:
            return 'web'
        elif arg in ['dev', 'development']:
            return 'dev'
    
    # Check environment variables
    interface_env = os.environ.get('LINUX_PLUS_INTERFACE', '').lower()
    if interface_env in ['cli', 'web']:
        return interface_env
    
    # Default to asking user
    return 'ask'


def get_user_interface_choice_with_web():
    """
    Get user's interface choice including web and desktop options.
    
    Returns:
        str: 'cli', 'web', or 'desktop'
    """
    try:
        print(f"{COLOR_INFO}Available interface options:")
        print(f"  {COLOR_SUCCESS}cli{COLOR_RESET}      - Command line interface")
        print(f"  {COLOR_SUCCESS}web{COLOR_RESET}      - Web server (browser)")
        print(f"  {COLOR_SUCCESS}desktop{COLOR_RESET}  - Desktop app (recommended)")
        print()
        
        while True:
            choice = input(f"{COLOR_INFO}Choose interface (cli/web/desktop): {COLOR_RESET}").strip().lower()
            
            if choice in ['cli', 'c', 'terminal', 'console']:
                return 'cli'
            elif choice in ['web', 'w', 'browser', 'server']:
                return 'web'
            elif choice in ['desktop', 'd', 'app', 'gui']:
                return 'desktop'
            else:
                print(f"{COLOR_WARNING}Invalid choice. Please type 'cli', 'web', or 'desktop'. {COLOR_RESET}")
                
    except EOFError:
        print(f"\n{COLOR_ERROR} Input interrupted. Defaulting to CLI. {COLOR_RESET}")
        return 'cli'
    except KeyboardInterrupt:
        print(f"\n{COLOR_WARNING} Operation cancelled by user. Exiting. {COLOR_RESET}")
        sys.exit(0)
def launch_web_interface_dev(game_state):
    """
    Launch the FastAPI web interface in development mode.
    
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
        
        print("🚀 Starting Linux+ Study App in development mode...")
        print("🌐 Web server mode - Use your browser")
        print("💡 Press Ctrl+C to exit gracefully")
        print("🌐 Server will be available at: http://127.0.0.1:5000")
        print("📚 API documentation: http://127.0.0.1:5000/api/docs")
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
            reload=False,
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


def launch_web_interface(game_state):
    """
    Launch the FastAPI web interface with Uvicorn (web server mode).
    
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
        print("🌐 Web server mode - Use your browser")
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
            reload=False,
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
def create_web_app():
    """
    Factory function to create FastAPI app for uvicorn.
    This is used when running with: uvicorn main:create_web_app --reload
    """
    try:
        from views.web_view import create_app
        
        # Initialize game state
        game_state = GameState()
        
        # Create and return FastAPI app
        return create_app(game_state, debug=True)
        
    except Exception as e:
        print(f"Error creating web app: {e}")
        traceback.print_exc()
        raise
def launch_desktop_interface(game_state):
    """
    Launch the FastAPI web interface in a desktop app window.
    
    Args:
        game_state: GameState instance
    """
    try:
        # Check for required dependencies
        try:
            import uvicorn
            from fastapi import FastAPI
            import webview
        except ImportError as e:
            print(f"{COLOR_ERROR}Error: Missing required packages for desktop mode.")
            print(f"{COLOR_INFO}Install with: pip install fastapi uvicorn[standard] pywebview")
            print(f"{COLOR_WARNING}Falling back to web browser mode...")
            return launch_web_interface(game_state)
        
        try:
            from views.web_view import LinuxPlusStudyFastAPI
        except ImportError as e:
            print(f"{COLOR_ERROR}Error: Failed to import FastAPI web interface: {e}")
            return
        
        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, signal_handler)
        
        print("🚀 Starting Linux+ Study App...")
        print("🖥️  Desktop Application Mode")
        print("📖 Modern ASGI web interface with desktop window")
        print("💡 Close the window or press Ctrl+C to exit")
        
        # Create FastAPI web interface
        web_interface = LinuxPlusStudyFastAPI(game_state, debug=False)
        
        # Try to start desktop app
        success = web_interface.start_desktop_app()
        
        if not success:
            print(f"{COLOR_WARNING}Desktop mode failed, falling back to web server...")
            launch_web_interface(game_state)
        
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        print(f"\n{COLOR_ERROR}An unexpected error occurred launching the desktop interface: {e}")
        print("Error details:")
        traceback.print_exc()
        print(f"{COLOR_INFO}Attempting to save progress...")
        game_state.save_history()
        game_state.save_achievements()
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
        interface_choice = get_user_interface_choice_with_web()
    elif interface_preference == 'dev':
        interface_choice = 'dev'
    else:
        interface_choice = interface_preference
    
    # Launch appropriate interface
    print(f"{COLOR_INFO}Starting Linux+ Study Game in {interface_choice.upper()} mode...{COLOR_RESET}")
    
    if interface_choice == 'web':
        launch_web_interface(game_state)
    elif interface_choice == 'desktop':
        launch_desktop_interface(game_state)
    elif interface_choice == 'dev':
        launch_web_interface_dev(game_state)
    else:
        launch_cli_interface(game_state)


if __name__ == "__main__":
    main()