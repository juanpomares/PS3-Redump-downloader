import json
import os
from pathlib import Path
from shutil import copyfileobj
import subprocess
import sys
import time
import zipfile

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper

PS3_ISOS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203/'
PS3_KEYS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203%20-%20Disc%20Keys%20TXT/'
FILE_JSON_URL = 'listPS3Titles.json'

CURRENT_DIR=os.path.dirname(__file__) 
TMP_FOLDER_NAME = 'tmp'
TMP_FOLDER_PATHNAME = os.path.join(CURRENT_DIR, TMP_FOLDER_NAME)

def getPS3List():
    try:
        with open(FILE_JSON_URL, 'r') as file:
            print(f'{FILE_JSON_URL} exists...')
            list_files = json.load(file)
            list_files_len = len(list_files)
            if list_files_len > 0:
                print(f'{FILE_JSON_URL} has {list_files_len} titles')
                return list_files
    except:
        pass

    print('Downloading PS3 list...')
    ps3_titles_response = requests.get(PS3_ISOS_URL)

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

    print('Saving in file...')
    with open(FILE_JSON_URL, 'w') as file:
        file.write(json.dumps(available_ps3_titles))
        file.close()

    print(f'Saved in {FILE_JSON_URL}')

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


# Original code from https://stackoverflow.com/a/37573701
def downloadFile(link, name):
    with open(name, "wb") as newFile:
        response = requests.get(link, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024

        if total_size is None:  # no content length header
            newFile.write(response.content)
        else:
            with tqdm(total=total_size, unit="B", unit_scale=True, unit_divisor=1024, desc=" - Downloading: ",
                      ascii=' █') as progress_bar:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    newFile.write(data)

            if total_size != 0 and progress_bar.n != total_size:
                raise RuntimeError("Could not download file")


# Original code from https://stackoverflow.com/a/73694796
def unZipFile(fzip):
    dest = Path('.').expanduser()
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


def downloadAndUnzip(route, title, isISO):
    isISO_str="ISO" if isISO else "Key";
    TMP_FILE=f"{title}_{isISO_str}.zip"
    print(f" # {isISO_str} file...")
    downloadFile(route, TMP_FILE)
    unZipFile(TMP_FILE)
    removeFile(TMP_FILE)
    print(' ')


def readGameKey(gameName):
    game_key_route = f"{gameName}.dkey"
    try:
        with open(game_key_route, 'r') as file:
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

def renameISOFile(title):
    oldName=f"{title}.iso"
    newName=f"{title}_original.iso"
    try:
        os.rename(oldName, newName)
    except:
        print(f'Error renaming ISO file')

def decryptFile(gameName):
    print(f"\nDecrypting {gameName} using PS3Dec ...")
    decrypted_key = readGameKey(gameName)
    if decrypted_key is None:
        print("Error getting decrypting game key :(\n")
        return
    
    renameISOFile(gameName)
    command = f'ps3dec d key {decrypted_key} "{gameName}_original.iso" "{gameName}.iso"'
    os.system(command)

    decrypted_file = f'{gameName}.iso'
    print(f"Generated '{decrypted_file}'...\n")
    openExplorerFile(decrypted_file)


def downloadPS3Element(element):
    link = element['link']
    title = element['title'].replace(".zip", "")

    print(f"\nSelected {title}\n")

    downloadAndUnzip(PS3_ISOS_URL + link, title, True)
    downloadAndUnzip(PS3_KEYS_URL + link, title, False)
    print(f'\n{title} downloaded :)')
    decryptFile(title)

def createFolder(folderPath):
    try:
        os.mkdir(folderPath)
    except OSError as error:
        print(f"Error creating 'tmp' folder", end='\n\n')
        sys.exit(-1)

def checkFolder(folderPath):
    if not os.path.exists(folderPath):
        createFolder(folderPath)
    elif not os.path.isdir(folderPath):
        print('Please remove the file named as tmp', end='\n\n')
        sys.exit(-1)

def checkWorkingFolders():
    checkFolder(TMP_FOLDER_NAME)    


def main():
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
