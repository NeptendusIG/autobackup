import os, shutil, time, logging, json
import schedule
from datetime import datetime

from utility import File
from autobackup import SETTINGS_PATH
from autobackup.backup_functions.email_sender import OutNetwork

log = logging.getLogger(__name__)

count_backups = 0
count_files_in_backup = 0
count_directories_in_backup = 0

get_fname = lambda x: os.path.basename(x)
total_size = lambda x: sum([os.path.getsize(file) for file in os.listdir(x)])

# -- Step 1 : Fonctions performant les copies/backup --
"""def full_backup(list_of_archivable, incrementation):
    #Manage back-up for each element in the given list.
    #@pre: list of archivable -> bi-tuple (original_file_path, his_backup_folder, increment?)
    #     the format to add date or index to the backup
    #
    global count_files_in_backup, count_directories_in_backup
    count_files_in_backup = 0
    # Start
    increment = incrementation()
    log.info(f"OP:Processing Backup: STARTED <{increment}>")
    for (original, backup_dir) in list_of_archivable:
        if not os.path.exists(original):
            log.error(f"FileNotFound: {original}")
        elif os.path.isdir(original):
            count_directories_in_backup += 1
            new_backup_folder(original, backup_dir, increment)
        elif os.path.isfile(original):
            count_files_in_backup += 1
            new_backup_file(original, backup_dir, increment)
    log.info(f"OP:Processing Backup: FINISHED <{increment}>\n")
    terminate_backup_date()
"""

def new_backup_file(file_path, backup_folder, target_path):
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)
    # Générez un format pour le nouveau nom de fichier
    shutil.copy2(file_path, target_path)
    log.info(f"OP:Processing Backup: \tfile COPIED ({get_fname(file_path)}, {os.path.dirname(target_path) + ' / ' + get_fname(target_path)})\n")


def new_backup_folder(folder_path, backup_root, target_path):
    if not os.path.exists(backup_root):
        os.makedirs(backup_root)
    # Faire copie
    shutil.copytree(folder_path, target_path)
    log.info(f"OP:Processing Backup: \tdir COPIED ({get_fname(folder_path)}, {get_fname(target_path)})\n")

# -- By type --
def single_backup(file_path, backup_folder, settings:dict):
    """
    settings : {
    }
    """
    # 1 Obtenir et supprimer l'ancienne sauvegarde
    files = os.listdir(backup_folder)
    assert len(files) <= 1, "Too many files in the backup folder"
    # 2 Créer l'incrément/suffixe
    name, ext = os.path.splitext(os.path.basename(file_path))
    new_path = os.path.join(backup_folder, f"{name}_{ext}")
    # 3 Copier le fichier/Dossier
    if os.path.isfile(file_path):
        if len(files) == 1:
            os.remove(os.path.join(backup_folder, files[0]))
        new_backup_file(file_path, backup_folder, new_path)
    elif os.path.isdir(file_path):
        if len(files) == 1:
            os.rmdir(os.path.join(backup_folder, files[0]))
        new_backup_folder(file_path, backup_folder, new_path)
    log.info(f"OP:Processing Backup: FINISHED <{get_fname(new_path)}>\n")


def count_limited_backup (file_path, backup_folder, settings:dict):
    """
    settings : {
        "max_elements": int 
        "format_type": "date" or "count" or "timestamp"
        "count": int
    }
    """
    # 1 Obtenir et supprimer la plus ancienne si nécessaire
    files = os.listdir(backup_folder)
    while len(files) >= settings["max_elements"]:
        files.sort(lambda x: os.path.getctime(x))
        os.remove(os.path.join(backup_folder, files[0]))
        files = os.listdir(backup_folder)
    # 2 Créer l'incrément/suffixe
    name, ext = os.path.splitext(os.path.basename(file_path))
    new_filename = f"{name}_{count + 1}{ext}"
    new_path = os.path.join(backup_folder, new_filename)
    # 3 Copier le fichier/Dossier
    if os.path.isfile(file_path):
        new_backup_file(file_path, backup_folder, new_path)
    elif os.path.isdir(file_path):
        new_backup_folder(file_path, backup_folder, new_path)
    log.info(f"OP:Processing Backup: FINISHED <{get_fname(new_path)}>\n")


