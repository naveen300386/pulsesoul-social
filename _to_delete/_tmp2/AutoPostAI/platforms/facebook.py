"""
Facebook Page.

Posts the image straight from disk (no public URL needed).
Token: a long-lived PAGE access token with pages_manage_posts.
Meta rate-limits Pages on a rolling formula rather than a flat daily count;
two posts a day is nowhere near it.
"""
import requests

from .base import Platform, TIMEOUT, clip, raise_for

GRAPH = "https://graph.facebook.com/v23.0"


class Facebook(Platform):
    name = "facebook"
    needs = ["FB_PAGE_ID", "FB_PAGE_TOKEN"]
    shape = "p45"
    link_style = "inline"
    voice = "hinglish"
    limit = 5000

    def post(self, text: str, image_stem: str, link: str) -> str:
        page_id = self.env("FB_PAGE_ID")
        token = self.env("FB_PAGE_TOKEN")
        body = clip(text, self.limit)
        img = self.image_path(image_stem)

        if img:
            with open(img, "rb") as fh:
                resp = requests.post(
                    f"{GRAPH}/{page_id}/photos",
                    data={"caption": body, "access_token": token},
                    files={"source": (img.name, fh, "image/jpeg")},
                    timeout=TIMEOUT,
                )
            raise_for(resp, "facebook photo")
            post_id = resp.json().get("post_id") or resp.json().get("id")
        else:
            resp = requests.post(
                f"{GRAPH}/{page_id}/feed",
                data={"message": body, "link": link, "access_token": token},
                timeout=TIMEOUT,
            )
            raise_for(resp, "facebook feed")
            post_id = resp.json().get("id")

        return f"https://facebook.com/{post_id}"
