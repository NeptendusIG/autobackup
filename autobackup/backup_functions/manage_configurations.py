##############################################
# Functional Module to manage configurations #
##############################################

# - IMPORTS -
import os
from autobackup import logger, SETTINGS_PATH
from utility import File, GUI

# - CLASSES (LOGGING) -
from autobackup.exception_classes import CancelInteruption, InvalidInput


# - VARIABLES -
default_config = {
    "source_path": "",
    "backup_path": "",
    "frequence": "date_fixed",  # or timer
    "frequence_value": {
        "base": "weekly",
        "subsets": [0, 3, 5],  # 0: Monday, 1: Tuesday, 2: Wednesday, 3: Thursday, 4: Friday, 5: Saturday, 6: Sunday
        "time": "00:00"
    },
    "mode": "by_count_limits",  # or by_space or alone (NOT by_time_limits because same as counts by calculation)
    "mode_value": {
        "max_elemnents": 5,
        "max_space": 100,  # in Mo
        "name_format": "{date}"  # or count or timestamp
    }
}


# - FUNCTIONS -
# 1 - New Configuration
def ask_path_target() -> [tuple, Exception]:
    """Ask for File or Directory"""
    print("Ajouter un fichier ou un dossier ?")
    answer = input("fichier/folder (f/fd) : ").strip().lower()
    if answer == "f":
        source_path = File.ask_file("Ajouter élément pour backup")
    elif answer == "fd":
        source_path = File.ask_dir("Ajouter élément pour backup")
    else:
        print("Choix invalide")
        raise InvalidInput("Invalid user input for file or folder : %s" % answer)
    if not source_path:
        logger.info("OP:Adding source: CANCELED\n")
        raise CancelInteruption("Cancelled")
    if not os.path.exists(source_path):
        logger.info("OP:Adding source: FileNotFound\n\t%s\n" % source_path)
        raise FileNotFoundError("File not found : %s" % source_path)
    return source_path, os.path.basename(source_path)


def get_initial_parameters(source_path, backup_path):
    default = {
        "source_path": source_path,
        "backup_path": backup_path,
        "frequence_mode": "calendar_based",  # or delay_based
        "frequence_value": {
            "base": "weekly",
            "subsets": [0, 3, 5],  # 0: Monday, 1: Tuesday, 2: Wednesday, 3: Thursday, 4: Friday, 5: Saturday, 6: Sunday
            "time": "00:00"
        },
        "archiving_mode": "by_count_limits",  # or by_space or alone (NOT by_time_limits because same as counts by calculation)
        "archiving_value": {
            "max_elemnents": 5,
            "max_space": 100,  # in Mo
            "name_format": "{date}"  # or count or timestamp
        },
        "notify_mode": False,
        "notify_value": {
            "email": None,
        }
    }
    return default

# 2 - Access Settings/Parameters
