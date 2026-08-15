"""
Threads.

Same two-step container flow as Instagram, on its own host, with its own
token (a Threads user token, not the Facebook Page token).
Limit: 250 posts per 24h. 500 characters.
"""
import time

import requests

from .base import Platform, TIMEOUT, clip, raise_for

API = "https://graph.threads.net/v1.0"


class Threads(Platform):
    name = "threads"
    needs = ["THREADS_USER_ID", "THREADS_TOKEN"]
    shape = "sq"
    link_style = "inline"
    voice = "english"
    limit = 480

    def post(self, text: str, image_stem: str, link: str) -> str:
        user_id = self.env("THREADS_USER_ID")
        token = self.env("THREADS_TOKEN")
        body = clip(text, self.limit)
        url = self.image_url(image_stem)

        payload = {"text": body, "access_token": token}
        if url:
            payload["media_type"] = "IMAGE"
            payload["image_url"] = url
        else:
            payload["media_type"] = "TEXT"

        create = requests.post(f"{API}/{user_id}/threads", data=payload, timeout=TIMEOUT)
        raise_for(create, "threads container")
        container = create.json()["id"]

        # Meta's own docs ask for a pause before publishing a container.
        time.sleep(30 if url else 5)

        publish = requests.post(
            f"{API}/{user_id}/threads_publish",
            data={"creation_id": container, "access_token": token},
            timeout=TIMEOUT,
        )
        raise_for(publish, "threads publish")
        return f"threads post {publish.json().get('id')}"
