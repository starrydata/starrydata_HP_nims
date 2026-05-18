"""
topics の 7 記事を構造化 JSON に変換する。

スキーマ:
{
  "topics": [
    {
      "id": "43",
      "slug": "materials_informatics",
      "title": "...",
      "date": "2020-09-14",
      "datetime": "2020-09-14T17:29:00+09:00",
      "author": "桂 ゆかり",
      "summary": "...",     // excerpt or 本文先頭から自動生成
      "body_html": "<p>...</p>"
    }
  ]
}
"""

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "_source/extracted/entries/topics"
AUTHORS = ROOT / "_source/extracted/authors.json"
DST = ROOT / "src/_data/topics.json"


def slugify(s: str, max_len: int = 100) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.ASCII)
    s = re.sub(r"_+", "_", s).strip("_-")
    return s[:max_len] or "untitled"


def resolve_slug(basename: str, title: str, id_: str = "") -> str:
    """generic basename はタイトルから再生成。日本語タイトルで slug が作れない場合は basename + id にフォールバック"""
    generic = (
        not basename
        or basename.isdigit()
        or re.fullmatch(r"(content|post)(_\d+)?", basename) is not None
    )
    if not generic:
        return basename
    new_slug = slugify(title)
    if new_slug == "untitled":
        # 日本語のみのタイトルなど、ASCIIで slug が作れない場合
        if basename:
            return f"{basename}_{id_}" if id_ else basename
        return f"item_{id_}" if id_ else "untitled"
    return new_slug


def parse_mt_date(s: str) -> tuple[str, str]:
    """20200914172900 -> ('2020-09-14', '2020-09-14T17:29:00+09:00')"""
    if not s or len(s) < 8:
        return "", ""
    try:
        dt = datetime.strptime(s, "%Y%m%d%H%M%S")
    except ValueError:
        try:
            dt = datetime.strptime(s, "%Y%m%d")
        except ValueError:
            return "", ""
    date = dt.strftime("%Y-%m-%d")
    # MT のサーバ TZ は JST と仮定
    iso = dt.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    return date, iso


def auto_summary(html: str, n: int = 100) -> str:
    """HTML からタグを除去し、先頭 n 文字程度を返す"""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[:n].rstrip() + "…"


def main():
    authors_list = json.loads(AUTHORS.read_text(encoding="utf-8"))
    author_by_id = {a["id"]: a for a in authors_list}

    out = []
    for jf in sorted(SRC_DIR.glob("*.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        body = (d.get("text") or "") + (d.get("text_more") or "")
        body = body.strip()
        date, iso = parse_mt_date(d.get("authored_on", ""))
        author = ""
        au = author_by_id.get(d.get("author_id", ""))
        if au:
            author = au.get("nickname") or au.get("name") or ""

        summary = d.get("excerpt", "").strip()
        if not summary:
            summary = auto_summary(body)

        out.append({
            "id": d["id"],
            "slug": resolve_slug(d["basename"], d["title"], d["id"]),
            "original_basename": d["basename"],
            "title": d["title"],
            "date": date,
            "datetime": iso,
            "author": author,
            "summary": summary,
            "body_html": body,
        })

    # 新しい順に並べる
    out.sort(key=lambda x: x["datetime"], reverse=True)

    DST.write_text(
        json.dumps({"topics": out}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"topics: {len(out)}")
    for t in out:
        print(f"  {t['date']}  {t['slug']:25} {t['title']}")


if __name__ == "__main__":
    main()
