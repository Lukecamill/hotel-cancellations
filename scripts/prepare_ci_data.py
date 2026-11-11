"""Fetch the attributed source CSV, enforcing the existing frozen identity."""

import hashlib
import shutil
from pathlib import Path

from hotel_cancel.config import load_config
from hotel_cancel.data import get_raw
import json


def main():
    config = load_config()
    root = Path(__file__).resolve().parents[1]
    expected = json.loads((root / "config/evaluation-lock.json").read_text())["identity"]["raw_sha256"]
    source = get_raw("hotel_bookings.csv", config)
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("Downloaded dataset differs from frozen source; refusing CI input")
    destination = config["raw_dir"] / "hotel_bookings.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    print(f"Verified source dataset SHA-256: {actual}")


if __name__ == "__main__":
    main()
