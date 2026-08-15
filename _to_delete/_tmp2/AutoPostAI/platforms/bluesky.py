"""
Bluesky (AT Protocol).

Free, no app review, works in ten minutes. Uses an App Password, not your
real password -- you can revoke it any time without changing your login.

300 characters, and links only become clickable if you attach a "facet"
pointing at the byte range of the URL, which is what _link_facets does.
"""
import re
from datetime import datetime, timezone

import requests

from .base import Platform, TIMEOUT, clip, raise_for

HOST = "https://bsky.social"
URL_RE = re.compile(r"https?://[^\s\)\]]+")


class Bluesky(Platform):
    name = "bluesky"
    needs = ["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"]
    shape = "sq"
    link_style = "inline"
    voice = "english"
    limit = 290

    def _session(self) -> dict:
        resp = requests.post(
            f"{HOST}/xrpc/com.atproto.server.createSession",
            json={"identifier": self.env("BLUESKY_HANDLE"), "password": self.env("BLUESKY_APP_PASSWORD")},
            timeout=TIMEOUT,
        )
        raise_for(resp, "bluesky login")
        return resp.json()

    @staticmethod
    def _link_facets(text: str) -> list:
        facets = []
        for m in URL_RE.finditer(text):
            start = len(text[: m.start()].encode("utf-8"))
            end = start + len(m.group(0).encode("utf-8"))
            facets.append(
                {
                    "index": {"byteStart": start, "byteEnd": end},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group(0)}],
                }
            )
        return facets

    def post(self, text: str, image_stem: str, link: str) -> str:
        session = self._session()
        jwt = session["accessJwt"]
        did = session["did"]
        auth = {"Authorization": f"Bearer {jwt}"}
        body = clip(text, self.limit)

        record = {
            "$type": "app.bsky.feed.post",
            "text": body,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "langs": ["en"],
        }
        facets = self._link_facets(body)
        if facets:
            record["facets"] = facets

        img = self.image_path(image_stem)
        if img:
            blob = requests.post(
                f"{HOST}/xrpc/com.atproto.repo.uploadBlob",
                headers={**auth, "Content-Type": "image/jpeg"},
                data=img.read_bytes(),
                timeout=TIMEOUT,
            )
            raise_for(blob, "bluesky uploadBlob")
            record["embed"] = {
                "$type": "app.bsky.embed.images",
                "images": [{"alt": "PulseSoul app screen", "image": blob.json()["blob"]}],
            }

        resp = requests.post(
            f"{HOST}/xrpc/com.atproto.repo.createRecord",
            headers=auth,
            json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
            timeout=TIMEOUT,
        )
        raise_for(resp, "bluesky createRecord")
        rkey = resp.json()["uri"].rsplit("/", 1)[-1]
        return f"https://bsky.app/profile/{self.env('BLUESKY_HANDLE')}/post/{rkey}"
