"""Download an Instagram reel and its metadata with yt-dlp."""

import re
from pathlib import Path

REEL_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/(?:[\w.]+/)?(?:reel|reels|p|tv)/([\w-]+)[^\s]*", re.I)

MAX_COMMENTS = 30


class DownloadError(RuntimeError):
    pass


def find_reel_urls(text: str) -> list[str]:
    return [m.group(0) for m in REEL_URL_RE.finditer(text or "")]


def reel_id(url: str) -> str | None:
    match = REEL_URL_RE.search(url or "")
    return match.group(1) if match else None


def download(url: str, out_dir: Path, cookies_file: str | None = None, cookies_browser: str | None = None) -> dict:
    """Download the reel into out_dir/<id>/ and return its metadata.

    Instagram usually needs a logged-in session: pass a Netscape cookies.txt
    (cookies_file) or a browser name to read cookies from (cookies_browser).
    Use a secondary Instagram account for this, never your main one.
    """
    try:
        import yt_dlp
    except ImportError as e:
        raise DownloadError("yt-dlp is not installed (pip install yt-dlp)") from e

    rid = reel_id(url)
    if not rid:
        raise DownloadError(f"not an Instagram reel/post URL: {url}")
    target = out_dir / rid
    target.mkdir(parents=True, exist_ok=True)

    opts = {
        "outtmpl": str(target / "video.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "writeinfojson": True,
        "getcomments": True,
        "extractor_args": {"instagram": {"max_comments": [str(MAX_COMMENTS)]}},
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if cookies_file:
        opts["cookiefile"] = str(Path(cookies_file).expanduser())
    elif cookies_browser:
        opts["cookiesfrombrowser"] = (cookies_browser,)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as e:
        message = str(e)
        if "login" in message.lower() or "rate" in message.lower() or "cookies" in message.lower():
            message += (
                " — Instagram wants a logged-in session. Set the plugin's cookies_file or"
                " cookies_from_browser setting (use a secondary Instagram account)."
            )
        raise DownloadError(message) from e

    comments = [
        {"author": c.get("author"), "text": c.get("text"), "likes": c.get("like_count")}
        for c in (info.get("comments") or [])[:MAX_COMMENTS]
        if c.get("text")
    ]
    uploader_id = info.get("uploader_id") or info.get("channel")
    return {
        "id": rid,
        "url": url,
        "dir": str(target),
        "video_path": str(video_path),
        "caption": info.get("description") or "",
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "uploader_id": uploader_id,
        "uploader_profile_url": f"https://www.instagram.com/{uploader_id}/" if uploader_id else None,
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "comments": comments,
    }
