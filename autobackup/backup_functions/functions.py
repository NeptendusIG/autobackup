import os, shutil, time, logging, json
import schedule
import datetime

from utility import File, OutNetwork
from autobackup import logger

count_backups = 0
count_files_in_backup = 0
count_directories_in_backup = 0

# -- Step 1 : Backuping --
def full_backup(list_of_archivable, incrementation):
    """Manage back-up for each element in the given list.
    @pre: list of archivable -> bi-tuple (original_file_path, his_backup_folder, increment?)
          the format to add date or index to the backup
    """
    global count_files_in_backup, count_directories_in_backup
    count_files_in_backup = 0
    # Start
    increment = incrementation()
    logger.info(f"OP:Processing Backup: STARTED <{increment}>")
    for (original, backup_dir) in list_of_archivable:
        if not os.path.exists(original):
            logger.error(f"FileNotFound: {original}")
        elif os.path.isdir(original):
            count_directories_in_backup += 1
            new_backup_folder(original, backup_dir, increment)
        elif os.path.isfile(original):
            count_files_in_backup += 1
            new_backup_file(original, backup_dir, increment)
    logger.info(f"OP:Processing Backup: FINISHED <{increment}>\n")
    terminate_backup_date()


def new_backup_file(file_path, backup_folder, increment=""):
    # Obtenez le nom du fichier sans le chemin, et séparer l'extension
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)
    # Créez le dossier de sauvegardes s'il n'existe pas
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)
    # Générez un format pour le nouveau nom de fichier
    backup_path = os.path.join(backup_folder, f"{name}_{increment}{ext}")
    shutil.copy2(file_path, backup_path)
    logger.info(f"OP:Processing Backup: \tfile COPIED ({file_name}, {increment})\n")


def new_backup_folder(folder_path, backup_root, increment=""):
    name = os.path.basename(folder_path)
    if not os.path.exists(backup_root):
        os.makedirs(backup_root)
    # Faire copie
    backup_path = os.path.join(backup_root, f"{name}{increment}")
    shutil.copytree(folder_path, backup_path)
    logger.info(f"OP:Processing Backup: \tdir COPIED ({name}, {increment})\n")


# -- Auto repeat operation --
def schedule_func_interval(backup_func, interval_minutes):
    """ Planifiez et exécuter la planification continument"""
    schedule.every(interval_minutes).minutes.do(backup_func)
    while True:
        schedule.run_pending()
        time.sleep(1)


def schedule_fixed_hour(backup_func, op_hour="20:00"):
    schedule.every().day.at(op_hour).do(backup_func)
    logger.info(f"Scheduled for {op_hour} every day")
    while True:
        schedule.run_pending()
        time.sleep(1)


# -- Indexing and Adding Formats --
def get_timestamp(sep="_"):
    return datetime.now().strftime(f"%Y%m%d{sep}%H%M%S")


def counting(digit=3):
    global count
    count += 1
    return str(count - 1).zfill(digit)


def date_based():
    today = datetime.datetime.now()
    return today.strftime("%y_%m_%d")


# -- On the file (list of files paths) --
def create_list_for_path(path="data/paths_list.json"):
    if os.path.exists(path):
        logger.info("\tAlready exists")
        return
    (os.makedirs(parents_dir, exist_ok=True) if (parents_dir := os.path.dirname(path)) else None)
    with open(path, 'w') as file:
        json.dump([], file)
    logger.info("\tMemory Initiated")


def get_paths_target_jsonlines(filename="data/paths_list.json"):
    """Traduit un fichier json line liste de tuple (1line -> 1tuple)"""
    if not os.path.exists(filename):
        logger.warning("DATAFileNotFound: %s" % filename)
    path_data = []
    with open(filename, "rb") as file:
        for line in file:
            path_data.append(tuple(json.loads(line)))
        logger.info("Sources: \n%s\n" % path_data)
    return path_data


def add_target(source, target, filename="data/paths_list.json"):
    """Add a json line with [the source path, and the target path]"""
    if not os.path.exists(filename): return
    with open(filename, 'r') as file:
        data = [tuple(json.loads(line)) for line in file]
    data.append((source, target))
    with open(filename, 'w') as file:
        for entry in data:
            json.dump(entry, file)
            file.write('\n')


def delete_target(line_index, memory_path="data/paths_list.json"):
    if not os.path.exists(memory_path): return False
    with open(memory_path, 'r') as file:
        lines = file.readlines()
    if line_index > len(lines):
        logger.warning(f"Selected Out of the List ({line_index+1})")
        return False
    del lines[line_index]
    with open(memory_path, 'w') as file:
        file.writelines(lines)
    return True

# -- Terminate back up --
def terminate_backup_everytime():
    notif_is_activated = File.JsonFile.get_value_jsondict("notification")
    logger.debug(str(notif_is_activated))
    if notif_is_activated:
        senders_mail = File.JsonFile.get_value_jsondict("mails")
        message = create_infomessage()
        for mail in senders_mail:
            OutNetwork.send_notif_mail(mail, message, subject="BACKUP INFO")
        logger.info("Terminate: EMAIL report Sent")
    else:
        logger.info("Terminate: No report set")


def terminate_backup_date():
    notif_is_activated = File.JsonFile.get_value_jsondict("notification", "main_settings.json")
    if not notif_is_activated:
        logger.info("OP:Terminate: No report set")
        return
    day_for_notif = File.JsonFile.get_value_jsondict("notification_day", "main_settings.json")
    if not any([is_weekday(datetime.datetime.today(), day_inx) for day_inx in day_for_notif]):
        logger.info("OP:Terminate: Report not set for TODAY")
        return
    senders_mail = File.JsonFile.get_value_jsondict("receiver_mails", "main_settings.json")
    message = create_infomessage()
    for mail in senders_mail:
        OutNetwork.send_notif_mail(mail, message, subject="Gaetan tests - BACKUP INFO")
    logger.info("OP:Terminate: EMAIL report Sent")


def create_infomessage():
    global count_backups, count_files_in_backup, count_directories_in_backup
    current_datetime = datetime.datetime.today()
    message_structure = (
        "Backup process occurred now: {}\n"
        "Backup index: {}\n"
        "Files in backup: {}\n"
        "Directories in backup: {}\n"
    )
    info_message = message_structure.format(
        current_datetime.strftime("%Y-%m-%d"), count_backups, count_files_in_backup,
        count_directories_in_backup
    )
    return info_message


def is_weekday(date_object, weekday_index):
    try:
        #date_object = datetime.strptime(date_str, "%Y-%m-%d")
        day_of_week = date_object.weekday()
        return day_of_week == weekday_index
    except ValueError:
        logger.error("TERMINATE: Invalid date format")
        return False


# -- SANDBOX --
if __name__ == '__main__':
    # - Variables -
    file_to_backup = "/Users/gaetan/Docs/Objectifs/4_Apprendre/pythonProject/ProjetsEnCours/AutoBackUp/data/input/test.txt"
    backup_directory = "/Users/gaetan/Docs/Objectifs/4_Apprendre/pythonProject/ProjetsEnCours/AutoBackUp/data/output"
    backup_interval_minutes = 0.05  # Une fois par jour
    # - Programme -
    schedule_func_interval(lambda: full_backup([(file_to_backup, backup_directory)], increment), backup_interval_minutes)
