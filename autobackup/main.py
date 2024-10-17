#####################################
#          Titre - Date             #
#####################################
# NOTES :
"""
"""
# -- IMPORTS --
# Modules
#import importlib, main_settings
import sys
from utility import Settings, File, InputUtil
from backup_functions.functions import *
"""Used :
create_list_for_path, get_archiveable_jsonlines, add_target, delete_target
full_backup, schedule_fixed_hour, increment,"""

# Classes

# -- LOGGING --
logger = Settings.setup_logging("main")

# -- FONCTIONS DÉFINIES --
def launch_auto_backup():
    """"""
    accessible_increment_format = {
        "date": date_based,
        "count": counting,
        "horodatage": get_timestamp
    }
    # Récupérer paramètres
    heure = File.JsonFile.get_value_jsondict("heure", "main_settings.json")
    renaming_type = File.JsonFile.get_value_jsondict("format_of_backup_files", "main_settings.json")
    incrementing_func = accessible_increment_format[renaming_type]
    logger.info(f"OP:Lauching Backup: SET ({heure}, {renaming_type})")
    # Lancer opération avec voc_managing_functions paramétrées
    elements_list = get_paths_target_jsonlines()
    logger.info(f"OP:Lauching Backup: paths IMPORTED ({heure}, {renaming_type})")
    schedule_fixed_hour(lambda: full_backup(elements_list, incrementing_func), heure)



def ajouter_fichier():
    # Montrer fichiers actuels
    logger.info("OP:Adding source: START"); time.sleep(0.05)
    print("-- Liste actuelle --")
    for elem in get_paths_target_jsonlines(): print(f"{os.path.basename(elem[0])}")
    source_path = File.ask_file("Ajouter élément pour backup")
    # Demander fichier source et destination du backup
    if not source_path : # None or ""
        logger.info("OP:Adding source: CANCELED\n")
        return False
    if not os.path.exists(source_path):
        logger.info("OP:Adding source: FileNotFound\n\t%s\n" % source_path)
        return False
    backup_dir = File.ask_dir()
    if not backup_dir : # None or ""
        logger.info("OP:Adding source: CANCELED\n")
        return False
    # Appliquer les infos
    add_target(source_path, backup_dir)
    logger.info("OP:Target Adding: ADDED ()\n")


def retirer_target():
    # 1 Montrer les cibles actives
    logger.info("OP:Remove source: START"); time.sleep(0.05)
    name_list = []
    print("-- Choisissez parmi la liste actuelle --")
    for line_idx, (source, backup_dir) in enumerate(get_paths_target_jsonlines()):
        print(f"\t{line_idx + 1}: {os.path.basename(source)}")
        name_list.append(os.path.basename(source))
    try:
        choosen_line = int(input("Choisissez un fichier (0 pour annuler) : ...")) -1
        if choosen_line < 0:
            logger.info("OP:Remove source: CANCELED\n")
            return
        if choosen_line > len(name_list) - 1:
            logger.info("OP:Remove source: CANCELED (out of file range)\n")
            return
    except Exception:
        return
    if delete_target(choosen_line):
        logger.info(f"OP:Remove source: COMPLETE ({name_list[choosen_line]})\n")
        return
    logger.warning(f"OP:Remove source: FAILED ({name_list[choosen_line]})\n")


def changer_reglages():
    """
    Champs de paramètres :
        - temps -> heure/délais
        - format -> incrémentation/jour/Horodatage
    """
    logger.info("Main settings: try opening")
    File.open_file("main_settings.json")
    if os.path.exists("main_settings.json"):
        logger.info("OP:Main settings: OPENED\n")


# -- VARIABLES INITIALES --
major_actions = {
    "Activer Backup": launch_auto_backup,
    "Ajouter un fichier/élément": ajouter_fichier,
    "Retirer un fichier/élément": retirer_target,
    "Vérifier/Changer les réglages": changer_reglages,
}

# -- FONCTIONS MAÎTRES --
def new_consol_command():
    # set options
    logger.info(f"Master: New action: asked for")
    time.sleep(0.05)
    for idx, key in enumerate(major_actions, 1):
        print(f"{idx}: {key}")
    cmd = InputUtil.ask_int("une option, terminez par activer le backup.")
    print()
    cmd_keyname = list(major_actions.keys())[cmd-1]
    major_actions[cmd_keyname]()
    logger.info(f"Master: New action: processed ({cmd_keyname})\n")


# -- PROGRAMME --
if __name__ == '__main__':
    # - Variables -
    # - Environnement -
    create_list_for_path()
    create_list_for_path("main_settings.json")
    # - Programme -
    logger.info(f"UTIL: START Session")
    time.sleep(0.01)
        # Proposer modifs et changements
    print("-- Programme de backup automatique --\n")
    while True:
        new_consol_command()

        # logger.info(f"UTIL: END Session\n")























