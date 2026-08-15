"""
Instagram (Business or Creator account linked to your Facebook Page).

Instagram will not accept uploaded bytes -- it fetches the image from a public
URL, which is why the rendered/ folder lives in a public GitHub repo and
IMAGE_BASE_URL points at raw.githubusercontent.com.

Two steps: create a container, then publish it.
Limit: 100 API posts per 24h. Links in captions are not clickable, so the
caption says "link in bio".
"""
import time

import requests

from .base import Platform, TIMEOUT, clip, raise_for

GRAPH = "https://graph.facebook.com/v23.0"


class Instagram(Platform):
    name = "instagram"
    needs = ["IG_USER_ID", "FB_PAGE_TOKEN", "IMAGE_BASE_URL"]
    shape = "p45"
    link_style = "bio"
    voice = "hinglish"
    limit = 2200

    def post(self, text: str, image_stem: str, link: str) -> str:
        ig_id = self.env("IG_USER_ID")
        token = self.env("FB_PAGE_TOKEN")
        url = self.image_url(image_stem)
        if not url:
            raise RuntimeError("instagram needs an image; set IMAGE_BASE_URL and check the post's image field")

        create = requests.post(
            f"{GRAPH}/{ig_id}/media",
            data={"image_url": url, "caption": clip(text, self.limit), "access_token": token},
            timeout=TIMEOUT,
        )
        raise_for(create, "instagram container")
        container = create.json()["id"]

        # Instagram needs a moment to pull the image before it will publish.
        for attempt in range(10):
            time.sleep(4)
            status = requests.get(
                f"{GRAPH}/{container}",
                params={"fields": "status_code,status", "access_token": token},
                timeout=TIMEOUT,
            )
            code = status.json().get("status_code") if status.ok else None
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError(f"instagram could not fetch the image: {status.text[:300]}")

        publish = requests.post(
            f"{GRAPH}/{ig_id}/media_publish",
            data={"creation_id": container, "access_token": token},
            timeout=TIMEOUT,
        )
        raise_for(publish, "instagram publish")
        return f"https://www.instagram.com/p/{publish.json().get('id')}"
