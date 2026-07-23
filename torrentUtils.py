import os
import time

import libtorrent as lt
from tqdm import tqdm


def getTorrentInfo(torrent_file_path):
    torrent_size = os.path.getsize(torrent_file_path)
    torrent_limits = {"max_buffer_size": torrent_size + 1024 * 1024}

    return lt.torrent_info(torrent_file_path, torrent_limits)


def findTorrentFileIndex(torrent_info, torrent_file_to_download):
    torrent_files = torrent_info.files()

    target_file_name = os.path.basename(torrent_file_to_download).casefold()

    matches = []

    for file_index in range(torrent_files.num_files()):
        internal_file_path = torrent_files.file_path(file_index)
        internal_file_name = os.path.basename(internal_file_path).casefold()

        if internal_file_name == target_file_name:
            matches.append({"index": file_index, "path": internal_file_path})

    if not matches:
        raise FileNotFoundError(
            f"'{torrent_file_to_download}' was not found inside the torrent."
        )

    if len(matches) > 1:
        matching_paths = "\n".join(f" - {match['path']}" for match in matches)

        raise RuntimeError(
            f"Multiple files named "
            f"'{torrent_file_to_download}' were found:\n"
            f"{matching_paths}"
        )

    match = matches[0]

    print(f"Torrent file found: {match['path']} (index: {match['index']})")

    return match["index"]


def downloadTorrentFileByIndex(torrent_info, torrent_index, destination_file_path):
    destination_file_path = os.path.abspath(destination_file_path)

    destination_folder = os.path.dirname(destination_file_path)
    destination_file_name = os.path.basename(destination_file_path)

    if os.path.isfile(destination_file_path):
        print(f"File already exists: {destination_file_path}")

        return destination_file_path

    torrent_files = torrent_info.files()

    if not 0 <= torrent_index < torrent_files.num_files():
        raise IndexError(f"Torrent index out of range: {torrent_index}")

    selected_file_size = torrent_files.file_size(torrent_index)
    torrent_info.rename_file(torrent_index, destination_file_name)

    file_priorities = [0] * torrent_files.num_files()
    file_priorities[torrent_index] = 7

    torrent_session = lt.session({"listen_interfaces": "0.0.0.0:0"})

    torrent_handle = torrent_session.add_torrent({
        "ti": torrent_info,
        "save_path": destination_folder,
        "file_priorities": file_priorities
    })

    print(f"Downloading {destination_file_name} using libtorrent...")

    with tqdm(
        total=selected_file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=" - Downloading: ",
        ascii=" █"
    ) as progress_bar:

        while True:
            status = torrent_handle.status()

            if status.errc and status.errc.value() != 0:
                raise RuntimeError(f"Torrent error: {status.errc.message()}")

            downloaded_bytes = min(
                status.total_wanted_done, selected_file_size)

            progress_bar.update(max(0, downloaded_bytes - progress_bar.n))

            download_speed = status.download_payload_rate
            remaining_bytes = (selected_file_size - downloaded_bytes)

            if download_speed > 0:
                eta_seconds = (remaining_bytes / download_speed)

                eta = tqdm.format_interval(eta_seconds)
            else:
                eta = "--:--"

            progress_bar.set_postfix_str(
                f"{download_speed / 1024 ** 2:.2f} MiB/s"
                f" | ETA {eta}"
                f" | peers {status.num_peers}"
            )

            if status.is_finished:
                progress_bar.update(selected_file_size - progress_bar.n)
                break

            time.sleep(1)

    if not os.path.isfile(destination_file_path):
        raise RuntimeError(
            "Torrent download finished but the file "
            f"was not found: {destination_file_path}"
        )

    print(f"File downloaded: {destination_file_path}")

    return destination_file_path


def downloadFileWithLibTorrent(torrent_file_path, tmp_file, new_file_name):
    torrent_info = getTorrentInfo(torrent_file_path)
    torrent_index = findTorrentFileIndex(torrent_info, new_file_name)

    return downloadTorrentFileByIndex(torrent_info, torrent_index, tmp_file)
