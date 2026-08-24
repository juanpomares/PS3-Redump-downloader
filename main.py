import json
import os
from pathlib import Path
from shutil import copyfileobj
import subprocess
import sys
import time
import zipfile
import configparser
from datetime import datetime

from requestUtils import getPS3ListByUrl, getTorrentFile
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

from torrentUtils import downloadFileWithLibTorrent

config = {}
TMP_FOLDER_PATHNAME = ''
TMP_ISO_FOLDER_PATHNAME = ''
TMP_KEY_FOLDER_PATHNAME = ''


def isGameListValid(game_list):
    if not isinstance(game_list, list):
        return False

    for game in game_list:
        if not isinstance(game, dict):
            return False
        if not all(key in game for key in ['title', 'size', 'game_id', 'key_id']):
            return False

    return True


def renameInvalidFile(file_name):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    invalid_file_name = os.path.join(
        os.path.dirname(file_name),
        f"{timestamp}.invalid.{os.path.basename(file_name)}"
    )

    os.replace(file_name, invalid_file_name)

    return invalid_file_name


def getFileListFromJSON(file_name):
    if not os.path.isfile(file_name):
        return None

    try:
        with open(file_name, 'r') as file:
            print(f"{config['LIST_FILES_JSON_NAME']} exists...")
            list_files = json.load(file)

        list_files_len = len(list_files)
        if list_files_len > 0 and isGameListValid(list_files):
            print(
                f"{config['LIST_FILES_JSON_NAME']} has {list_files_len} titles")
            return list_files

    except Exception as e:
        print(f"Error reading JSON file '{file_name}': {e}")

    invalid_file_name = renameInvalidFile(file_name)
    print(f"{config['LIST_FILES_JSON_NAME']} is empty or invalid. Old file renamed to '{invalid_file_name}'. Re-downloading...")

    return None


def getPS3List():
    json_file_path = os.path.join(
        TMP_FOLDER_PATHNAME, config['LIST_FILES_JSON_NAME'])
    json_file_name = f"{config['TMP_FOLDER_NAME']}/{config['LIST_FILES_JSON_NAME']}"

    final_list = getFileListFromJSON(json_file_path)

    if final_list is not None:
        return final_list

    games_list = getPS3ListByUrl(config['ISO_URL'])
    keys_list = getPS3ListByUrl(config['KEY_URL'])

    keys_by_title = {
        key['title']: key
        for key in keys_list
    }

    final_list = []

    for game in games_list:
        title = game['title']

        key_entry = keys_by_title.get(title)

        if not key_entry:
            continue

        final_list.append({
            'title': title,
            'size': game['size'],
            'game_id': game['id'],
            'key_id': key_entry['id']
        })

    print(f'List loaded with {len(final_list)} titles')

    with open(json_file_path, 'w') as file:
        json.dump(final_list, file, indent=4, sort_keys=True)

    print(f'Saved in {json_file_name}')

    return final_list


def printList(_list):
    for index, element in enumerate(_list):
        print(f"{index + 1}. {element['title']} ({element['size']})")
    print('')


def filterList(_list, search):
    searches = search.strip().lower().split()

    return [
        element
        for element in _list
        if all(
            search in element['title'].lower()
            for search in searches
        )
    ]


def downloadFileUsingExternalTorrentClient(torrent_file_path, file_name_to_download, destination_file_path):
    destination_file_path = os.path.abspath(destination_file_path)
    torrent_file_path = os.path.abspath(torrent_file_path)

    destination_folder = os.path.dirname(destination_file_path)

    if os.path.isfile(destination_file_path):
        print(f"File already exists: {destination_file_path}")
        return destination_file_path

    print(
        f"\nPlease open the following torrent file with your preferred torrent client:\n"
        f"'{torrent_file_path}'"
    )

    print(
        f"\nDownload only '{file_name_to_download}' and copy it to:\n"
        f"'{destination_folder}'"
    )

    openExplorer(destination_folder)

    print("\nWaiting for the file to be copied...")
    input("Press Enter to start checking for the file...")

    while not os.path.isfile(destination_file_path):
        print(
            f"\nFile not found! Make sure "
            f"'{file_name_to_download}' has been downloaded "
            f"and copied to:\n"
            f"'{destination_folder}'"
        )

        input("\tPress Enter to check again...")

    print(f"\nFile found: '{destination_file_path}'\n")

    return destination_file_path


# Original code from https://stackoverflow.com/a/73694796
def unZipFile(fzip):
    dest = Path(fzip).parent

    with zipfile.ZipFile(fzip) as zipf, tqdm(
            desc=' -  Extracting: ', unit="B", unit_scale=True, unit_divisor=1024,
            total=sum(getattr(i, "file_size", 0) for i in zipf.infolist()),
            ascii=' █'
    ) as pbar:
        for i in zipf.infolist():
            if not getattr(i, "file_size", 0):  # directory
                zipf.extract(i, os.fspath(dest))
            else:
                with zipf.open(i) as fi, open(os.fspath(dest / i.filename), "wb") as fo:
                    copyfileobj(CallbackIOWrapper(pbar.update, fi), fo)


