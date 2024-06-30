import json
import os
from pathlib import Path
from shutil import copyfileobj
import subprocess
import sys
import time
import zipfile
import configparser

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

config = {}
TMP_FOLDER_PATHNAME = ''
TMP_ISO_FOLDER_PATHNAME = ''
TMP_KEY_FOLDER_PATHNAME = ''


def getPS3List():
    json_file_path = os.path.join(TMP_FOLDER_PATHNAME, config['LIST_FILES_JSON_NAME'])
    json_file_name = f"{config['TMP_FOLDER_NAME']}/{config['LIST_FILES_JSON_NAME']}"

    try:
        with open(json_file_path, 'r') as file:
            print(f"{config['LIST_FILES_JSON_NAME']} exists...")
            list_files = json.load(file)
            list_files_len = len(list_files)
            if list_files_len > 0:
                print(f"{config['LIST_FILES_JSON_NAME']} has {list_files_len} titles")
                return list_files
    except:
        pass

    print('Downloading PS3 list...')
    ps3_titles_response = requests.get(config['ISO_URL'])

    available_ps3_titles = []

    print('Converting data...')
    soup = BeautifulSoup(ps3_titles_response.content, features='html.parser')
    links = soup.select('table#list tbody tr')
    links.pop(0)

    for current_link in links:
        try:
            link_element = current_link.select('td.link a')[0]
            size_element = current_link.select('td.size')[0]

            available_ps3_titles.append(
                {'title': link_element.text, 'link': link_element['href'], 'size': size_element.text})

        except:
            pass

    print(f'Downloaded {len(available_ps3_titles)} titles')

    with open(json_file_path, 'w') as file:
        file.write(json.dumps(available_ps3_titles))
        file.close()

    print(f'Saved in {json_file_name}')

    return available_ps3_titles


def printList(_list):
    for index, element in enumerate(_list):
        print(f"{index + 1}. {element['title']} ({element['size']})")
    print('')


def titleContainsWords(title, searches):
    for search in searches:
        if search not in title:
            return False

    return True


def filterList(_list, search):
    searches = search.strip().lower().split(" ")
    filtered_list = []

    for element in _list:
        if titleContainsWords(element['title'].lower(), searches):
            filtered_list.append(element)

    return filtered_list


def getFileSize(link):
    response = requests.get(link, headers={"Range": "bytes=0-1"})
    try:
        total_size = int(response.headers.get('content-range').split('/')[1])
    except:
        total_size = None

    return total_size


# Original code from https://stackoverflow.com/a/37573701
def downloadFile(link, name):
    total_size = getFileSize(link)

    retries = 0
    while retries < config["MAX_RETRIES"]:
        headers = {}

        first_byte = 0
        if total_size is not None and os.path.exists(name):
            first_byte = os.path.getsize(name)
            if first_byte >= total_size:
                print(f"The files {name} is downloaded previosly.")
                return
            headers = {"Range": f"bytes={first_byte}-{total_size}"}

        try:
            with requests.get(link, headers=headers, stream=True, timeout=config["TIMEOUT_REQUEST"],
                              verify=True) as response, open(name, "ab") as newFile:
                block_size = 1024
                if total_size is None:  # no content length header
                    newFile.write(response.content)
                else:
                    with tqdm(total=total_size, unit="B", unit_scale=True, unit_divisor=block_size,
                              desc=" - Downloading: ",
                              ascii=' █', initial=first_byte) as progress_bar:
                        for data in response.iter_content(block_size):
                            progress_bar.update(len(data))
                            newFile.write(data)

                        if total_size != 0 and progress_bar.n != total_size:
                            raise RuntimeError("Could not download file")
                        else:
                            break

        except (requests.ConnectionError, requests.Timeout, RuntimeError):
            retries += 1
            print(
                f"Connection error! Try again ({retries}/{config['MAX_RETRIES']}). Waiting {config['DELAY_BETWEEN_RETRIES']} secs...")
            time.sleep(config['DELAY_BETWEEN_RETRIES'])
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    if retries == config['MAX_RETRIES']:
        raise RuntimeError(f"Failed to download file after {config['MAX_RETRIES']} attempts.")


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


