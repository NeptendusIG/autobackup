#####################################
#      py-Projet - xx/xx/xxxx       #
#          __init__.py              #
#####################################
import os
from pathlib import Path
# - PROJECT DATA -


# - IMPORTS -
from utility import Settings

# - SETTINGS -
logger = Settings.setup_logging("debugging")
logger.info("LOGGING Initialized")

    # Config File
default_config = {
    "user": {
        "name": "John Doe",
        "email": ""
    },
    "configurations":{
        "source_path1":{
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
        },
        "source_path2":{}
    }
}
root_dir = Settings.ConfigPath.set_directories("autobackup")
Settings.ConfigPath.set_jsonfile(root_dir, "config.json", default_config, exist_ok=True)
SETTINGS_PATH = Settings.ConfigPath.get_path("autobackup", "config.json")

# - VARIABLES (GLOBALES) -
SETTINGS_PATH
__title__ = "Auto back up"
__options__ = {
    "add_path": ("-a, --add", "Ajouter un fichier à sauvegarder"),  # SUBCOMMANDS : -d --dir, -f --file  (ouvre boîtes de dialogues)
    "run_backup": ("-r, --run", "Lancer la sauvegarde automatique"),
    "remove_path": ("-rm, --remove", "Retirer un fichier à sauvegarder"),
}


