import os
import libtorrent as lt


def findTorrentFileIndex(torrent_file_path, torrent_file_to_download):
    torrent_size = os.path.getsize(torrent_file_path)
    torrent_limits = {"max_buffer_size": torrent_size + 1024 * 1024}

    torrent_info = lt.torrent_info(torrent_file_path, torrent_limits)
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
            f"'{torrent_file_to_download}' was not found "
            f"inside '{torrent_file_path}'."
        )

    if len(matches) > 1:
        matching_paths = "\n".join(
            f" - {match['path']}" for match in matches
        )

        raise RuntimeError(
            f"Multiple files named "
            f"'{torrent_file_to_download}' were found:\n"
            f"{matching_paths}"
        )

    match = matches[0]
    print(f"Torrent file found: {match['path']} (index: {match['index']})")

    return match["index"]


def downloadFileWithLibTorrent(torrent_file_path, tmp_file, new_file_name):
    print(f"Downloading {tmp_file} using libtorrent...")
    torrentIndex = findTorrentFileIndex(torrent_file_path, tmp_file)

    # TODO Donwload file with torrentIndex
