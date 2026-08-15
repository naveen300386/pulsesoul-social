"""
LinkedIn company page.

The slowest one to switch on: posting to a Page needs the Community
Management API, which is a restricted product -- expect 1-2 weeks of review.
Everything else here works while you wait.

LINKEDIN_ORG_ID is just the numeric id from your page's admin URL.
"""
import requests

from .base import Platform, TIMEOUT, clip, raise_for

API = "https://api.linkedin.com/rest"
# LinkedIn sunsets version headers about a year after release and rejects
# expired ones with HTTP 426 NONEXISTENT_VERSION. Bump this yearly.
VERSION = "202607"


class LinkedIn(Platform):
    name = "linkedin"
    needs = ["LINKEDIN_TOKEN", "LINKEDIN_ORG_ID"]
    shape = "sq"
    link_style = "inline"
    voice = "english"
    limit = 2800

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.env('LINKEDIN_TOKEN')}",
            "LinkedIn-Version": VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _upload_image(self, owner: str, path) -> str:
        init = requests.post(
            f"{API}/images?action=initializeUpload",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"initializeUploadRequest": {"owner": owner}},
            timeout=TIMEOUT,
        )
        raise_for(init, "linkedin initializeUpload")
        value = init.json()["value"]

        put = requests.put(
            value["uploadUrl"],
            headers={"Authorization": f"Bearer {self.env('LINKEDIN_TOKEN')}"},
            data=path.read_bytes(),
            timeout=TIMEOUT,
        )
        raise_for(put, "linkedin image upload")
        return value["image"]

    def post(self, text: str, image_stem: str, link: str) -> str:
        owner = f"urn:li:organization:{self.env('LINKEDIN_ORG_ID')}"
        payload = {
            "author": owner,
            "commentary": clip(text, self.limit),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        img = self.image_path(image_stem)
        if img:
            payload["content"] = {"media": {"id": self._upload_image(owner, img), "title": "PulseSoul"}}

        resp = requests.post(
            f"{API}/posts",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
        raise_for(resp, "linkedin post")
        post_urn = resp.headers.get("x-restli-id", "")
        return f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else "linkedin post created"
