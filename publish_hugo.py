#!/usr/bin/env python3
"""Publish a markdown file to the Hugo weekly-blogs site.

Reads a markdown file with frontmatter (title, [subtitle], [date]) and writes
it to content/<section>/<slug>.md, then optionally git commits and pushes.

Usage:
    publish_hugo.py <section> <markdown-file> [--no-git] [--no-push] [--verify]

Sections: mlp-weekly | qmc-weekly | cqed-weekly

Defaults:
    - Generates slug from title (lowercased, hyphen-separated)
    - Adds today's date to frontmatter if missing
    - git add + commit + push (unless --no-git or --no-push)
    - --verify: after push, wait and check live URL returns 200
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent.resolve()
SECTIONS = {"mlp-weekly", "qmc-weekly", "cqed-weekly"}

# Public URL pattern — update once Cloudflare Pages live
PUBLIC_BASE = os.environ.get("WEEKLY_BLOGS_BASE", "https://digest.cwmyung.com")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Frontmatter is YAML-ish key: value."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        fm[k.strip()] = v
    return fm, m.group(2)


def slugify(title: str) -> str:
    """Derive a Hugo-friendly slug from a title."""
    s = title.lower()
    # Strip common boilerplate
    s = re.sub(r"^(ml potentials weekly|mlp weekly|qmc weekly|cqed weekly)\s*[—\-:]\s*", "", s)
    s = re.sub(r"[^a-z0-9\-\s]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s or "post"


def run(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("section", choices=sorted(SECTIONS))
    p.add_argument("markdown", help="path to markdown file with frontmatter")
    p.add_argument("--slug", default=None, help="override generated slug")
    p.add_argument("--no-git", action="store_true", help="do not git commit")
    p.add_argument("--no-push", action="store_true", help="commit but do not push")
    p.add_argument("--verify", action="store_true",
                   help="after push, wait for deploy and check URL returns 200")
    p.add_argument("--verify-wait", type=int, default=90,
                   help="seconds to wait before verifying URL (default 90)")
    args = p.parse_args()

    src = Path(args.markdown).resolve()
    if not src.exists():
        sys.exit(f"markdown not found: {src}")
    text = src.read_text()
    fm, body = parse_frontmatter(text)
    if "title" not in fm:
        sys.exit("frontmatter is missing a `title:` field")

    if "date" not in fm:
        fm["date"] = datetime.now().strftime("%Y-%m-%d")

    slug = args.slug or slugify(fm["title"])
    out_path = HERE / "content" / args.section / f"{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Re-emit frontmatter in stable order
    fm_lines = []
    for k in ["date", "title", "subtitle", "draft"]:
        if k in fm:
            v = fm[k]
            fm_lines.append(f'{k}: "{v}"')
    for k, v in fm.items():
        if k not in {"date", "title", "subtitle", "draft"}:
            fm_lines.append(f'{k}: "{v}"')

    new_text = "---\n" + "\n".join(fm_lines) + "\n---\n" + body.lstrip("\n")
    out_path.write_text(new_text)

    result = {
        "section": args.section,
        "slug": slug,
        "path": str(out_path.relative_to(HERE)),
        "url": f"{PUBLIC_BASE}/{args.section}/{slug}/",
    }

    if not args.no_git:
        try:
            run(["git", "add", str(out_path.relative_to(HERE))], cwd=HERE)
            commit_msg = f"publish {args.section}/{slug}"
            run(["git", "commit", "-m", commit_msg], cwd=HERE)
            result["committed"] = True
            if not args.no_push:
                run(["git", "push"], cwd=HERE)
                result["pushed"] = True
        except subprocess.CalledProcessError as e:
            result["git_error"] = e.stderr or str(e)

    if args.verify and result.get("pushed"):
        time.sleep(args.verify_wait)
        try:
            req = urllib.request.Request(
                result["url"],
                headers={"User-Agent": "Mozilla/5.0 publish_hugo.py"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result["verified_status"] = resp.status
                result["live"] = resp.status == 200
        except Exception as e:
            result["verified_status"] = "error"
            result["verify_error"] = str(e)
            result["live"] = False

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
