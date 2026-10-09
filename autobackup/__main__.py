#####################################
#          Titre - Date             #
#####################################
# NOTES :
"""
"""
# -- IMPORTS --
# Modules
#import importlib, main_settings
import sys, schedule, time, os
from utility import Settings, File, InputUtil, GUI
from autobackup.backup_functions.functions import single_backup, count_limited_backup, space_limited_backup, schedule_time_delay, schedule_fixed_hour
from autobackup.backup_functions.manage_configurations import ask_path_target, get_initial_parameters, user_edit_parameters
from autobackup.backup_functions.cli_input import choose_configuration
"""Used :
create_list_for_path, get_archiveable_jsonlines, add_target, delete_target
full_backup, schedule_fixed_hour, increment,"""
from autobackup.backup_functions.functions import get_fname

# -- LOGGING --
import logging
from autobackup import log as log_setup
from autobackup import SETTINGS_PATH
from autobackup.exception_classes import CancelInteruption, InvalidInput

log = logging.getLogger(__name__)

# -- FONCTIONS DÉFINIES --
def launch_auto_backup():
    log_setup.setup_daemon(foreground=True)
    log.info("OP:Launch Backup: START")
    frequence_modes = {
        "calendar_based": schedule_fixed_hour,
        "delay_based": schedule_time_delay
    }
    archiving_modes = {
        "by_count_limit": count_limited_backup,
        "by_space": space_limited_backup,
        "single": single_backup
    } 
    File.JsonFile.set_value(SETTINGS_PATH, "is_running", True)
    # 1 - Récupérer les configurations
    configurations = File.JsonFile.get_value(SETTINGS_PATH, "configurations")
    for config_name, config in configurations.items():
        log.info(f"Launch Backup: Setting Up a config ({config_name})")
        # 2 - Récupérer les paramètres
        #    fréquence/moments/timer
        source_path = config["source_path"]
        backup_path = config["backup_path"]
        frequence_mode = config["frequence_mode"]
        frequence_value = config["frequence_value"]
        log.debug(f"Setting up config: {get_fname(source_path)} to {get_fname(backup_path)} ({frequence_mode})")
        assert frequence_mode in frequence_modes, f"Mode de fréquence invalide : {frequence_mode}"
        #    nombre d'archives conservées / nommage des sauvegardes
        archiving_mode = config["archiving_mode"]
        mode_value = config["archiving_value"]
        assert archiving_mode in archiving_modes, f"Mode d'archivage invalide : {archiving_mode}"
        #    notification (oui/non) / valeur de notification
        has_notification: bool = config.get("notify_mode", False)
        notify_value = config.get("notify_value", {})
        # 3 - Créer la fonction performant le backup
        backup_maker = lambda: archiving_modes[archiving_mode](source_path, backup_path, mode_value)
        notification_sender = lambda: None
        # 4 - Programmer la tâche
        frequence_modes[frequence_mode](backup_maker, frequence_value)
    else: 
        log.info("OP:Launch Backup: All task SET\n")
    # 5 - Démarrer la boucle
    while True:
        schedule.run_pending()
        time.sleep(1)
        if not File.JsonFile.get_value(SETTINGS_PATH, "is_running", default=False, handle_keyERROR=True):
            break


def ajouter_fichier():
    log.info("OP:Adding source: START"); time.sleep(0.05)
    # - 1 - Montrer fichiers actuels
    print("-- Liste actuelle --")
    configurations: list = File.JsonFile.get_value(SETTINGS_PATH, "configurations").keys()
    print(*configurations, sep="\n", end="\n\n")
    # - 2 - Demander fichier source (FICHIER/DOSSIER)
    try:
        path, name = ask_path_target()
    except CancelInteruption:
        log.info("OP:Adding source: CANCELED")
        return False
    except InvalidInput:
        log.info("OP:Adding source: INVALID INPUT")
        return False
    except FileNotFoundError:
        log.info("OP:Adding source: FileNotFound")
        return False
    except Exception as e:
        log.error("OP:Adding source: ERROR\n\t%s" % e)
        raise e
    # - 3 - Demander dossier de backup (DESTINATION)
    backup_dir = GUI.ask_dir()
    if not backup_dir : # None or ""
        log.info("OP:Adding source: CANCELED")
        return False
    if not os.path.exists(backup_dir):
        log.info("OP:Adding source: FileNotFound\n\t%s" % backup_dir)
        return False
    # - 4 - Initialiser et ouvrir les paramètres de configuration
    config = get_initial_parameters(path, backup_dir)
    # - 5 - Ajouter la cible
    configurations: dict = File.JsonFile.get_value(SETTINGS_PATH, "configurations")
    configurations.update({name: config})
    File.JsonFile.set_value(SETTINGS_PATH, "configurations", configurations)    
    log.info("OP:Target Adding: ADDED ()")


def retirer_target():
    # 1 Montrer les cibles actives
    log.info("OP:Remove source: START"); time.sleep(0.05)
    config_name = choose_configuration()
    # 2 Supprimer la cible
    existing_configs = File.JsonFile.get_value(SETTINGS_PATH, "configurations")
    del existing_configs[config_name]
    File.JsonFile.set_value(SETTINGS_PATH, "configurations", existing_configs)
    # 3 Si pas d'erreur, confirmer
    log.info(f"OP:Remove source: COMPLETE ({config_name})\n")


def changer_reglages():
    # 1 Choisir la config à modifier
    log.info("OP:Change settings: START"); time.sleep(0.05)
    config_name = choose_configuration()
    # 2 Activer la fenêtre de modifiaction des paramètres
    editied_config = user_edit_parameters(config_name)
    # 3 Enregistrer/Vérifier les modifications
    File.JsonFile.DictOfDicts.set_value(SETTINGS_PATH, "configurations", sub_key=config_name, value=editied_config, can_add_key=False)
    log.info(f"OP:Change settings: COMPLETE ({config_name})\n")

def arreter_application():
    File.JsonFile.set_value(SETTINGS_PATH, "is_running", False)
    log.info("OP:STOP Application: COMPLETE")


# -- VARIABLES INITIALES --
major_actions = {
    "Ajouter un fichier/élément": ajouter_fichier,
    "Retirer un fichier/élément": retirer_target,
    "Vérifier/Changer les réglages": changer_reglages,
    "Activer Backup": launch_auto_backup,
    "Désactiver Backup": arreter_application,
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
    log_setup.setup_cli(verbose=1)  # INFO sur stderr
    log.info("UTIL: START Session")
    first_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if first_arg:
        log.info(f"Master: New action: asked for ({first_arg})")
        action = associate_longargs.get(first_arg) or associate_shortargs.get(first_arg)
        major_actions[action]()
    else:
        log.info(f"Master: New action: asked for")
        while True:    
            new_consol_command()


def new_consol_command():
    # set options
    log.info(f"Master: New action: asked for")
    time.sleep(0.05)
    for idx, key in enumerate(major_actions, 1):
        print(f"{idx}: {key}")
    cmd = InputUtil.ask_int("une option, terminez par activer le backup.")
    print()
    cmd_keyname = list(major_actions.keys())[cmd-1]
    major_actions[cmd_keyname]()
    log.info(f"Master: New action: processed ({cmd_keyname})\n")


# -- PROGRAMME --
if __name__ == '__main__':
    time.sleep(0.01)
        # Proposer modifs et changements
    print("-- Programme de backup automatique --\n")
    main()






















