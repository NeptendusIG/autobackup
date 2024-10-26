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
from autobackup.backup_functions.functions import *
from autobackup.backup_functions.manage_configurations import ask_path_target
"""Used :
create_list_for_path, get_archiveable_jsonlines, add_target, delete_target
full_backup, schedule_fixed_hour, increment,"""


# -- LOGGING --
from autobackup import logger 
from autobackup import SETTINGS_PATH
from autobackup.exception_classes import CancelInteruption, InvalidInput

# -- FONCTIONS DÉFINIES --
def launch_auto_backup():
    """"""
    accessible_increment_format = {
        "date": date_based,
        "count": counting,
        "horodatage": get_timestamp
    }
    # Récupérer paramètres
    heure = File.JsonFile.get_value_jsondict("heure", SETTINGS_PATH)
    renaming_type = File.JsonFile.get_value_jsondict("format_of_backup_files", SETTINGS_PATH)
    incrementing_func = accessible_increment_format[renaming_type]
    logger.info(f"OP:Lauching Backup: SET ({heure}, {renaming_type})")
    # Lancer opération avec voc_managing_functions paramétrées
    elements_list = get_paths_target_jsonlines()
    logger.info(f"OP:Lauching Backup: paths IMPORTED ({heure}, {renaming_type})")
    schedule_fixed_hour(lambda: full_backup(elements_list, incrementing_func), heure)



def ajouter_fichier():
    logger.info("OP:Adding source: START"); time.sleep(0.05)
    # - 1 - Montrer fichiers actuels
    print("-- Liste actuelle --")
    configurations = File.JsonFile.get_value(SETTINGS_PATH, "configurations").keys()
    print(*configurations, sep="\n", end="\n\n")
    source_path = File.ask_file("Ajouter élément pour backup")
    # - 2 - Demander fichier source (FICHIER/DOSSIER)
    try:
        path, name = ask_path_target()
    except CancelInteruption:
        logger.info("OP:Adding source: CANCELED\n")
        return False
    except InvalidInput:
        logger.info("OP:Adding source: INVALID INPUT\n")
        return False
    except FileNotFoundError:
        logger.info("OP:Adding source: FileNotFound\n\t%s\n" % source_path)
        return False
    # - 3 - Demander dossier de backup (DESTINATION)
    backup_dir = File.ask_dir()
    if not backup_dir : # None or ""
        logger.info("OP:Adding source: CANCELED\n")
        return False
    if not os.path.exists(backup_dir):
        logger.info("OP:Adding source: FileNotFound\n\t%s\n" % backup_dir)
        return False
    # - 4 - Initialiser et ouvrir les paramètres de configuration
    get
    logger.info("OP:Target Adding: ADDED ()\n")


def retirer_target():
    # 1 Montrer les cibles actives
    logger.info("OP:Remove source: START"); time.sleep(0.05)
    print("-- Choisissez parmi la liste actuelle --")
    configurations = {i: config for i, config in enumerate(File.JsonFile.get_value(SETTINGS_PATH, "configurations"))}
    for line_idx, config_key in configurations.items():
        print(f"\t{line_idx + 1}: {config_key}")
    try:
        choosen_line = int(input("Choisissez un fichier (0 pour annuler) : ...")) -1
        if choosen_line < 0:
            logger.info("OP:Remove source: CANCELED\n")
            return
        if choosen_line > line_idx:
            logger.info("OP:Remove source: CANCELED (out of file range)\n")
            return
    except Exception:
        logger.info("OP:Remove source: CANCELED (invalid input)\n")
        return
    # 2 Supprimer la cible
    existing_configs = File.JsonFile.get_value(SETTINGS_PATH, "configurations")
    del existing_configs[configurations[choosen_line]]
    File.JsonFile.set_value(SETTINGS_PATH, "configurations", existing_configs)
    # 3 Si pas d'erreur, confirmer
    logger.info(f"OP:Remove source: COMPLETE ({configurations[choosen_line]})\n")


def changer_reglages():
    """
    Champs de paramètres :
        - temps -> heure/délais
        - format -> incrémentation/jour/Horodatage
    """
    logger.info("Main settings: try opening")
    File.open_file(SETTINGS_PATH)
    if os.path.exists(SETTINGS_PATH):
        logger.info("OP:Main settings: OPENED\n")


# -- VARIABLES INITIALES --
major_actions = {
    "Activer Backup": launch_auto_backup,
    "Ajouter un fichier/élément": ajouter_fichier,
    "Retirer un fichier/élément": retirer_target,
    "Vérifier/Changer les réglages": changer_reglages,
    "Quitter": sys.exit
}

associate_longargs = {
    "--run": "Activer Backup",
    "--add": "Ajouter un fichier/élément",
    "--remove": "Retirer un fichier/élément"
}

associate_shortargs = {
    "-r": "Activer Backup",
    "-a": "Ajouter un fichier/élément",
    "-rm": "Retirer un fichier/élément"
}

# -- FONCTIONS MAÎTRES --
def main():
    first_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if first_arg:
        logger.info(f"Master: New action: asked for ({first_arg})")
        action = associate_longargs.get(first_arg) or associate_shortargs.get(first_arg)
        major_actions[action]()
    else:
        logger.info(f"Master: New action: asked for")
        new_consol_command()


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
    logger.info(f"UTIL: START Session")
    time.sleep(0.01)
        # Proposer modifs et changements
    print("-- Programme de backup automatique --\n")
    main()






















