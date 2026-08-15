"""
LinkedIn, in three modes.

  Company Page via feed (LINKEDIN_FEED=1)  -- the runner writes the post into
                                              content/feed.xml and Zapier, an
                                              approved LinkedIn partner, reads
                                              the feed and posts it to the
                                              Page. No entity required. THIS IS
                                              THE DEFAULT SETUP.
  Company Page via API  (LINKEDIN_ORG_ID)  -- needs the Community Management
                                              API, which LinkedIn grants only
                                              to registered legal organizations.
  Your own profile  (LINKEDIN_PERSON_ID)   -- needs the "Share on LinkedIn"
                                              product, self-serve and instant,
                                              but posts under your name, not
                                              the Page's.

Precedence is ORG_ID, then FEED, then PERSON_ID. With none of them set,
LinkedIn is skipped and everything else carries on.

Why the feed exists at all: posting as a person was not what was wanted -- the
Page is the brand. Rather than wait for a company registration, the runner
hands the post to a partner that already has the permission LinkedIn will not
give a solo developer.

The two modes are not cosmetic variations: they are different APIs. The Page
uses the versioned /rest/posts endpoint with the images upload service; the
profile uses the older /v2/ugcPosts endpoint with the assets service. Do not
try to merge them.

TOKEN EXPIRY -- the one thing that will bite you. A LinkedIn access token
lasts 60 days, and refresh tokens are only issued to approved Marketing
Developer Platform partners, which a self-serve app is not. So roughly every
two months you have to generate a new token by hand and update the secret.
The runner tells you when LinkedIn starts failing, but a calendar reminder at
55 days is better than finding out from a silent account.
"""
import requests

from core import feed

from .base import Platform, TIMEOUT, clip, raise_for

API = "https://api.linkedin.com/rest"
V2 = "https://api.linkedin.com/v2"
# LinkedIn sunsets version headers about a year after release and rejects
# expired ones with HTTP 426 NONEXISTENT_VERSION. Bump this yearly.
VERSION = "202607"


class LinkedIn(Platform):
    name = "linkedin"
    needs = ["LINKEDIN_TOKEN"]
    shape = "sq"
    link_style = "inline"
    voice = "english"
    limit = 2800

    # --- which mode ---------------------------------------------------------
    def _org(self) -> str:
        return self.env("LINKEDIN_ORG_ID")

    def _person(self) -> str:
        return self.env("LINKEDIN_PERSON_ID")

    def _feed_mode(self) -> bool:
        return self.env("LINKEDIN_FEED").lower() in ("1", "true", "yes", "on")

    def available(self) -> bool:
        if self._feed_mode():
            return True                      # writing a file needs no token
        return bool(self.env("LINKEDIN_TOKEN")) and bool(self._org() or self._person())

    def missing(self) -> list[str]:
        if self._feed_mode():
            return []
        gaps = [k for k in self.needs if not self.env(k)]
        if not (self._org() or self._person()):
            gaps.append("LINKEDIN_FEED=1, or LINKEDIN_ORG_ID / LINKEDIN_PERSON_ID")
        return gaps

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.env('LINKEDIN_TOKEN')}",
            "LinkedIn-Version": VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    # --- Company Page: /rest/posts ------------------------------------------
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

    def _post_as_page(self, text: str, image_stem: str) -> str:
        owner = f"urn:li:organization:{self._org()}"
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

    # --- Your profile: /v2/ugcPosts -----------------------------------------
    def _v2_headers(self) -> dict:
        """ugcPosts predates the versioned API and rejects the version header."""
        return {
            "Authorization": f"Bearer {self.env('LINKEDIN_TOKEN')}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _upload_asset(self, owner: str, path) -> str:
        register = requests.post(
            f"{V2}/assets?action=registerUpload",
            headers={**self._v2_headers(), "Content-Type": "application/json"},
            json={"registerUploadRequest": {
                "owner": owner,
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }],
            }},
            timeout=TIMEOUT,
        )
        raise_for(register, "linkedin registerUpload")
        value = register.json()["value"]
        url = value["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]

        put = requests.put(
            url,
            headers={"Authorization": f"Bearer {self.env('LINKEDIN_TOKEN')}"},
            data=path.read_bytes(),
            timeout=TIMEOUT,
        )
        raise_for(put, "linkedin asset upload")
        return value["asset"]

    def _post_as_person(self, text: str, image_stem: str) -> str:
        owner = f"urn:li:person:{self._person()}"
        body = clip(text, self.limit)
        share = {"shareCommentary": {"text": body}, "shareMediaCategory": "NONE"}

        img = self.image_path(image_stem)
        if img:
            share["shareMediaCategory"] = "IMAGE"
            share["media"] = [{
                "status": "READY",
                "media": self._upload_asset(owner, img),
                "title": {"text": "PulseSoul"},
            }]

        resp = requests.post(
            f"{V2}/ugcPosts",
            headers={**self._v2_headers(), "Content-Type": "application/json"},
            json={
                "author": owner,
                "lifecycleState": "PUBLISHED",
                "specificContent": {"com.linkedin.ugc.ShareContent": share},
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            },
            timeout=TIMEOUT,
        )
        raise_for(resp, "linkedin post")
        post_urn = resp.headers.get("x-restli-id") or resp.json().get("id", "")
        return f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else "linkedin post created"

    # --- the Page, by way of a feed a partner reads ------------------------
    def _post_to_feed(self, text: str, image_stem: str) -> str:
        # The image has to be a public URL, not bytes: the reader fetches it
        # itself, exactly as Instagram does.
        path = feed.append(image_stem or "post", clip(text, self.limit), self.image_url(image_stem))
        return f"queued in {path.name} for the PulseSoul Page"

    def post(self, text: str, image_stem: str, link: str) -> str:
        if self._org():
            return self._post_as_page(text, image_stem)
        if self._feed_mode():
            return self._post_to_feed(text, image_stem)
        return self._post_as_person(text, image_stem)
