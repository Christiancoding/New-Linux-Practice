#!/usr/bin/env python3
"""
Linux+ Study Game - Main Entry Point

A comprehensive study tool for CompTIA Linux+ certification preparation
featuring both CLI and web interfaces with gamification elements.
"""

import sys
import traceback
# Ensure the script is run with Python 3
if sys.version_info < (3, 0):
    print("This script requires Python 3. Please run with python3.")
    sys.exit(1)

import os

# Import configuration and utilities
from models.question import QuestionManager
from utils.database import DatabaseManager
from utils.config import *
from models.game_state import GameState
from views.cli_view import LinuxPlusStudyCLI
import views.cli_view as cli_view
from views.web_view import LinuxPlusStudyWeb

# Initialize database manager with proper error handling
try:
    db_manager = DatabaseManager(use_sqlite=True)
    print(f"{COLOR_INFO}Database initialized: {'SQLite' if db_manager.use_sqlite else 'JSON'}{COLOR_RESET}")
except Exception as e:
    print(f"{COLOR_ERROR}Database initialization failed: {e}{COLOR_RESET}")
    print(f"{COLOR_WARNING}Falling back to JSON mode...{COLOR_RESET}")
    db_manager = DatabaseManager(use_sqlite=False)

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
    Launch the command-line interface.
    
    Args:
        game_state: GameState instance
    """
    try:
        cli_view = LinuxPlusStudyCLI(game_state, db_manager)
        cli_view.main_loop()
    except KeyboardInterrupt:
        print(f"\n{COLOR_WARNING}Goodbye!{COLOR_RESET}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Error details:")
        traceback.print_exc()
        print("Attempting to save progress...")
        game_state.save_history()
        game_state.save_achievements()
def launch_web_interface(game_state):
    """
    Launch the web interface.
    
    Args:
        game_state: GameState instance
    """
    try:
        web_view = LinuxPlusStudyWeb(game_state, db_manager)
        web_view.start()
        
    except ImportError as e:
        print(f"Error: Failed to initialize web interface.")
        print(f"Missing required packages. Install with: pip install flask pywebview")
        print(f"Error details: {e}")
        
        # Attempt to save before exiting
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(1)
        
    except Exception as e:
        print(f"\nAn unexpected error occurred launching the web interface: {e}")
        print("Error details:")
        traceback.print_exc()
        print("Attempting to save progress...")
        game_state.save_history()
        game_state.save_achievements()
        sys.exit(1)
def handle_command_line_args():
    """Handle command line arguments for database operations."""
    if len(sys.argv) < 2:
        return None
    
    command = sys.argv[1].lower()
    
    if command == '--backup':
        print(f"{COLOR_INFO}Creating database backup...{COLOR_RESET}")
        try:
            backup_path = db_manager.backup_database()
            print(f"{COLOR_SUCCESS}Backup created: {backup_path}{COLOR_RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{COLOR_ERROR}Backup failed: {e}{COLOR_RESET}")
            sys.exit(1)
    
    elif command == '--migrate':
        print(f"{COLOR_INFO}Starting manual migration from JSON to SQLite...{COLOR_RESET}")
        try:
            # Force re-migration
            db_manager_temp = DatabaseManager(use_sqlite=True)
            db_manager_temp._migrate_from_json_if_needed()
            print(f"{COLOR_SUCCESS}Migration completed successfully{COLOR_RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{COLOR_ERROR}Migration failed: {e}{COLOR_RESET}")
            sys.exit(1)
    
    elif command == '--check-db':
        print(f"{COLOR_INFO}Checking database integrity...{COLOR_RESET}")
        try:
            report = db_manager.validate_data_integrity()
            print(f"{COLOR_SUCCESS}Database Status:{COLOR_RESET}")
            print(f"  - Valid: {report['valid']}")
            print(f"  - Stats: {report['stats']}")
            if report['errors']:
                print(f"{COLOR_ERROR}  - Errors: {report['errors']}{COLOR_RESET}")
            if report['warnings']:
                print(f"{COLOR_WARNING}  - Warnings: {report['warnings']}{COLOR_RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{COLOR_ERROR}Database check failed: {e}{COLOR_RESET}")
            sys.exit(1)
    
    elif command == '--help':
        print_help()
        sys.exit(0)
    
    return command

def print_help():
    """Print command line help."""
    print(f"{COLOR_INFO}Linux+ Study Game - Command Line Options:{COLOR_RESET}")
    print(f"{COLOR_OPTIONS}  python main.py{COLOR_RESET}          - Start interactive mode")
    print(f"{COLOR_OPTIONS}  python main.py cli{COLOR_RESET}      - Start CLI mode directly")
    print(f"{COLOR_OPTIONS}  python main.py web{COLOR_RESET}      - Start web mode directly")
    print(f"{COLOR_OPTIONS}  python main.py --backup{COLOR_RESET} - Create database backup")
    print(f"{COLOR_OPTIONS}  python main.py --migrate{COLOR_RESET}- Migrate JSON to SQLite")
    print(f"{COLOR_OPTIONS}  python main.py --check-db{COLOR_RESET}- Check database integrity")
    print(f"{COLOR_OPTIONS}  python main.py --help{COLOR_RESET}   - Show this help")
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    import signal
    
    def signal_handler(signum, frame):
        print(f"\n{COLOR_WARNING}Received shutdown signal. Saving progress...{COLOR_RESET}")
        try:
            if 'db_manager' in globals():
                db_manager.backup_database()
                print(f"{COLOR_SUCCESS}Backup created before shutdown{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_ERROR}Could not create backup: {e}{COLOR_RESET}")
        finally:
            print(f"{COLOR_INFO}Goodbye!{COLOR_RESET}")
            sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
def main():
    """Main entry point for the Linux+ Study Game."""
        # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    # Handle command line arguments first
    command = handle_command_line_args()
    if command:
        # Command was handled, exit gracefully
        return
    # Initialize colorama if available
    try:
        if 'colorama' in sys.modules:
            import colorama
            colorama.init(autoreset=True)
    except Exception as e:
        print(f"Warning: Failed to initialize colorama: {e}")
    
    # Initialize game state with database manager
    try:
        game_state = GameState(db_manager)
        print(f"{COLOR_SUCCESS}Game state initialized successfully{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_ERROR}Fatal error: Failed to initialize game state: {e}{COLOR_RESET}")
        traceback.print_exc()
        
        # Try to create backup before exiting
        try:
            if 'db_manager' in locals():
                backup_path = db_manager.backup_database()
                print(f"{COLOR_INFO}Emergency backup created: {backup_path}{COLOR_RESET}")
        except:
            pass
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


if __name__ == "__main__":
    main()