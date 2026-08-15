"""
Shared shape for every platform.

Rules that matter:
  * A platform with missing tokens is SKIPPED, never an error. That is how you
    switch platforms on one at a time -- add the secret, it starts posting.
  * A platform that fails NEVER stops the others.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDERED = ROOT / "rendered"

TIMEOUT = 60


class Platform:
    name = "base"
    # environment variables that must all be present for this platform to run
    needs: list[str] = []
    # "sq" 1080x1080 | "p45" 1080x1350 | "pin" 1000x1500
    shape = "sq"
    # "inline"  -> put the URL in the post text
    # "bio"     -> platform does not make links clickable, point at the profile
    # "field"   -> the link goes in a dedicated API field, not the text
    link_style = "inline"
    # which copy to use: "hinglish" or "english"
    voice = "english"
    # hard character ceiling for the post body, None = no practical limit
    limit: int | None = None

    def available(self) -> bool:
        return all(os.environ.get(k, "").strip() for k in self.needs)

    def missing(self) -> list[str]:
        return [k for k in self.needs if not os.environ.get(k, "").strip()]

    def env(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default).strip()

    def image_path(self, stem: str) -> Path | None:
        if not stem:
            return None
        p = RENDERED / f"{stem}__{self.shape}.jpg"
        return p if p.exists() else None

    def image_url(self, stem: str) -> str | None:
        """Public URL for platforms that fetch the image themselves."""
        base = os.environ.get("IMAGE_BASE_URL", "").strip().rstrip("/")
        if not base or not stem:
            return None
        return f"{base}/{stem}__{self.shape}.jpg"

    def post(self, text: str, image_stem: str, link: str) -> str:
        raise NotImplementedError


def clip(text: str, limit: int | None) -> str:
    if limit is None or len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut[-40:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip() + "…"


def raise_for(resp, what: str) -> None:
    if resp.status_code >= 400:
        body = resp.text[:400].replace("\n", " ")
        raise RuntimeError(f"{what} -> HTTP {resp.status_code}: {body}")
