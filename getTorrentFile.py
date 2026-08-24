import os
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


MINERVA_BASE_URL = "https://minerva-archive.org"


def getTorrentFile(rom_id, destination_folder):
    torrent_file_path = os.path.join(destination_folder, "temp.torrent")

    if os.path.isfile(torrent_file_path):
        print(
            f"Torrent file already exists at {torrent_file_path}. Skipping download.")
        return torrent_file_path

    rom_url = f"{MINERVA_BASE_URL}/rom?id={rom_id}"

    print(f"Downloading torrent file from '{rom_url}'...")

    response = requests.get(rom_url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, features="html.parser")

    download_element = soup.select_one('a#download[href*=".torrent"]')

    if not download_element:
        raise RuntimeError(
            f"Torrent download link was not found at '{rom_url}'.")

    torrent_url = urljoin(MINERVA_BASE_URL, download_element["href"])

    torrent_response = requests.get(torrent_url, timeout=60)
    torrent_response.raise_for_status()

    with open(torrent_file_path, "wb") as torrent_file:
        torrent_file.write(torrent_response.content)

    print(f"Torrent file downloaded: {torrent_file_path}")

    return torrent_file_path
