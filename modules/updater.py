import requests
import webbrowser

REPO_API = "https://api.github.com/repos/rojus-dev/bombaclat-radio/releases/latest"
REPO_RELEASES = "https://github.com/rojus-dev/bombaclat-radio/releases"

CURRENT_VERSION = "1.0.0"


def check_for_updates():
    try:
        response = requests.get(REPO_API, timeout=5)
        response.raise_for_status()

        latest = response.json()["tag_name"].lstrip("v")

        return {
            "current": CURRENT_VERSION,
            "latest": latest,
            "update_available": latest != CURRENT_VERSION
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def open_release_page():
    webbrowser.open(REPO_RELEASES)