def removeFile(fileRoute):
    try:
        os.remove(fileRoute)
    except:
        print(f'Error removing {fileRoute}')


def removeFiles(files):
    for file in files:
        removeFile(file)


def downloadFile(isISO, torrent_file_path, file_name_to_download, tmp_folder_path):
    destination_file_path = os.path.join(
        tmp_folder_path, file_name_to_download)

    download_using_external_client = config["EXTERNAL_ISO_DOWNLOAD" if isISO else "EXTERNAL_KEY_DOWNLOAD"]

    if download_using_external_client:
        return downloadFileUsingExternalTorrentClient(torrent_file_path, file_name_to_download, destination_file_path)

    return downloadFileWithLibTorrent(torrent_file_path, file_name_to_download, destination_file_path)


def unzipAndRemoveFile(zip_file_path, expected_file_path):
    if not os.path.isfile(zip_file_path):
        return False

    try:
        unZipFile(zip_file_path)

    except (zipfile.BadZipFile, EOFError) as e:
        print(f"Invalid or incomplete ZIP '{zip_file_path}': {e}")

        if os.path.exists(expected_file_path):
            removeFile(expected_file_path)

        removeFile(zip_file_path)
        return False

    except OSError as e:
        raise RuntimeError(f"Could not extract '{zip_file_path}': {e}"
                           ) from e

    if not os.path.isfile(expected_file_path):
        print(
            f"The ZIP was extracted, but the expected file "
            f"was not found: {expected_file_path}"
        )

        removeFile(zip_file_path)
        return False

    removeFile(zip_file_path)
    return True


def downloadAndUnzip(rom_id, title, isISO):
    is_iso_string = "ISO" if isISO else "Key"
    print(f" # {is_iso_string} file...")

    tmp_folder_path = TMP_ISO_FOLDER_PATHNAME if isISO else TMP_KEY_FOLDER_PATHNAME

    unzipped_file_name = f"{title}.{'iso' if isISO else 'dkey'}"
    unzipped_file_path = os.path.join(tmp_folder_path, unzipped_file_name)

    if os.path.isfile(unzipped_file_path):
        print(' - File previously downloaded :)', end='\n\n')
        return

    zipped_file_name = f"{title}.zip"
    zipped_file_path = os.path.join(tmp_folder_path, zipped_file_name)

    if unzipAndRemoveFile(zipped_file_path, unzipped_file_path):
        print(' - File previously downloaded/extracted :)', end='\n\n')
        return

    torrent_file_path = getTorrentFile(rom_id, tmp_folder_path)

    downloaded_file_path = downloadFile(
        isISO, torrent_file_path, zipped_file_name, tmp_folder_path)

    if not unzipAndRemoveFile(downloaded_file_path, unzipped_file_path):
        raise RuntimeError(
            f"Could not extract the downloaded file: "
            f"{downloaded_file_path}"
        )

    print(" ")


def readGameKey(gameKeyRoute):
    try:
        with open(gameKeyRoute, 'r') as file:
            key = file.read()
            return key.strip()
    except Exception as e:
        print(e)
        return None


def openExplorer(fileName):
    path = os.path.join('.', fileName)
    is_file = os.path.isfile(path)

    if os.path.exists(path):
        if os.name == 'nt':  # Windows Systems
            subprocess.Popen(['explorer', '/select,', path]
                             if is_file else ['explorer', path])
        elif os.name == 'posix':  # Unix Systems (Linux, macOS)
            subprocess.Popen(['xdg-open', '--select', path]
                             if is_file else ['xdg-open', path])
    else:
        print(f"Error opening {fileName}.\n")


def decryptFile(gameName):
    key_route_name = os.path.join(TMP_KEY_FOLDER_PATHNAME, f"{gameName}.dkey")
    original_game_path_name = os.path.join(
        TMP_ISO_FOLDER_PATHNAME, f"{gameName}.iso")

    print(f"\nDecrypting {gameName} using PS3Dec ...")
    decrypted_key = readGameKey(key_route_name)
    if decrypted_key is None:
        print("Error getting decrypting game key :(\n")
        return

    command = f'ps3dec d key {decrypted_key} "{original_game_path_name}" "{gameName}.iso"'
    os.system(command)

    decrypted_file = f'{gameName}.iso'
    print(f"Generated '{decrypted_file}'...\n")

    removeFiles([original_game_path_name, key_route_name])

    openExplorer(decrypted_file)


def downloadPS3Element(element):
    title = element['title'].replace(".zip", "")

    print(f"\nSelected {title}\n")

    downloadAndUnzip(element['game_id'], title, isISO=True)
    downloadAndUnzip(element['key_id'], title, isISO=False)
    print(f'\n{title} downloaded :)')
    decryptFile(title)