def space_limited_backup(file_path, backup_folder, settings:dict):
    """Manage backups file wieght limitation
    settings : {
        "max_space": int  # in Mo
        "format_type": "date" or "count" or "timestamp"
        "count": int
    """
    # 1 Supprimer anciennes sauvegardes si nécessaire
    files = os.listdir(backup_folder)
    files.sort(key=lambda x: os.path.getctime(x))
    while total_size(files) >= settings["max_space"]:
        os.remove(os.path.join(backup_folder, files[0]))
        files = os.listdir(backup_folder)
        files.sort(key=lambda x: os.path.getctime(x))
    # 2 Créer l'incrément/suffixe
    name, ext = os.path.splitext(os.path.basename(file_path))
    # with date format : 
    new_filename = f"{name}_{get_timestamp()}{ext}"
    new_path = os.path.join(backup_folder, new_filename) 
    # 3 Copier le fichier/Dossier
    if os.path.isfile(file_path):
        new_backup_file(file_path, backup_folder, new_path)
    elif os.path.isdir(file_path):
        new_backup_folder(file_path, backup_folder, new_path)
    log.info(f"OP:Processing Backup: FINISHED <{get_fname(new_path)}>\n")


   
# -- Auto repeat operation --
def schedule_fixed_hour(backup_func, freq_settings):
    """ Planifiez et exécuter la planification continument
    frequence : {
        base: "hourly" or "daily" or "weekly" or "monthly" or "yearly"
        subsets: [0, 3, 5]  # 0: Monday, 1: Tuesday, 2: Wednesday, 3: Thursday, 4: Friday, 5: Saturday, 6: Sunday
        sub-subset: [x, xx, xx, xx] ex: for day in specifics month from year
        time: "00:00"
    }
    """
    if freq_settings["base"] == "monthly":
        def job():
            today = datetime.now().day
            if today in freq_settings["subsets"]:
                backup_func()
        schedule.every().day.at(freq_settings["time"]).do(job)
    elif freq_settings["base"] == "weekly":
        def job():
            today = datetime.now().weekday()
            if today in freq_settings["subsets"]:
                backup_func()
        schedule.every().day.at(freq_settings["time"]).do(job)
    elif freq_settings["base"] == "daily":
        for hour in freq_settings["subsets"]:
            schedule.every().day.at(f"{str(hour).zfill(2)}:00").do(backup_func)
    elif freq_settings["base"] == "hourly":
        def job():
            minute = datetime.now().minute
            if minute in freq_settings["subsets"]:
                backup_func()
        schedule.every().minute.do(job)

    log.info(f"Scheduled for {freq_settings['base']} at {freq_settings['time']}")


def schedule_time_delay(backup_func, freq_settings):
    """ Planifiez et exécuter la planification selon intervalle répété
    frequence : {
        base: "minute" or "hourly" or "daily" or "weekly" or "monthly" or "yearly"
        multiplicator: int
        time: "00:00"
    }
    """
    # Get the settings
    base = freq_settings["base"]
    multiplicator = freq_settings["multiplicator"]
    daytime = freq_settings.get("time")
    # Schedule the backup
    if base == "monthly":
        schedule.every(multiplicator).month.at(daytime).do(backup_func)
    elif base == "weekly":
        schedule.every(multiplicator).week.at(daytime).do(backup_func)
    elif base == "daily":
        schedule.every(multiplicator).day.at(daytime).do(backup_func)
    elif base == "hourly":
        schedule.every(multiplicator).hour.do(backup_func)
    elif base == "minute":
        schedule.every(multiplicator).minutes.do(backup_func)

    log.info(f"Scheduled for every {multiplicator} {base} (at {daytime}) if set")


