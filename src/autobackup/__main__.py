"""
Démarre l'application principale.

--- Journey ---
1. Setup environment
2. Setup logging
3. Start the main loop
"""

import logging
import argparse
import sys

import questionary as q

from autobackup.logs import setup_logging
from autobackup.paths import ensure_environment, log_dir



logger = logging.getLogger("autobackup.main" )


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée principal de l'application.
    """
    parser = argparse.ArgumentParser(prog="autobackup", description="Autobackup - Automatic backup tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)")

    args = parser.parse_args(argv)

    ensure_environment()
    log_path = setup_logging(log_dir(), verbose=args.verbose)
    logger.info(f"Logging initialized. Log file: {log_path}")

    return interactive_menu()


def run_backup() -> int:
    """Lance le backup. Jamais de questionary ici : appelé sans terminal."""
    logger.info("Backup lancé (pas encore implémenté).")
    return 0


def interactive_menu():
    try: 
        while True:
            q.print("")
            menu = q.select(
                "Select an action:",
                choices=[
                    q.Choice("View/edit backup pairs", value="list"),
                    q.Choice("Add a new backup pair", value="add"),
                    q.Choice("Change settings", value="settings"),
                    q.Choice("Launch backup now", value="launch"),
                    q.Separator(),
                    q.Choice("Exit", value="quit")
                ]
            )
            action = menu.unsafe_ask()
            logger.debug(f"Selected action: {action}")

            match action:
                case "quit":
                    logger.info("Exiting the application.")
                    q.print("Exiting the application.")
                    return 0
                case "list":
                    q.print("Viewing/editing backup pairs (not implemented yet).")
                case "add":
                    q.print("Adding a new backup pair (not implemented yet).")
                case "settings":
                    q.print("Changing settings (not implemented yet).")
                case "launch":
                    run_backup()
    except KeyboardInterrupt:
        q.print("\nInterrompu.")
        logger.info("User interrupted the application with Ctrl+C.")
        return 130 



if __name__ == "__main__":
    sys.exit(main())