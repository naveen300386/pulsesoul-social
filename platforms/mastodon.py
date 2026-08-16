"""
Mastodon.

Free, no review. Create an application inside your own Mastodon account's
settings (Preferences -> Development) and copy the access token.

MASTODON_INSTANCE looks like https://mastodon.social. Write it without the
scheme and requests raises "Invalid URL '/api/v2/media': No scheme supplied",
which reads like a bug in this file rather than a typo in a secret -- so the
scheme is added here if it is missing instead.
"""
import time

import requests

from .base import Platform, TIMEOUT, clip, raise_for


class Mastodon(Platform):
    name = "mastodon"
    needs = ["MASTODON_INSTANCE", "MASTODON_TOKEN"]
    shape = "sq"
    link_style = "inline"
    voice = "english"
    limit = 480

    def post(self, text: str, image_stem: str, link: str) -> str:
        base = self.env("MASTODON_INSTANCE").rstrip("/")
        if not base.startswith(("http://", "https://")):
            base = f"https://{base}"
        auth = {"Authorization": f"Bearer {self.env('MASTODON_TOKEN')}"}
        payload = {"status": clip(text, self.limit), "visibility": "public"}

        img = self.image_path(image_stem)
        if img:
            with open(img, "rb") as fh:
                media = requests.post(
                    f"{base}/api/v2/media",
                    headers=auth,
                    data={"description": "PulseSoul app screen"},
                    files={"file": (img.name, fh, "image/jpeg")},
                    timeout=TIMEOUT,
                )
            raise_for(media, "mastodon media")
            media_id = media.json()["id"]
            # 202 means the server is still processing the upload
            if media.status_code == 202:
                for _ in range(10):
                    time.sleep(3)
                    check = requests.get(f"{base}/api/v1/media/{media_id}", headers=auth, timeout=TIMEOUT)
                    if check.status_code == 200:
                        break
            payload["media_ids[]"] = media_id

        resp = requests.post(f"{base}/api/v1/statuses", headers=auth, data=payload, timeout=TIMEOUT)
        raise_for(resp, "mastodon status")
        return resp.json().get("url", "mastodon post created")
