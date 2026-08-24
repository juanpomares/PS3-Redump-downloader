import os
import sys
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


MINERVA_BASE_URL = "https://minerva-archive.org"


def getResponse(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    return response


def getPage(url):
    response = getResponse(url)

    return BeautifulSoup(response.content, features="html.parser")


def getTorrentFile(rom_id, destination_folder):
    torrent_file_path = os.path.join(destination_folder, "temp.torrent")

    if os.path.isfile(torrent_file_path):
        print(
            f"Torrent file already exists at {torrent_file_path}. Skipping download.")
        return torrent_file_path

    rom_url = f"{MINERVA_BASE_URL}/rom?id={rom_id}"

    print(f"Downloading torrent file from '{rom_url}'...")

    soup = getPage(rom_url)

    download_element = soup.select_one('a[href*=".torrent"]')

    if not download_element:
        raise RuntimeError(
            f"Torrent download link was not found at '{rom_url}'.")

    torrent_url = urljoin(MINERVA_BASE_URL, download_element["href"])

    torrent_data = getResponse(torrent_url).content

    with open(torrent_file_path, "wb") as torrent_file:
        torrent_file.write(torrent_data)

    print(f"Torrent file downloaded: {torrent_file_path}")

    return torrent_file_path


def getPS3ListByUrl(url):
    print(f"Downloading list from '{url}' ...")

    available_entries = []

    print(" - Converting data...")

    soup = getPage(url)
    entries = soup.select('div.entry:not(.search_back)')

    for current_entry in entries:
        try:
            link_element = current_entry.select_one('a[href^="/rom?id="]')
            size_element = current_entry.select_one("span")

            if not link_element or not size_element:
                continue

            href = link_element.get("href", "")
            entry_id = parse_qs(urlparse(href).query).get("id", [None])[0]

            if not entry_id:
                continue

            available_entries.append({
                "title": link_element.get_text(strip=True),
                "size": size_element.get_text(strip=True),
                "id": entry_id
            })
        except Exception as e:
            print(f"  Error processing entry: {e}")

    entries_len = len(available_entries)
    if entries_len == 0:
        print(f" Error: No titles found at '{url}'")
        sys.exit(-1)

    print(f" - List loaded with {entries_len} titles")
    return available_entries
