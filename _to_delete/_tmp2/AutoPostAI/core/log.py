import sys
import time

_START = time.time()


def _emit(icon: str, msg: str) -> None:
    print(f"{icon} {msg}", flush=True)


def info(msg: str) -> None:
    _emit("  ", msg)


def step(msg: str) -> None:
    _emit("->", msg)


def ok(msg: str) -> None:
    _emit("OK", msg)


def skip(msg: str) -> None:
    _emit("--", msg)


def fail(msg: str) -> None:
    _emit("!!", msg)
    sys.stdout.flush()


def header(msg: str) -> None:
    print(f"\n{'=' * 62}\n{msg}\n{'=' * 62}", flush=True)


def elapsed() -> str:
    return f"{time.time() - _START:.1f}s"