def createFolder(folderPath):
    try:
        os.mkdir(folderPath)
    except OSError as error:
        print(
            f"Error creating '{config['TMP_FOLDER_NAME']}' folder {error}", end='\n\n')
        sys.exit(-1)


def checkFolder(folderPath):
    if not os.path.exists(folderPath):
        createFolder(folderPath)
    elif not os.path.isdir(folderPath):
        print(
            f"Please remove the file named as {config['TMP_FOLDER_NAME']}", end='\n\n')
        sys.exit(-1)


def checkWorkingFolders():
    current_dir = '.'

    global TMP_FOLDER_PATHNAME
    TMP_FOLDER_PATHNAME = os.path.join(current_dir, config['TMP_FOLDER_NAME'])
    checkFolder(TMP_FOLDER_PATHNAME)

    global TMP_ISO_FOLDER_PATHNAME
    TMP_ISO_FOLDER_PATHNAME = os.path.join(
        current_dir, config['TMP_FOLDER_NAME'], config['TMP_ISO_FOLDER_NAME'])
    checkFolder(TMP_ISO_FOLDER_PATHNAME)

    global TMP_KEY_FOLDER_PATHNAME
    TMP_KEY_FOLDER_PATHNAME = os.path.join(
        current_dir, config['TMP_FOLDER_NAME'], config['TMP_KEY_FOLDER_NAME'])
    checkFolder(TMP_KEY_FOLDER_PATHNAME)


def loadConfig():
    config_file_parser = configparser.ConfigParser(interpolation=None)
    config_file_parser.read('config.ini')

    global config
    config = {
        'ISO_URL': config_file_parser.get('url', 'ISO',
                                          fallback="https://minerva-archive.org/browse/Redump/Sony%20-%20PlayStation%203/"),
        'KEY_URL': config_file_parser.get('url', 'KEY',
                                          fallback="https://minerva-archive.org/browse/Redump/Sony%20-%20PlayStation%203%20-%20Disc%20Keys%20TXT/"),

        'LIST_FILES_JSON_NAME': config_file_parser.get('Download', 'LIST_FILES_JSON_NAME',
                                                       fallback="listPS3Titles.json"),
        'EXTERNAL_ISO_DOWNLOAD': config_file_parser.getint('Download', 'EXTERNAL_ISO', fallback=0) != 0,
        'EXTERNAL_KEY_DOWNLOAD': config_file_parser.getint('Download', 'EXTERNAL_KEY', fallback=0) != 0,
        'MAX_RETRIES': config_file_parser.getint('Download', 'MAX_RETRIES', fallback=-1),
        'DELAY_BETWEEN_RETRIES': config_file_parser.getint('Download', 'DELAY_BETWEEN_RETRIES', fallback=-1),
        'TIMEOUT_REQUEST': config_file_parser.getint('Download', 'TIMEOUT_REQUEST', fallback=-1),

        'TMP_FOLDER_NAME': config_file_parser.get('folder', 'TMP_FOLDER_NAME', fallback="tmp"),
        'TMP_ISO_FOLDER_NAME': config_file_parser.get('folder', 'TMP_ISO_FOLDER_NAME', fallback="iso_files"),
        'TMP_KEY_FOLDER_NAME': config_file_parser.get('folder', 'TMP_KEY_FOLDER_NAME', fallback="key_files"),
    }

    if config['MAX_RETRIES'] < 1:
        config['MAX_RETRIES'] = 5
    if config['DELAY_BETWEEN_RETRIES'] < 5:
        config['DELAY_BETWEEN_RETRIES'] = 5
    if config['TIMEOUT_REQUEST'] < 0:
        config['TIMEOUT_REQUEST'] = None


def main():
    loadConfig()
    checkWorkingFolders()

    list_titles = getPS3List()
    print('\n', end='')

    search_input = ''
    while True:
        if search_input == '':
            print('Find PS3 title to download: ', end='')
            search_input = input()

        filtered_list = filterList(list_titles, search_input)
        filtered_list_len = len(filtered_list)

        if filtered_list_len > 0:
            printList(filtered_list)
            print(f'Enter PS3 title number [1-{filtered_list_len}]: ', end='')
            file_number_input = input()

            try:
                file_number = int(file_number_input) - 1
                if 0 <= file_number < filtered_list_len:
                    downloadPS3Element(filtered_list[file_number])

                else:
                    print(
                        f'Number not in valid range (1-{filtered_list_len})\n')
                    time.sleep(2)
                search_input = ''

            except ValueError:
                search_input = file_number_input
            except Exception as e:
                print(e, end='\n\n')

        else:
            print('No elements found \n')
            search_input = ''


try:
    main()
except KeyboardInterrupt:
    print('\n\nBye Bye ;)')
