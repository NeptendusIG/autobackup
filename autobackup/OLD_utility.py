#####################################
#   Module Utilitaire - dec/2024    #
#####################################
# NOTES :
"""
Fonctions utilitaire classées grâce aux classes
 -> Ce sont exclusivement des méhodes de classes
* ORGANISATION *
- InputUtil
- File
- Formatting
- GetData      -> Fonctions spécifiques à ce projet
"""
# Fonction à caractère générale
# Pour constituer un module utilitaire
import os.path, shutil, math, subprocess, platform, json, logging.config, logging.handlers  # Basic
import smtplib, genanki  # Specific
from tkinter import Tk, filedialog
import ttkbootstrap as ttk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ** Ajouts aux Built-In **
# TYPE : str

# ** settings **
class Settings:
    @classmethod
    def setup_logging_json(cls, path_logconfig="logconfig.json"):
        config_file = os.path.abspath(path_logconfig)
        with open(config_file) as f:
            config = json.load(f)
        logging.config.dictConfig(config)
        return logging.getLogger("main")

    @classmethod
    def setup_logging(cls, logger_name="main"):
        try:
            import log_config  # config: dct et Filtres
        except ModuleNotFoundError as e:
            print(f"ModuleNotFoundError: {e}")
            return
        try:
            logging.config.dictConfig(log_config.config)
            return logging.getLogger(logger_name)
        except Exception as e:
            print(f"Exception: {e}")


# str.isfloat = isfloat


class InputUtil:

    @classmethod
    def ask_int(cls, context, other=[]):
        """Gestion input
        @pre: Phrase posée étant le context
        @post: gère les erreurs

        Notes : obligé d'entrer un entier supp à 0 (pas rien)"""
        print(f"Veuillez saisir {context} ")
        while True:
            try:
                length = int(input(f"Entrez : "))  # {context}
                if length > 0 or length in other:
                    return length
            except TypeError:
                print("La saisie doit être un entier")
            except Exception as e:
                print(f"Erreur : {e}")

    @classmethod
    def ask_iterable(cls, other=[]):
        """Gestion input
        @pre: Phrase posée étant le context, type de donnée à entrer/fournir
        @post: gère les erreurs

        Notes : obligé d'entrer un entier supp à 0 (pas rien)"""
        type1 = list
        type2 = int
        print(f"Veuillez saisir des valeurs séparées par un espace")
        while True:
            try:
                length = type1(type2(dat) for dat in input(f"Entrez : ").split())  # {context}
                if isinstance(length, type1) or length in other:
                    return length
            except TypeError:
                print(f"La saisie doit être un {type}")
            except Exception as e:
                print(f"Erreur : {e}")

    @classmethod
    def commands(cls, cmd_input, dico, obj=None):
        """Traitement de commandes présentes dans dictionnaire
        @pre: command et dictionnaire
            dictionaire = {"cmd": (func, args-len, method/func, type, "context" or <ask_parameters>)}
            Si la longueur des arg ne correspond pas,
                soit type est donné, alors ask_input(type, context)
                soit type est None, alors exécute la func à <ask_parameters> (fonction fournie)
        @post: éxecution de la fonction associée dans le dictionnaire
            (return le return de la fonction)
        """
        parts = cmd_input.strip().split()
        parts = [Formatting.digitpart(part, True) for part in parts]
        cmd = parts[0]
        if cmd not in dico:
            return "cmd not found"
        if all([len(parts) < nbre_args for nbre_args in dico[cmd][1]]):
            if dico[cmd][3] is None:  # dico[cmd][3] (type de donnée)
                parts.append(dico[cmd][4]())
            elif dico[cmd][3] is int:
                parts.append(demande_int(dico[cmd][4]))
        if dico[cmd][2] == "method":
            # get object (else error)
            parts.insert(1, obj)

        result = dico[cmd][0](*parts[1:])
        return result

    @classmethod
    def take_command_one_character(cls, cmd_dict, context=None):
        if context is None:
            context = "\nEntrez Commande: "
        while True:
            cmd, *_ = input(context)
            if cmd not in cmd_dict:
                continue
            if cmd == "":
                break
            cmd_dict[cmd]()


