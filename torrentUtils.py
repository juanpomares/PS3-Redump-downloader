import os
import time

import libtorrent as lt
from tqdm import tqdm


_torrent_session = None

TORRENT_FILE_DONT_DOWNLOAD = 0
TORRENT_FILE_TOP_PRIORITY = 7


def getTorrentSession():
    global _torrent_session

    if _torrent_session is None:
        _torrent_session = lt.session({
            "listen_interfaces": "0.0.0.0:0"
        })

    return _torrent_session


def getTorrentInfo(torrent_file_path):
    torrent_size = os.path.getsize(torrent_file_path)

    torrent_limits = {"max_buffer_size": torrent_size + 1024 * 1024}

    return lt.torrent_info(torrent_file_path, torrent_limits)


def findFileIndexInTorrent(torrent_info, file_name_to_download):
    torrent_files = torrent_info.files()

    target_file_name = os.path.basename(file_name_to_download).casefold()

    matches = []

    for file_index in range(torrent_files.num_files()):
        internal_file_path = torrent_files.file_path(file_index)
        internal_file_name = os.path.basename(internal_file_path).casefold()

        if internal_file_name == target_file_name:
            matches.append({"index": file_index, "path": internal_file_path})

    if not matches:
        raise FileNotFoundError(
            f"'{file_name_to_download}' was not found inside the torrent."
        )

    if len(matches) > 1:
        matching_paths = "\n".join(f" - {match['path']}" for match in matches)

        raise RuntimeError(
            f"Multiple files named "
            f"'{file_name_to_download}' were found:\n"
            f"{matching_paths}"
        )

    match = matches[0]

    print(f"File found in torrent: {match['path']} (index: {match['index']})")

    return match["index"]


def removeTorrentAndPartFile(torrent_handle):
    torrent_session = getTorrentSession()
    torrent_session.remove_torrent(torrent_handle, lt.session.delete_partfile)

    timeout_at = time.monotonic() + 10

    while torrent_handle.is_valid():
        if time.monotonic() >= timeout_at:
            break

        time.sleep(0.05)


def downloadTorrentFileByIndex(torrent_info, torrent_index, destination_file_path):

    destination_file_path = os.path.abspath(destination_file_path)

    destination_folder = os.path.dirname(destination_file_path)
    destination_file_name = os.path.basename(destination_file_path)

    if os.path.isfile(destination_file_path):
        print(f"File already exists: {destination_file_path}")

        return destination_file_path

    torrent_files = torrent_info.files()

    selected_file_size = torrent_files.file_size(torrent_index)

    torrent_info.rename_file(torrent_index, destination_file_name)

    file_priorities = [TORRENT_FILE_DONT_DOWNLOAD] * torrent_files.num_files()

    file_priorities[torrent_index] = TORRENT_FILE_TOP_PRIORITY

    torrent_params = lt.add_torrent_params()
    torrent_params.ti = torrent_info
    torrent_params.save_path = destination_folder
    torrent_params.file_priorities = file_priorities

    torrent_session = getTorrentSession()
    torrent_handle = torrent_session.add_torrent(torrent_params)

    try:
        print(f"Downloading {destination_file_name} using libtorrent...")

        with tqdm(
            total=selected_file_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=" - Downloading: ",
            ascii=" █",
            bar_format=(
                "{l_bar}{bar}| {n_fmt}/{total_fmt} "
                "[elapsed {elapsed}{postfix}]"
            )
        ) as progress_bar:

            while True:
                status = torrent_handle.status()

                if status.errc and status.errc.value() != 0:
                    raise RuntimeError(
                        f"Torrent error: {status.errc.message()}")

                total_wanted = (
                    status.total_wanted
                    if status.total_wanted > 0
                    else selected_file_size
                )

                downloaded_bytes = min(status.total_wanted_done, total_wanted)

                if progress_bar.total != total_wanted:
                    progress_bar.total = total_wanted
                    progress_bar.refresh()

                progress_bar.update(max(0, downloaded_bytes - progress_bar.n))

                download_speed = status.download_payload_rate
                upload_speed = status.upload_payload_rate

                remaining_bytes = max(0, total_wanted - downloaded_bytes)

                minimum_speed_for_eta = 50 * 1024  # 50 KiB/s

                if download_speed >= minimum_speed_for_eta and remaining_bytes > 0:
                    eta_seconds = remaining_bytes / download_speed
                    eta = tqdm.format_interval(eta_seconds)
                elif remaining_bytes == 0:
                    eta = "00:00"
                else:
                    eta = "--:--"

                progress_bar.set_postfix_str(
                    f"↓ {download_speed / 1024 ** 2:.2f} MiB/s"
                    f" | ↑ {upload_speed / 1024 ** 2:.2f} MiB/s"
                    f" | ETA {eta}"
                    f" | peers {status.num_peers}"
                )

                download_finished = (
                    status.is_finished
                    or (
                        status.total_wanted > 0
                        and status.total_wanted_done
                        >= status.total_wanted
                    )
                )

                if download_finished:
                    progress_bar.update(max(0, total_wanted - progress_bar.n))
                    break

                time.sleep(1)

    finally:
        if torrent_handle is not None and torrent_handle.is_valid():
            removeTorrentAndPartFile(torrent_handle)

    if not os.path.isfile(destination_file_path):
        raise RuntimeError(
            "Torrent download finished but the file "
            f"was not found: {destination_file_path}"
        )

    print(f"File downloaded: {destination_file_path}")

    return destination_file_path


def downloadFileWithLibTorrent(torrent_file_path, file_name_to_download, destination_file_path):

    torrent_info = getTorrentInfo(torrent_file_path)

    torrent_index = findFileIndexInTorrent(torrent_info, file_name_to_download)

    return downloadTorrentFileByIndex(torrent_info, torrent_index, destination_file_path)
