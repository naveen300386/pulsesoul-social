"""
Telegram channel.

The easiest one on the list: make a bot with @BotFather, add it to your
channel as an admin, done. No review, no expiry, no rate ceiling worth
worrying about. Caption limit is 1024 characters.
"""
import requests

from .base import Platform, TIMEOUT, clip, raise_for


class Telegram(Platform):
    name = "telegram"
    needs = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    shape = "sq"
    link_style = "inline"
    voice = "english"
    limit = 1000

    def post(self, text: str, image_stem: str, link: str) -> str:
        token = self.env("TELEGRAM_BOT_TOKEN")
        chat = self.env("TELEGRAM_CHAT_ID")
        body = clip(text, self.limit)
        img = self.image_path(image_stem)

        if img:
            with open(img, "rb") as fh:
                resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendPhoto",
                    data={"chat_id": chat, "caption": body},
                    files={"photo": (img.name, fh, "image/jpeg")},
                    timeout=TIMEOUT,
                )
            raise_for(resp, "telegram sendPhoto")
        else:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": body},
                timeout=TIMEOUT,
            )
            raise_for(resp, "telegram sendMessage")

        msg_id = resp.json().get("result", {}).get("message_id")
        return f"telegram message {msg_id}"