class File:
    """Functions on files
    - window to select a file
    - window to select a directory
    - copy file to a directory
    - open a file (with system)
    - création d'un fichier sous n'importe quel cas (existe déjà, requiers dirs, ...)
    -
    """

    @classmethod
    def ask_file(cls, context="fichier", type=None, multiple=False):
        """Ask for a file (not a dir)
        pre:  context, filetype(optional)
        post: file navigation window
              if file selected, file path
        - Peut entrainer un coonfli entre fenêtre Tkinter"""
        root1 = Tk()
        root1.withdraw()  # cacher la fenlêtre principale

        filepath = filedialog.askopenfilename(
            # initialdir=None,  # Répertoire initial où la boîte de dialogue s'ouvre
            title=f"Choisir {context}",  # Titre de la boîte de dialogue
            # filetypes=type,    # Types de fichiers autorisés, par exemple [("Fichiers image", "*.png;*.jpg")]
            # defaultextension="",  # Extension par défaut si l'utilisateur ne spécifie pas d'extension
            # initialfile="",    # Nom de fichier pré-rempli dans la boîte de dialogue
            # parent=None,       # Widget parent de la boîte de dialogue
            multiple=multiple,  # Permettre la sélection de plusieurs fichiers (True/False)
        )
        logger.info(filepath)
        return filepath

    @classmethod
    def ask_dir(cls, initialdir=os.getcwd(), can_cancel=True):
        """Can only select a directory"""
        root2 = Tk()
        root2.withdraw()  # Hide the main window

        folder_path = filedialog.askdirectory(initialdir=initialdir)  # Open a dialog for folder selection
        if os.path.isdir(folder_path):
            return folder_path
        elif not can_cancel:
            logger.info("Aucun dossier sélectionné -> return current cwd")
            return os.getcwd()
        logger.info("Aucun dossier sélectionné -> return None")

    @classmethod
    def copy_file_to(cls, base_file_path, directory_location):
        """Copy a file to a dir and return the new path if successful"""
        try:
            file_name = os.path.basename(base_file_path)
            new_file_path = os.path.join(directory_location, file_name)
            shutil.copy2(base_file_path, new_file_path)
            logger.info(f"Fichier copié: {new_file_path}")
        except Exception as e:
            logger.warning(f"Copie fichier : Error {e}")
            return False
        return new_file_path

    @classmethod
    def open_file(cls, file_path):
        """Show/open a file (any type)
        pre:  - file_path
              - import subprocess, platform
        """
        try:
            system = platform.system()
            if system == 'Windows':
                subprocess.run(['start', '""', file_path], shell=True)
            elif system == 'Darwin':
                subprocess.run(['open', file_path])
            elif system == 'Linux':
                subprocess.run(['xdg-open', file_path])
            else:
                print("Unsupported operating system")
        except Exception as e:
            print(f"An error occurred: {e}")

    @classmethod
    def create_file_tree(cls, path, can_make_dirs=True, default_content=None):
        """If it does not exist, Create the specified file and dirs if needed."""
        if os.path.exists(path):
            logger.info("\tAlready exists")
            return
        if not os.path.exists(parents_dir := os.path.dirname(path)) and not can_make_dirs:
            logger.warning(f"Parent DirNotFound: {parents_dir}")
            return
        (os.makedirs(parents_dir, exist_ok=True) if parents_dir else None)
        with open(path, 'w') as file:
            if default_content is not None:
                json.dump(default_content, file)
        logger.info("\tFile created")

    @classmethod
    def delete_line(cls, line_index, filepath):
        if not os.path.exists(filepath): return
        with open(filepath, 'r') as file:
            lines = file.readlines()
        if line_index > len(lines):
            logger.warning(f"Selected Out of the List ({line_index + 1})")
            return
        del lines[line_index]
        with open(filepath, 'w') as file:
            file.writelines(lines)

    class JsonFile:

        @classmethod
        def check_and_load_jsondict(cls, jsonfile_path: str) -> dict:
            """Check if file exists and load it in python"""
            if not os.path.exists(jsonfile_path):
                logger.warning(f"FileNotFound: {jsonfile_path}")
                return
            if os.path.splitext(jsonfile_path)[1] != '.json':
                logger.warning(f"JsonFileError: type must be json ({jsonfile_path})")
                return
            with open(jsonfile_path, 'rb') as jfile:
                content = json.load(jfile)
            if not isinstance(content, dict):
                logger.warning(f"JsonFileContentError: content must be dict")
                return
            return content

        @classmethod
        def get_value_jsondict(cls, key, jsonfile_path, handle_keyERROR=False, default_val=None):
            """get key for json file"""
            # Error handling
            if (dict_content := cls.check_and_load_jsondict(jsonfile_path)) is None:
                return
            # return value
            if handle_keyERROR:
                if key not in dict_content: logger.info(f"JsonFileContent: key not in j-dict")
                return dict_content.get(key, default_val)
            return dict_content[key]

        @classmethod
        def set_value_jsondict(cls, jsonfile_path, key, value, can_modify_key=True, can_add_key=True):
            """Set value for a key in a json file"""
            # Error handling
            if (dict_content := cls.check_and_load_jsondict(jsonfile_path)) is None:
                return
            if not can_modify_key and key in dict_content:
                logger.warning(f"JsonFileContent: key already exists")
                return False
            if not can_add_key and key not in dict_content:
                logger.warning(f"JsonFileContent: key not in json-dict")
                return False
            # Set value
            dict_content[key] = value
            with open(jsonfile_path, 'w') as jfile:
                json.dump(dict_content, jfile, indent=4)

    class JsonLine:

        @classmethod
        def made_list_of_jsonline(cls, filename):
            """Traduit un fichier json line liste de tuple (1line -> 1tuple)"""
            if not os.path.exists(filename):
                logger.warning("DATAFileNotFound: %s" % filename)
                return
            path_data = []
            with open(filename, "rb") as file:
                for line in file:
                    path_data.append(tuple(json.loads(line)))
                logger.info("Sources: \n%s\n" % path_data)
            return path_data

        @classmethod
        def add_a_jsonline(cls, information, filename="data/paths_list.json"):
            """Add a json line with [the source path, and the target path]"""
            if not os.path.exists(filename): return
            with open(filename, 'r') as file:
                data = [tuple(json.loads(line)) for line in file]
            data.append(information)
            with open(filename, 'w') as file:
                for entry in data:
                    json.dump(entry, file)
                    file.write('\n')


