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
from autobackup.paths import ensure_environment, log_dir, config_dir
from autobackup.pairs import ensure_files, safe_read_hour, read_settings
from autobackup.operations.edit_list import manage_edit_list
from autobackup.operations.add import manage_add_pair
from autobackup.operations.edit_settings import open_file_settings
from autobackup.operations.backup import run_backup, run_backup
from autobackup.scheduler import install, uninstall, is_installed
from autobackup.notify import build_report, send



logger = logging.getLogger("autobackup.main" )


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée principal de l'application.
    """
    parser = argparse.ArgumentParser(prog="autobackup", description="Autobackup - Automatic backup tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--run", action="store_true", help="Run the backup immediately without user interaction")

    args = parser.parse_args(argv)

    ensure_environment()
    ensure_files(config_dir())
    log_path = setup_logging(log_dir(), verbose=args.verbose)
    logger.info(f"Logging initialized. Log file: {log_path}")

    if args.run:
        logger.info("Running backup immediately due to --run flag.")
        return executer_tous_backups()
    return interactive_menu()


def executer_tous_backups() -> int:
    """Lance le backup. Jamais de questionary ici : appelé sans terminal."""
    results = run_backup()
    settings = read_settings(config_dir())
    msg = build_report(results, settings.sender_email, settings.receivers_emails)
    try:
        send(msg, settings.sender_email, settings.sender_email_key)
    except OSError:
        logger.exception("Échec de l'envoi du rapport")   # journalisé, le run ne plante pas
    return 0

def show_list() -> int:
    """Affiche la liste des paires de backup. Jamais de questionary ici : appelé sans terminal."""
    manage_edit_list()
    logger.info("Opération sur la liste des paires de backup effectuée.")
    return 0

def add_pair() -> int:
    """Ajoute une nouvelle paire de backup. Jamais de questionary ici : appelé sans terminal."""
    manage_add_pair()
    return 0

def change_settings() -> int:
    """Ouvre le fichier settings.toml dans l'éditeur par défaut du système."""
    open_file_settings()
    return 0

def set_scheduler() -> int:
    """Configure le planificateur de tâches pour exécuter le backup automatiquement."""
    if is_installed():
        uninstall()
        
    hour, minute = safe_read_hour(config_dir())  # Pour récupérer l'heure de backup
    install(hour, minute)
    logger.info(f"Scheduler installed to run backup at {hour:02d}:{minute:02d}.")
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
                    q.Choice("Setup automatic backup", value="scheduler"),
                    q.Separator(),
                    q.Choice("Quit", value="exit")
                ]
            )
            action = menu.unsafe_ask()
            logger.debug(f"Selected action: {action}")

            match action:
                case "exit":
                    logger.info("Exiting the application.")
                    q.print("Exiting the application.")
                    return 0
                case "list":
                    show_list()
                case "add":
                    add_pair()
                case "settings":
                    change_settings()
                case "launch":
                    executer_tous_backups()
                case "scheduler":
                    set_scheduler()
    except KeyboardInterrupt:
        q.print("\nInterrompu.")
        logger.info("User interrupted the application with Ctrl+C.")
        return 130 



if __name__ == "__main__":
    sys.exit(main())