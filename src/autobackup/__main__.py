"""
Démarre l'application principale.

--- Journey ---
1. Setup environment
2. Setup logging
3. Start the main loop
"""

import questionary as q

from pathlib import Path
from autobackup.logs import setup_logging



def setup_environment():
    return



def main_loop():
    # ... automatically setup the task (based on current settings).
    # see (or edit) the list of files to backup.
    # add a new pair of files to backup.
    # open settings (change time or email settings).
    # launch a backup now (the scheduled one stays in place).
    # see history of backups (with date, time, and status).

    while True:
        q.print("")
        main_action = q.select(
            "Select an action:",
            choices=[
                q.Choice("View/edit backup pairs", value="list"),
                q.Choice("Add a new backup pair", value="add"),
                q.Choice("Change settings", value="settings"),
                q.Choice("Launch backup now", value="launch"),
                q.Choice("View backup history", value="history"),
                q.Separator(),
                q.Choice("Exit", value="quit")
            ]
        ).ask()

        if main_action == "quit":
            q.print("Exiting the application.")
            break
        if main_action == "list":
            q.print("Viewing/editing backup pairs (not implemented yet).")
        elif main_action == "add":
            q.print("Adding a new backup pair (not implemented yet).")
        elif main_action == "settings":
            q.print("Changing settings (not implemented yet).")
        elif main_action == "launch":
            q.print("Launching backup now (not implemented yet).")
        elif main_action == "history":
            q.print("Viewing backup history (not implemented yet).")

    return


if __name__ == "__main__":
    # Setup environment
    setup_environment()

    # Setup logging
    setup_logging(Path.home() /"wksp_python"/"_ongoing"/"autobackup-project"/"logs" , verbose=True)

    # Start the main loop
    main_loop()