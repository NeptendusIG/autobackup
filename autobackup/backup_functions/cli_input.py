
from autobackup import logger, SETTINGS_PATH
from utility import File

def choose_configuration():
    print("\n-- Choisissez parmi la liste actuelle --")
    configurations = {i: config for i, config in enumerate(File.JsonFile.get_value(SETTINGS_PATH, "configurations"))}
    for line_idx, config_key in configurations.items():
        print(f"{line_idx + 1}: {config_key}")
    try:
        choosen_line = int(input("\tChoisissez un fichier (0 pour annuler) : ...")) -1
        if choosen_line < 0:
            logger.info("OP:Remove source: CANCELED\n")
            return
        if choosen_line > line_idx:
            logger.info("OP:Remove source: CANCELED (out of file range)\n")
            return
        return configurations[choosen_line]
    except Exception:
        logger.error("OP:Remove source: CANCELED (invalid input)\n")
        return


