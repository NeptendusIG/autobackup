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
from autobackup.operations.send_notification import manage_send_notification
from autobackup.paths import ensure_environment, log_dir, config_dir
from autobackup.pairs import ensure_files, read_valid_hour, read_settings, default_hour, default_hour_setting
from autobackup.operations.edit_list import manage_edit_list
from autobackup.operations.add import manage_add_pair
from autobackup.operations.edit_settings import open_file_settings
from autobackup.operations.backup import run_backup, run_backup
from autobackup.scheduler import install, uninstall, is_installed
from autobackup.notify import send_notification, build_notification
from autobackup.errors import describe, ConfigError, SchedulerError, PairsError, SettingsError



logger = logging.getLogger("autobackup.main" )


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée principal de l'application.
    """
    parser = argparse.ArgumentParser(prog="autobackup", description="Autobackup - Automatic backup tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--run", action="store_true", help="Run the backup immediately without user interaction")

    args = parser.parse_args(argv)

    ensure_environment()
    log_path = setup_logging(log_dir(), verbose=args.verbose)
    ensure_files(config_dir())  # Placer après setup_logging pour que les logs soient capturés
    logger.info(f"Logging initialized. Log file: {log_path}")

    if args.run:
        logger.info("Running backup immediately due to --run flag.")
        try:
            return executer_tous_backups()
        except PairsError as e:
            logger.critical("Backup pairs could not be read: %s", describe(e))
            logger.debug("PairsError details: %s", e, exc_info=True)
            try:
                manage_send_notification([], critical_message="Backup could not be run due to Invalid settings.")
                logger.info("Notification sent regarding backup failure.")
            except Exception as e:
                logger.error("Failed to send notification of failure: %s", describe(e))
                return 1
            return 1
        except SettingsError as e:
            logger.critical("Settings could not be read: %s", describe(e))
            logger.debug("SettingsError details: %s", e, exc_info=True)
            return 1
        except ConfigError as e:
            logger.critical("Configuration error: %s", describe(e))
            logger.debug("ConfigError details: %s", e, exc_info=True)
            return 1
    return interactive_menu()


def executer_tous_backups() -> int:
    """Lance le backup. Jamais de questionary ici : appelé sans terminal.
    Raises:
        FileNotFoundError: si le dossier source ou destination n'existe pas.
        OSError: si une erreur de copie se produit.
        ConfigError: Si les pairs ou settings sont illisibles.
    """
    logger.debug("Starting backup execution...")


    # TODO: Read_pairs could be out of run_backup()
    try: 
        results = run_backup()
    except PairsError as e:
        raise e
    except ConfigError as e:
        logger.debug("Configuration error while running backup: %s", describe(e))
        raise e
    except OSError as e:
        logger.critical("Error occurred while running backup: %s", describe(e))
        raise PairsError("Error occurred while running backup") from e

    try:
        manage_send_notification(results)
    except OSError:
        logger.exception("Échec de l'envoi du rapport")   # journalisé, le run ne plante pas
    success = 1 - sum(1 for r in results if r.success) // len(results) if results else 1
    return success 


def show_list() -> int:
    """Affiche la liste des paires de backup. Jamais de questionary ici : appelé sans terminal."""
    logger.debug("Starting to manage the backup pairs list...")
    try:
        manage_edit_list()
        logger.info("Opération sur la liste des paires de backup effectuée.")
    except ConfigError as e:
        logger.error("Configuration error while managing the backup pairs list: %s", describe(e))
        return 1
    except OSError as e:
        logger.error("OS error while managing the backup pairs list: %s", describe(e))
        return 1
    return 0


def add_pair() -> int:
    """Ajoute une nouvelle paire de backup. Jamais de questionary ici : appelé sans terminal."""
    logger.debug("Starting to add a new backup pair.")
    try:
        manage_add_pair()
        logger.info("New backup pair added successfully.")
    except ConfigError as e:
        logger.error("Configuration error while adding a new backup pair: %s", describe(e))
        return 1
    except OSError as e:
        logger.error("OS error while adding a new backup pair: %s", describe(e))
        return 1
    return 0


def change_settings() -> int:
    """Ouvre le fichier settings.toml dans l'éditeur par défaut du système."""
    logger.debug("Start opening settings in native editor.")
    try:
        open_file_settings()
    except FileNotFoundError as e:
        logger.critical("Settings file not found (user must restart the application): %s", e)
        return 1
    except OSError as e:
        # Settings could exist and be accessible, but the editor could fail.
        logger.error("Failed to open settings file: %s", e)
        return 1
    logger.info("Settings file opened in editor successfully.")
    return 0


def set_scheduler() -> int:
    """Configure le planificateur de tâches pour exécuter le backup automatiquement."""
    logger.debug("Start installing task for automatic backup.")
        
    hour, minute = default_hour()
    try:
        hour, minute = read_valid_hour(config_dir())  
    except ValueError as e:
        logger.warning("Valeur invalide dans settings (chemin=%s), utilise défaut=%s : %s", config_dir(), default_hour_setting(), e)
    except OSError as e:
        logger.warning("Lecture de l'heure impossible. Origine: %s", describe(e))
    except SettingsError as e:
        logger.error("Erreur de lecture des paramètres. Origine: %s", describe(e))
        q.print(f"Please check the settings to fix the issue: {config_dir()}", style="fg:red")

    try:
        install(hour, minute)
    except SchedulerError as e:
        logger.critical("Échec de l'installation du planificateur. Origine: %s", describe(e))
        logger.debug("SchedulerError details: %s", e, exc_info=True)
        return 1

    logger.info("Scheduler installed to run backup at %02d:%02d.", hour, minute)
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
                    try:
                        executer_tous_backups()
                    except ConfigError as e:
                        logger.error("Backup execution failed due to configuration error: %s", describe(e))
                        logger.debug("ConfigError details: %s", e, exc_info=True)
                        q.print(f"Please check the settings and data files to fix the issue: {config_dir()}", style="fg:red")
                    except OSError as e:
                        logger.critical("Backup execution failed due to OS error: %s", describe(e))
                        logger.debug("OSError details: %s", e, exc_info=True)
                        return 1
                case "scheduler":
                    set_scheduler()
    except KeyboardInterrupt:
        q.print("\nInterrompu.")
        logger.info("User interrupted the application with Ctrl+C.")
        return 130 



if __name__ == "__main__":
    sys.exit(main())