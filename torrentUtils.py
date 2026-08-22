import os
import time

import libtorrent as lt
from tqdm import tqdm

METADATA_TIMEOUT_SECONDS = 300
_torrent_session = None


def getTorrentSession():
    global _torrent_session

    if _torrent_session is None:
        _torrent_session = lt.session({
            "listen_interfaces": "0.0.0.0:0"
        })

    return _torrent_session


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


def waitForTorrentMetadata(torrent_handle):
    print("Downloading torrent metadata...")

    timeout_at = time.monotonic() + METADATA_TIMEOUT_SECONDS

    while True:
        status = torrent_handle.status()

        if status.errc and status.errc.value() != 0:
            raise RuntimeError(
                f"Torrent error: {status.errc.message()}"
            )

        if status.has_metadata:
            torrent_info = torrent_handle.torrent_file()

            if torrent_info is None:
                raise RuntimeError(
                    "Torrent metadata was received but "
                    "torrent information is not available."
                )

            print("Torrent metadata downloaded.")
            return torrent_info

        if time.monotonic() >= timeout_at:
            raise TimeoutError(
                "Timeout waiting for torrent metadata."
            )

        time.sleep(0.25)


def removeTorrentAndPartFile(torrent_handle):
    torrent_session = getTorrentSession()
    torrent_session.remove_torrent(torrent_handle, lt.session.delete_partfile)

    timeout_at = time.monotonic() + 10

    while torrent_handle.is_valid():
        if time.monotonic() >= timeout_at:
            break

        time.sleep(0.05)


def downloadMagnetFileWithLibTorrent(magnet_link, file_name_to_download, destination_file_path):
    destination_file_path = os.path.abspath(destination_file_path)

    destination_folder = os.path.dirname(destination_file_path)
    destination_file_name = os.path.basename(destination_file_path)

    if os.path.isfile(destination_file_path):
        print(f"File already exists: {destination_file_path}")

        return destination_file_path

    torrent_session = getTorrentSession()

    torrent_params = lt.parse_magnet_uri(magnet_link)
    torrent_params.save_path = destination_folder

    torrent_params.flags |= lt.torrent_flags.default_dont_download

    torrent_handle = torrent_session.add_torrent(torrent_params)

    try:
        torrent_info = waitForTorrentMetadata(torrent_handle)

        torrent_index = findFileIndexInTorrent(
            torrent_info, file_name_to_download)

        torrent_files = torrent_info.files()

        selected_file_size = torrent_files.file_size(torrent_index)
        torrent_handle.rename_file(torrent_index, destination_file_name)

        torrent_handle.file_priority(torrent_index, 7)

        priority_timeout_at = time.monotonic() + 10

        while torrent_handle.file_priority(torrent_index) == 0:
            status = torrent_handle.status()

            if status.errc and status.errc.value() != 0:
                raise RuntimeError(f"Torrent error: {status.errc.message()}")

            if time.monotonic() >= priority_timeout_at:
                raise TimeoutError("Timeout applying torrent file priority.")

            time.sleep(0.05)

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
        if torrent_handle.is_valid():
            removeTorrentAndPartFile(torrent_handle)

    if not os.path.isfile(destination_file_path):
        raise RuntimeError(
            "Torrent download finished but the file "
            f"was not found: {destination_file_path}"
        )

    print(f"File downloaded: {destination_file_path}")

    return destination_file_path
