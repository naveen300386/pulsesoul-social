"""
Pinterest.

Worth knowing before you spend time here: on Trial access every Pin you
create is a sandbox object that ONLY YOU can see. Pinterest only becomes a
real traffic source after Standard access is approved, which needs a screen
recording of the integration working. So this is deliberately last in the
setup order.

The link goes in a dedicated field, so the description does not need a URL.
"""
import base64

import requests

from .base import Platform, TIMEOUT, clip, raise_for

API = "https://api.pinterest.com/v5"


class Pinterest(Platform):
    name = "pinterest"
    needs = ["PINTEREST_TOKEN", "PINTEREST_BOARD_ID"]
    shape = "pin"
    link_style = "field"
    voice = "english"
    limit = 480

    def post(self, text: str, image_stem: str, link: str) -> str:
        img = self.image_path(image_stem)
        if not img:
            raise RuntimeError("pinterest needs an image and this post has none")

        title = text.split("\n", 1)[0][:100]
        payload = {
            "board_id": self.env("PINTEREST_BOARD_ID"),
            "title": title,
            "description": clip(text, self.limit),
            "link": link,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/jpeg",
                "data": base64.b64encode(img.read_bytes()).decode("ascii"),
            },
        }

        resp = requests.post(
            f"{API}/pins",
            headers={"Authorization": f"Bearer {self.env('PINTEREST_TOKEN')}", "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
        raise_for(resp, "pinterest pin")
        return f"https://www.pinterest.com/pin/{resp.json().get('id')}"