class Formatting:

    @classmethod
    def reforme(cls, data):
        """Rend les données entrées dans le type approprié
        @pre : nombre (entier, flaot, Complex) ou txt"""
        try:  # n est un nombre
            if float(data) >= 0:
                return max(abs(int(data)), float(data))
            else:
                return min(abs(int(data)), float(data))
        except:
            if isinstance(data, complex):  # AttributeError  #n est un complex
                if data == 0:
                    return 0  # sinon il donne 0+0j
                return data
            if ("−") in data:  # nombre négatif mal écrit
                return reforme(data.replace("−", "-"))
            if any(char in data for char in ".,;[](){}"):  # n est entr crochet/parenthèses
                for caract in ".,;[](){}":
                    data = data.replace(caract, "")
                data = reforme(data)  # re-tester
            else:
                print("Rentrez des données séparées par un espace")
                return False
            return data

    @classmethod
    def digitpart(cls, part, could_be_txt=False):
        """Retourne un nombre pour une chaine contenant une expression math"""
        parametre = ""
        for c in part:
            if c.isdigit() or c in "+/=.":
                parametre += c
        try:
            return eval(parametre)
        except ZeroDivisionError:
            print("Division par 0")
        except SyntaxError:
            if could_be_txt and parametre == "":
                return part
            else:
                print(f"Syntaxe invalide for {part} or {parametre}")
        except Exception as e:
            print(f"Erreur : {e}")

    @classmethod
    def round_significant(cls, number, n=2, base=10):
        if number == 0:
            return 0.0
        magnitude = n - int(math.floor(math.log(abs(number), base))) - 1
        return round(number, magnitude)


class OutNetwork:

    @classmethod
    def send_notif_mail(cls, receiver, message, subject="NOTIFICATION"):
        """
        Attention : n'encode pas les caractères {é, }
        """
        # SENDER CONFIG
        try:
            sender = File.JsonFile.get_value_jsondict("sender_mail", "main_settings.json")
            psw = File.JsonFile.get_value_jsondict("sender_mail_key", "main_settings.json")
        except Exception as e:
            logger.warning(f"Couldn't (get) SETTINGS mail sender : {e}")
            return
        # CONTENT
        text = f"Subject: {subject}\n\n{message}"
        # SET UP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, psw)
        # SENDING
        server.sendmail(sender, receiver, text)


class GetData:
    file_of_filepath = "files_history.txt"

    @classmethod
    def get_current_file(cls):
        with open("files_history.txt", 'r') as file:
            filepath = file.read()
        if os.path.exists(filepath):
            return filepath
        logging.error(f"Error NotFoundFile: {filepath}")


class GUI:
    @classmethod
    def set_basic_window(cls):
        nom = "Tableau des commandes"
        size = "300x450"
        themename = "journal"
        window = ttk.Window(themename=themename)  # tk.Tk()
        window.title(nom)
        window.geometry(size)
        # Titre principale
        label = ttk.Label(master=window, text="Ankization", font="Calibri 24 bold")
        label.pack()
        return window

    @classmethod
    def set_cmd_buttons(cls, window, commandes):
        # Input field
        input_frame = ttk.Frame(master=window)
        # Create buttons
        buttons = {}
        for name, func in commandes.items():
            logger.info(name)
            buttons[name] = ttk.Button(master=input_frame, text=name, command=func)
        # Add buttons to input field
        for button in buttons.values():
            button.pack(pady=5)
        # Ajouter les éléments (to window)
        input_frame.pack()


class Anki():
    @classmethod
    def create_cards_fromlist_ofdict(cls, dict_list):
        """Create cards from a list of dict
        pre:  list of dict
                dict = {"front": <type>, "back": <type>, "template": str}
        post: deck of genanki
        """
