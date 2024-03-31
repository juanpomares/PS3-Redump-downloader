import json
import time

import requests
from bs4 import BeautifulSoup

PS3_ISOS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203/'
PS3_KEYS_URL = 'https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%203%20-%20Disc%20Keys/'
FILE_JSON_URL = 'listPS3Titles.json'


def getPS3List():
    try:
        with open(FILE_JSON_URL, 'r') as file:
            print(f'{FILE_JSON_URL} exists...')
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

def printList(list):
    for index, element in enumerate(list):
        print(f"{index+1}. {element['title']} ({element['size']})")
    print('')

def filterList(list, search):
    searchInput=search.lower()
    filteredList=[]

    for element in list:
        if searchInput in element['title'].lower():
            filteredList.append(element)

    return filteredList

def downloadPS3Element(element):
    print(element)

def main():
    PS3List = getPS3List()
    print('\n\n', end='')

    searchInput=''
    while True:
        if searchInput == '':
            print('Find PS3 title to download: ', end='')
            searchInput=input()
        
        filteredList=filterList(PS3List, searchInput)
        filteredListLen=len(filteredList)

        if filteredListLen>0:
            printList(filteredList)
            print('Enter PS3 number: ', end='')
            desiredFileNumber=input()

            try:
                desiredFileNumber=int(desiredFileNumber)-1
                if desiredFileNumber>=0 and desiredFileNumber<filteredListLen:
                    print('Downloading ', end='')
                    print(filteredList[desiredFileNumber])   

                else:
                    print(f'Number not in valid range (1-{filteredListLen})\n')
                    time.sleep(2)
                searchInput=''
            
            except:
                searchInput=desiredFileNumber


        else:
            print('No elements found \n')
            searchInput=''

main()