# -- Indexing and Adding Formats --
def get_timestamp(sep="_"):
    return datetime.now().strftime(f"%Y%m%d{sep}%H%M%S")


def counting(digit=3):
    global count
    count += 1
    return str(count - 1).zfill(digit)


def date_based():
    today = datetime.now()
    return today.strftime("%y_%m_%d")



# -- On the file (list of files paths) --
"""def create_list_for_path(path="data/paths_list.json"):
    if os.path.exists(path):
        log.info("\tAlready exists")
        return
    (os.makedirs(parents_dir, exist_ok=True) if (parents_dir := os.path.dirname(path)) else None)
    with open(path, 'w') as file:
        json.dump([], file)
    log.info("\tMemory Initiated")


def get_paths_target_jsonlines(filename="data/paths_list.json"):
    # ""Traduit un fichier json line liste de tuple (1line -> 1tuple)""
    if not os.path.exists(filename):
        log.warning("DATAFileNotFound: %s" % filename)
    path_data = []
    with open(filename, "rb") as file:
        for line in file:
            path_data.append(tuple(json.loads(line)))
        log.info("Sources: \n%s\n" % path_data)
    return path_data


def add_target(source, target, filename="data/paths_list.json"):
    @ ""Add a json line with [the source path, and the target path]""
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
        log.warning(f"Selected Out of the List ({line_index+1})")
        return False
    del lines[line_index]
    with open(memory_path, 'w') as file:
        file.writelines(lines)
    return True"""

# -- Terminate back up --
def terminate_backup_everytime():
    notif_is_activated = File.JsonFile.get_value(SETTINGS_PATH, "notification", default=False, handle_keyERROR=True)
    log.debug(str(notif_is_activated))
    if notif_is_activated:
        senders_mail = File.JsonFile.get_value(SETTINGS_PATH, "mails", default=[], handle_keyERROR=True)
        message = create_infomessage()
        for mail in senders_mail:
            OutNetwork.send_notif_mail(mail, message, subject="BACKUP INFO")
        log.info("Terminate: EMAIL report Sent")
    else:
        log.info("Terminate: No report set")


def d():
    notif_is_activated = File.JsonFile.get_value(SETTINGS_PATH, "notification", default=False, handle_keyERROR=True)
    if not notif_is_activated:
        log.info("OP:Terminate: No report set")
        return
    day_for_notif = File.JsonFile.get_value(SETTINGS_PATH, "notification_day", default=[], handle_keyERROR=True)
    if not any([is_weekday(datetime.today(), day_inx) for day_inx in day_for_notif]):
        log.info("OP:Terminate: Report not set for TODAY")
        return
    senders_mail = File.JsonFile.get_value(SETTINGS_PATH, "receiver_mails", default=[], handle_keyERROR=True)
    message = create_infomessage()
    for mail in senders_mail:
        OutNetwork.send_notif_mail(mail, message, subject="Gaetan tests - BACKUP INFO")
    log.info("OP:Terminate: EMAIL report Sent")


def create_infomessage():
    global count_backups, count_files_in_backup, count_directories_in_backup
    current_datetime = datetime.today()
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
        log.error("TERMINATE: Invalid date format")
        return False


# -- SANDBOX --
if __name__ == '__main__':
    # - Variables -
    file_to_backup = "/Users/gaetan/Docs/Objectifs/4_Apprendre/pythonProject/ProjetsEnCours/AutoBackUp/data/input/test.txt"
    backup_directory = "/Users/gaetan/Docs/Objectifs/4_Apprendre/pythonProject/ProjetsEnCours/AutoBackUp/data/output"
    backup_interval_minutes = 0.05  # Une fois par jour
    # - Programme -
    schedule_func_interval(lambda: full_backup([(file_to_backup, backup_directory)], increment), backup_interval_minutes)
