from .bluesky import Bluesky
from .facebook import Facebook
from .instagram import Instagram
from .linkedin import LinkedIn
from .mastodon import Mastodon
from .pinterest import Pinterest
from .telegram import Telegram
from .threads import Threads

# Order matters only for readability of the log.
ALL = [
    Facebook(),
    Instagram(),
    Threads(),
    Telegram(),
    Bluesky(),
    Mastodon(),
    LinkedIn(),
    Pinterest(),
]

BY_NAME = {p.name: p for p in ALL}