def downloadAndUnzip(route, title, isISO):
    is_iso_string = "ISO" if isISO else "Key"
    print(f" # {is_iso_string} file...")

    unzipped_file_name = f"{title}.{'iso' if isISO else 'dkey'}"

    if os.path.exists(os.path.join(TMP_ISO_FOLDER_PATHNAME if isISO else TMP_KEY_FOLDER_PATHNAME, unzipped_file_name)):
        print(' - File previosly downloaded :)', end='\n\n')
        return

    new_file_name = f"{title}.zip"
    tmp_file = os.path.join(TMP_ISO_FOLDER_PATHNAME if isISO else TMP_KEY_FOLDER_PATHNAME, new_file_name)

    downloadFile(route, tmp_file)
    unZipFile(tmp_file)
    removeFile(tmp_file)
    print(' ')


def readGameKey(gameKeyRoute):
    try:
        with open(gameKeyRoute, 'r') as file:
            key = file.read()
            return key.strip()
    except Exception as e:
        print(e)
        return None


def openExplorerFile(fileName):
    file_path = os.path.join('.', fileName)

    if os.path.exists(file_path):
        if os.name == 'nt':  # Windows Systems
            subprocess.Popen(['explorer', '/select,', file_path])
        elif os.name == 'posix':  # Unix Systems (Linux, macOS)
            subprocess.Popen(['xdg-open', '--select', file_path])
    else:
        print(f"Error opening {fileName}.\n")


def decryptFile(gameName):
    key_route_name = os.path.join(TMP_KEY_FOLDER_PATHNAME, f"{gameName}.dkey")
    original_game_path_name = os.path.join(TMP_ISO_FOLDER_PATHNAME, f"{gameName}.iso")

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

    openExplorerFile(decrypted_file)


def downloadPS3Element(element):
    link = element['link']
    title = element['title'].replace(".zip", "")

    print(f"\nSelected {title}\n")

    downloadAndUnzip(config['ISO_URL'] + link, title, True)
    downloadAndUnzip(config['KEY_URL'] + link, title, False)
    print(f'\n{title} downloaded :)')
    decryptFile(title)


def createFolder(folderPath):
    try:
        os.mkdir(folderPath)
    except OSError as error:
        print(f"Error creating '{config['TMP_FOLDER_NAME']}' folder {error}", end='\n\n')
        sys.exit(-1)


def checkFolder(folderPath):
    if not os.path.exists(folderPath):
        createFolder(folderPath)
    elif not os.path.isdir(folderPath):
        print(f"Please remove the file named as {config['TMP_FOLDER_NAME']}", end='\n\n')
        sys.exit(-1)


def checkWorkingFolders():
    current_dir = '.'

    global TMP_FOLDER_PATHNAME
    TMP_FOLDER_PATHNAME = os.path.join(current_dir, config['TMP_FOLDER_NAME'])
    checkFolder(TMP_FOLDER_PATHNAME)

    global TMP_ISO_FOLDER_PATHNAME
    TMP_ISO_FOLDER_PATHNAME = os.path.join(current_dir, config['TMP_FOLDER_NAME'], config['TMP_ISO_FOLDER_NAME'])
    checkFolder(TMP_ISO_FOLDER_PATHNAME)

    global TMP_KEY_FOLDER_PATHNAME
    TMP_KEY_FOLDER_PATHNAME = os.path.join(current_dir, config['TMP_FOLDER_NAME'], config['TMP_KEY_FOLDER_NAME'])
    checkFolder(TMP_KEY_FOLDER_PATHNAME)


def loadConfig():
    config_file_parser = configparser.ConfigParser(interpolation=None)
    config_file_parser.read('config.ini')

    global config
    config = {
        'ISO_URL': config_file_parser.get('url', 'ISO',
                                          fallback="https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203/"),
        'KEY_URL': config_file_parser.get('url', 'KEY',
                                          fallback="https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203%20-%20Disc%20Keys%20TXT/"),

        'LIST_FILES_JSON_NAME': config_file_parser.get('Download', 'LIST_FILES_JSON_NAME',
                                                       fallback="listPS3Titles.json"),
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
        config['MAX_RETRIES'] = 5
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
                    print(f'Number not in valid range (1-{filtered_list_len})\n')
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
