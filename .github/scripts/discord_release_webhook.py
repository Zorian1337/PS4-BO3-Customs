#!/usr/bin/env python3
"""Post published GitHub release notes and asset links to the BO3 Customs Discord."""
import argparse
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

REPOSITORY = "Zorian1337/PS4-BO3-Customs"
USERNAME = "BO3 Customs Releases"
AVATAR_URL = "https://github.com/Zorian1337.png?size=128"
EMBED_COLOR = 16744448  # Orange, matching the previous release notice.


def markdown_label(value):
    value = str(value).replace("\\", "\\\\")
    for character in ("[", "]", "(", ")", chr(96)):
        value = value.replace(character, "\\" + character)
    return value


def checked_github_url(value, prefix):
    parts = urlsplit(str(value or ""))
    if parts.scheme != "https" or parts.hostname != "github.com" or not parts.path.startswith(prefix):
        return ""
    return value


def make_payload(release):
    if not isinstance(release, dict):
        raise ValueError("Release event does not contain a release object")
    tag = str(release.get("tag_name") or "").strip()
    if not tag or len(tag) > 128 or not re.fullmatch(r"[A-Za-z0-9._/+~-]+", tag):
        raise ValueError("Release tag is missing or malformed")
    release_url = checked_github_url(
        release.get("html_url"), f"/{REPOSITORY}/releases/tag/"
    )
    if not release_url:
        raise ValueError("Release page URL is not a GitHub release for this repository")

    title = str(release.get("name") or tag).strip() or tag
    title = (title + " — change notes")[:256]
    notes = str(release.get("body") or "").strip() or "No change notes were provided."
    if len(notes) > 3800:
        notes = notes[:3750].rstrip() + "…\n\n[Full release notes](" + release_url + ")"

    download_prefix = f"/{REPOSITORY}/releases/download/"
    assets = release.get("assets")
    if not isinstance(assets, list):
        assets = []
    links = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        url = checked_github_url(asset.get("browser_download_url"), download_prefix)
        name = str(asset.get("name") or "Download").strip()
        if url and name:
            links.append(f"• [{markdown_label(name)}]({url})")

    page_link = f"[All release files and details]({release_url})"
    download_text = "\n".join(links)
    if not download_text:
        download_text = "No downloadable assets are attached yet."
    elif len(download_text) > 860:
        kept = []
        for line in links:
            candidate = "\n".join(kept + [line])
            if len(candidate) > 800:
                break
            kept.append(line)
        download_text = "\n".join(kept)
        if len(kept) < len(links):
            download_text += "\n• Additional files are listed on the release page."
    download_text += "\n\n" + page_link

    prerelease = bool(release.get("prerelease"))
    footer = ("BO3 Customs | DEBUG prerelease | Console testing required"
              if prerelease else "BO3 Customs | GitHub release")
    embed = {
        "title": title,
        "url": release_url,
        "description": notes,
        "color": EMBED_COLOR,
        "fields": [
            {"name": "Downloads", "value": download_text[:1024], "inline": False},
            {"name": "Build", "value": f"{tag} · {'DEBUG prerelease' if prerelease else 'Release'}", "inline": True},
        ],
        "footer": {"text": footer},
    }
    return {
        "username": USERNAME,
        "avatar_url": AVATAR_URL,
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }


def send(webhook, payload):
    parts = urlsplit(webhook)
    if (parts.scheme != "https" or parts.hostname not in ("discord.com", "discordapp.com")
            or not parts.path.startswith("/api/webhooks/") or parts.username or parts.password):
        raise ValueError("DISCORD_WEBHOOK_URL is not a valid HTTPS Discord webhook URL")
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for attempt in range(3):
        request = Request(webhook, data=data, method="POST", headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "BO3-Customs-ReleaseBot/1.0 (GitHub Actions)",
        })
        try:
            with urlopen(request, timeout=20) as response:
                print(f"Discord announcement delivered (HTTP {response.status}).")
            return True
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code <= 599
            if retryable and attempt < 2:
                try:
                    delay = min(15.0, max(1.0, float(error.headers.get("Retry-After", "2"))))
                except (TypeError, ValueError):
                    delay = 2.0
                print(f"::warning::Discord returned HTTP {error.code}; retrying after its rate limit.")
                time.sleep(delay)
                continue
            print(f"::warning::Discord rejected the notice (HTTP {error.code}); the release remains available.")
            return False
        except URLError:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            print("::warning::Discord could not be reached; the release remains available.")
            return False
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_json", help="GitHub release event JSON or REST release JSON")
    args = parser.parse_args()
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("Discord publisher is restricted to the BO3 Customs repository")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        print("::warning::DISCORD_WEBHOOK_URL is not configured; release announcement skipped.")
        return 0
    with open(args.release_json, "r", encoding="utf-8") as stream:
        event = json.load(stream)
    release = event.get("release") if isinstance(event, dict) and isinstance(event.get("release"), dict) else event
    send(webhook, make_payload(release))
    return 0  # Notification trouble must not invalidate a successfully published release.


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"::warning::Discord release notice skipped: {error}")
        raise SystemExit(0)
