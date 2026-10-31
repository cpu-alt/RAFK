"""Optional Discord webhook notifications, sent in the background."""
import json
import logging
import threading
import urllib.request

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()

    def send(self, message: str) -> None:
        if not self.webhook_url:
            return
        threading.Thread(target=self._post, args=(message,), daemon=True).start()

    def _post(self, message: str) -> None:
        body = json.dumps({"username": "RAFK", "content": message}).encode()
        req = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "RAFK"},
        )
        try:
            urllib.request.urlopen(req, timeout=10).close()
        except OSError as exc:
            log.warning("Notification Discord échouée : %s", exc)
