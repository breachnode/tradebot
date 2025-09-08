import requests
from .settings import SETTINGS


def send(message: str):
    if not SETTINGS.discord_webhook:
        return
    try:
        requests.post(SETTINGS.discord_webhook, json={"content": message}, timeout=5)
    except Exception:
        pass

