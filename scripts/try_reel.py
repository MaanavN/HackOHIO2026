"""Run the reel download + frame sampling without Hermes (milestone 1).

    venv/bin/python scripts/try_reel.py https://www.instagram.com/reel/XXXXXXXX/
    venv/bin/python scripts/try_reel.py <url> --cookies-from-browser chrome

Output goes to ./data/reels/<id>/ (video, info.json, audio.wav, frames/).
Transcription and the AI analysis need Hermes, so they are skipped here.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apply.reel import analyze  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--cookies-from-browser", help="chrome, firefox, safari, ...")
    parser.add_argument("--cookies-file", help="Netscape cookies.txt")
    args = parser.parse_args()

    if args.cookies_from_browser:
        os.environ["APPLY_COOKIES_FROM_BROWSER"] = args.cookies_from_browser
    if args.cookies_file:
        os.environ["APPLY_COOKIES_FILE"] = args.cookies_file

    out = analyze.analyze(args.url)
    meta = out["metadata"]
    print(json.dumps(
        {
            "video": meta["video_path"],
            "uploader": meta["uploader_id"],
            "upload_date": meta["upload_date"],
            "duration": meta["duration"],
            "caption": meta["caption"],
            "comments": [c["text"] for c in meta["comments"][:10]],
            "frames": out["frames"],
            "notes": out["notes"],
        },
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
