import json

import requests
from bs4 import BeautifulSoup

PS3_ISOS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203/'
PS3_KEYS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203%20-%20Disc%20Keys/'
FILE_JSON_URL = 'listPS3Titles.json'


def getPS3List():
    try:
        with open(FILE_JSON_URL, 'r') as file:
            print(f'{FILE_JSON_URL} exist...')
            list_files = json.load(file)
            list_files_len = len(list_files)
            if list_files_len > 0:
                print(f'{FILE_JSON_URL} has {list_files_len} titles')
                return list_files
    except Exception as e:
        print(e)

    print('Downloading PS3 list...')
    PS3_titles_response = requests.get(PS3_ISOS_URL)

    available_PS3_titles = []

    print('Converting data...')
    soup = BeautifulSoup(PS3_titles_response.content, features='html.parser')
    links = soup.select('table#list tbody tr')
    links.pop(0)

    for current_link in links:
        try:
            linkElement = current_link.select('td.link a')[0]
            sizeElement = current_link.select('td.size')[0]

            available_PS3_titles.append(
                {'title': linkElement.text, 'link': linkElement['href'], 'size': sizeElement.text})

        except:
            error = 1

    print(f'Downloaded {len(available_PS3_titles)} titles')

    print('Saving in file...')
    with open(FILE_JSON_URL, 'w') as file:
        file.write(json.dumps(available_PS3_titles))
        file.close()

    print(f'Saved in {FILE_JSON_URL}')

    return available_PS3_titles


list = getPS3List()
