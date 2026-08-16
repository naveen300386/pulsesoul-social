"""
Pinterest.

Worth knowing before you spend time here: on Trial access Pinterest will NOT
let you create Pins on the production host at all. It answers

    HTTP 403, code 29: "Apps with Trial access may not create Pins in
    production https://api.pinterest.com - use API Sandbox
    https://api-sandbox.pinterest.com instead."

The sandbox is a SEPARATE HOST with its own, initially EMPTY set of boards --
your real PulseSoul board does not exist over there. Pins made there are
visible only to you. So while access is Trial, set PINTEREST_SANDBOX=1 and
the runner talks to that host; when Standard access is approved, clear it and
the same code starts creating real Pins.

Two consequences, both handled below rather than left as traps:

  * Sandbox board ids are different, so sandbox mode requires its own
    PINTEREST_SANDBOX_BOARD_ID. If it is missing the platform is SKIPPED, not
    attempted -- a failed attempt would burn a queue slot and a schedule slot
    on a request that cannot succeed.
  * A sandbox pin is not a published post. Its ref is prefixed SANDBOX so the
    log, --status and history all say so, and so history.platforms_seen() does
    not count it as a working account. Otherwise the run goes green forever
    and nothing tells you nobody can see any of it.

The link goes in a dedicated field, so the description does not need a URL.
"""
import base64

import requests

from .base import Platform, TIMEOUT, clip, raise_for

API = "https://api.pinterest.com/v5"
SANDBOX_API = "https://api-sandbox.pinterest.com/v5"

TRUTHY = {"1", "true", "yes", "on"}
FALSY = {"0", "false", "no", "off"}


class Pinterest(Platform):
    name = "pinterest"
    needs = ["PINTEREST_TOKEN", "PINTEREST_BOARD_ID"]
    shape = "pin"
    link_style = "field"
    voice = "english"
    limit = 480

    def sandbox(self) -> bool:
        """A value we do not recognise must NOT quietly mean 'production' --
        that is the one branch already known to fail with 403."""
        raw = self.env("PINTEREST_SANDBOX").lower()
        if not raw or raw in FALSY:
            return False
        if raw in TRUTHY:
            return True
        raise RuntimeError(
            f"PINTEREST_SANDBOX is set to '{raw}', which means nothing. "
            f"Use 1 while your Pinterest app is on Trial access, or clear the secret entirely."
        )

    def base_url(self) -> str:
        """Trial access can only create Pins on the sandbox host."""
        return SANDBOX_API if self.sandbox() else API

    def board_id(self) -> str:
        """Sandbox boards are a separate set with their own ids. Never fall
        back to the production id here: that sends a real board id to the
        sandbox host, which 404s on every single run."""
        return self.env("PINTEREST_SANDBOX_BOARD_ID") if self.sandbox() else self.env("PINTEREST_BOARD_ID")

    def missing(self) -> list[str]:
        """Sandbox mode swaps which board id is required, so a half-set-up
        sandbox reads as 'not connected yet' and is skipped, instead of failing
        after the run has already recorded the post as spent."""
        try:
            sandbox = self.sandbox()
        except RuntimeError as exc:
            return [str(exc)]
        gaps = super().missing()
        if sandbox and not self.env("PINTEREST_SANDBOX_BOARD_ID"):
            gaps.append("PINTEREST_SANDBOX_BOARD_ID (sandbox boards have their own ids)")
        return gaps

    def available(self) -> bool:
        return not self.missing()

    def note(self) -> str:
        """Shown by --status, so 'ready' never overstates what a run will do."""
        try:
            return "  SANDBOX - pins are private, nobody else can see them" if self.sandbox() else ""
        except RuntimeError:
            return ""

    def post(self, text: str, image_stem: str, link: str) -> str:
        img = self.image_path(image_stem)
        if not img:
            raise RuntimeError("pinterest needs an image and this post has none")

        title = text.split("\n", 1)[0][:100]
        payload = {
            "board_id": self.board_id(),
            "title": title,
            "description": clip(text, self.limit),
            "link": link,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/jpeg",
                "data": base64.b64encode(img.read_bytes()).decode("ascii"),
            },
        }

        base = self.base_url()
        resp = requests.post(
            f"{base}/pins",
            headers={"Authorization": f"Bearer {self.env('PINTEREST_TOKEN')}", "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
        raise_for(resp, "pinterest pin")
        pin_id = resp.json().get("id")
        if base == SANDBOX_API:
            # NOT a published post. The SANDBOX prefix is load-bearing:
            # history.platforms_seen() uses it to keep this out of the set of
            # accounts that are genuinely live.
            return f"SANDBOX pin {pin_id} - private, not published (Trial access)"
        return f"https://www.pinterest.com/pin/{pin_id}"
