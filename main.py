import json
import os
import sys
import time

import requests
from bs4 import BeautifulSoup

from zipfile import ZipFile 

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

def downloadISOFile(link, name):
    with open(name, "wb") as newFile:
        response = requests.get(link, stream=True)
        total_length = response.headers.get('content-length')
        if total_length is None: # no content length header
            newFile.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                newFile.write(data)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) + f" {int(100*dl/total_length)} %" )    
                sys.stdout.flush()
            print('')


def downloadKeyFile(link, name):
    response = requests.get(link)
    with open(name, "wb") as newFile:
        newFile.write(response.content)

def unZipFile(fileRoute):
    with ZipFile(fileRoute, 'r') as zObject: 
        zObject.extractall() 

def removeFile(fileRoute):
    try:
        os.remove(fileRoute)
    except:
        print(f'Error removing {fileRoute}')

def downloadAndUnzip(route, text, isISO):
    TMPFILE='tmp.zip'
    print(f"Downloading {text}...")
    downloadISOFile(route, TMPFILE) if isISO else downloadKeyFile(route, TMPFILE)   
    print(f'Unzipping {text}...\n')
    unZipFile(TMPFILE)
    removeFile(TMPFILE)

def downloadPS3Element(element):
    link=element['link']
    title=element['title']

    downloadAndUnzip(PS3_ISOS_URL+link, f'{title} ISO', True)
    downloadAndUnzip(PS3_KEYS_URL+link, f'{title} Key', False)
    print(f'\n{title} downloaded :)\n')


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
                   downloadPS3Element(filteredList[desiredFileNumber])   

                else:
                    print(f'Number not in valid range (1-{filteredListLen})\n')
                    time.sleep(2)
                searchInput=''
            
            except ValueError:
                searchInput=desiredFileNumber
            except Exception as e:
                print(e)

        else:
            print('No elements found \n')
            searchInput=''

main()