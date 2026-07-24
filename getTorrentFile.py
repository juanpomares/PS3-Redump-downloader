import os

import re
from playwright.sync_api import Error as PlaywrightError, expect, sync_playwright


def openPlaywrightBrowser(playwright):
    browsers = [
        ("chrome", "Google Chrome"),
        ("msedge", "Microsoft Edge")
    ]

    for channel, browser_name in browsers:
        try:
            browser = playwright.chromium.launch(
                channel=channel,
                headless=True,
            )

            print(f"Using {browser_name} with Playwright.")
            return browser

        except PlaywrightError:
            print(f"{browser_name} not found. Trying next browser...")
            pass

    raise RuntimeError(
        "No compatible browser was found.\n"
        "Please install Microsoft Edge or Google Chrome."
    )


def getTorrentFile(baseRoute, file, file_path):
    link = baseRoute.replace('browse', 'rom/?name=.') + file + '.zip'
    torrent_file_path = os.path.join(file_path, "temp.torrent")
    if os.path.exists(torrent_file_path):
        print(
            f"Torrent file already exists at {torrent_file_path}. Skipping download.")
        return torrent_file_path

    print(f"Downloading torrent file...")

    with sync_playwright() as playwright:
        browser = openPlaywrightBrowser(playwright)

        try:
            context = browser.new_context(accept_downloads=True)

            page = context.new_page()
            page.goto(link, wait_until="domcontentloaded", timeout=60_000)

            download_link = page.locator("#download")

            expect(download_link).to_have_attribute(
                "href",
                re.compile(r"\.torrent(?:\?.*)?$"),
                timeout=60_000,
            )

            with page.expect_download(timeout=60_000) as download_info:
                download_link.click()

            download = download_info.value
            download.save_as(torrent_file_path)

        finally:
            browser.close()

    print(f"Torrent file downloaded: {torrent_file_path}")

    return torrent_file_path
