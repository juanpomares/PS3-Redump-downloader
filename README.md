# PS3 Redump Downloader

PS3 Redump Downloader is a Python console application to help download and process PS3 disc image files from a configured source ( [Minerva Archive](https://minerva-archive.org/) ), and decrypt them using **PS3Dec**.

This project is not affiliated with Minerva Archive.

## Project status

- **In development** while the project is adapted to use **Minerva Archive** as the upstream source.
- Minerva Archive uses torrents instead of direct downloads, but the general setup and usage flow are expected to remain similar.

## Intended use / legal

This tool is intended for **lawful personal use**, such as working with **disc dumps you made yourself** or content you otherwise have the rights to use.  
You are responsible for complying with applicable laws in your jurisdiction.

---

## Installation Guide

### Windows

#### Easy Installation

1. Go to the **[Releases page](https://github.com/juanpomares/PS3-Redump-downloader/releases)** and download the latest `.zip`.
2. Extract the downloaded zip file and run **PS3RedumpDownloader.exe**.

#### Manual Setup

1. Get **PS3Dec** (used to decrypt PS3 ISO files). You can either:
   - Download a Windows build from **ConsoleMods**: https://consolemods.org/wiki/File:PS3DecR5.7z
   - Or compile it yourself from **al3xtjames/PS3Dec**: https://github.com/al3xtjames/PS3Dec
2. Download **PS3RedumpDownloader.exe** from the **[Releases page](https://github.com/juanpomares/PS3-Redump-downloader/releases)**.
3. Place `PS3Dec.exe` next to `PS3RedumpDownloader.exe` (same folder) and run **PS3RedumpDownloader.exe**.

### Other Operating Systems

1. Download and compile **PS3Dec**: https://github.com/al3xtjames/PS3Dec
2. Clone this repository.
3. Install dependencies:
   - `pip install requests beautifulsoup4 tqdm`
4. Run:
   - `python main.py`

---

## How to Use

On first launch, the tool connects to the configured source and downloads the available title list.  
This list is cached in a file named **`listPS3Titles.json`**.

![First Time Open](./doc/firstTimeOpen.png)

Subsequent launches will load the cached list:

![Next Time Open](./doc/notFirstTimeOpen.png)

The app will display: `Find PS3 title to download`.  
Type a full title or a substring to filter the list.

![Filtering Game List](./doc/filterList.png)

Each entry is indexed for selection. To download an item, type its index and press Enter.  
The tool will download, extract, and then decrypt (via PS3Dec) when applicable.

![Downloading Game](./doc/downloading.gif)

When finished, you should see:

- `Title_decrypted.iso`
- Optional original files you may delete: `Title.iso` and `Title.dkey`

![Downloaded Game](./doc/downloaded.png)

---

## Contributions

Contributions are welcome, with focus on bugfixes and maintenance.
If you find a bug or want to suggest an improvement, please open an issue or submit a pull request.

---

## Credits

- **al3xtjames** for creating **PS3Dec**: https://github.com/al3xtjames/PS3Dec

## Author

Developed by **juanpomares**: https://github.com/juanpomares/

## License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute this project, provided you include attribution to the original author.
