import json
import os
import sys
import time

import requests
from bs4 import BeautifulSoup

from zipfile import ZipFile

PS3_ISOS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203/'
PS3_KEYS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203%20-%20Disc%20Keys%20TXT/'
FILE_JSON_URL = 'listPS3Titles.json'
TMP_FILE = 'tmp.zip'


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


def printProgressPercentage(current, total):
    current_percentage = f"{int(current * 100 / total)}".rjust(3)
    total_characters_length = len(f"{total}")
    current_value_string = f"{current}".rjust(total_characters_length)
    return f"{current_value_string}/{total} ({current_percentage} % )"


def printProgressBar(current, total, characters=50):
    current_percentage = current / total
    done = int(characters * current_percentage)
    progress_bar = "\r[%s>%s]" % ('=' * done, ' ' * (characters - done)) if current_percentage < 0.99 else "\r[%s]" % (
                '=' * (characters + 1))
    sys.stdout.write(f"{progress_bar} {printProgressPercentage(current, total)}")
    sys.stdout.flush()


def downloadFileWithProgress(link, name):
    with open(name, "wb") as newFile:
        response = requests.get(link, stream=True)
        total_length = response.headers.get('content-length')
        if total_length is None:  # no content length header
            newFile.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                newFile.write(data)
                printProgressBar(dl, total_length)
            print('')


def downloadNormalFile(link, name):
    response = requests.get(link)
    with open(name, "wb") as newFile:
        newFile.write(response.content)


def downloadFile(link, name, withProgress):
    (downloadFileWithProgress if withProgress else downloadNormalFile)(link, name)


def unZipFile(fileRoute):
    with ZipFile(fileRoute, 'r') as zObject:
        zObject.extractall()


def removeFile(fileRoute):
    try:
        os.remove(fileRoute)
    except:
        print(f'Error removing {fileRoute}')


def downloadAndUnzip(route, isISO):
    file_type_text = "ISO" if isISO else "Key"
    print(f"Downloading {file_type_text} file...")
    downloadFile(route, TMP_FILE, isISO)
    print(f'Unzipping...\n')
    unZipFile(TMP_FILE)
    removeFile(TMP_FILE)


def readGameKey(gameName):
    game_key_route = f"{gameName}.dkey"
    try:
        with open(game_key_route, 'r') as file:
            key = file.read()
            return key.strip()
    except Exception as e:
        print(e)
        return None


def decryptFile(gameName):
    print(f"\nDecrypting {gameName}...")
    decrypted_key = readGameKey(gameName)
    if decrypted_key is None:
        print("Error getting decrypting game key :(\n")
        return

    command = f'ps3dec d key {decrypted_key} "{gameName}.iso" "{gameName}_decrypted.iso"'
    os.system(command)
    print(f"Generated '{gameName}_decrypted.iso'...\n")


def downloadPS3Element(element):
    link = element['link']
    title = element['title'].replace(".zip", "")

    print(f"\nDownloading {title}")

    downloadAndUnzip(PS3_ISOS_URL + link, True)
    downloadAndUnzip(PS3_KEYS_URL + link, False)
    print(f'{title} downloaded :)')
    decryptFile(title)


def main():
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
            print(f'Enter PS3 title number[1-{filtered_list_len}]: ', end='')
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
