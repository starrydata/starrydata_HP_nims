"""
MovableType の XML バックアップを解析し、
templates / pages / entries / blogs / folders / authors / assets を
編集しやすいファイル群に分解する。

出力先: _source/extracted/
  blogs.json          全ブログ一覧
  folders.json        全フォルダ一覧
  authors.json        ユーザー一覧
  assets.json         画像メタ情報
  structure.json      全体サマリ
  templates/<blog>/<id>__<type>__<name>.html  各テンプレート本体
  templates/<blog>/index.json                 テンプレートのメタ情報
  pages/<blog>/<basename>.json                各ページ（タイトル＋本文）
  entries/<blog>/<basename>.json              各記事
"""

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "http://www.sixapart.com/ns/movabletype"
ROOT = Path(__file__).resolve().parent.parent
SRC_XML = ROOT / "_source/backup/Movable_Type-2026-05-15-09-06-04-Export-1.xml"
OUT = ROOT / "_source/extracted"


def tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def text_of(elem, name, default=""):
    child = elem.find(tag(name))
    if child is None:
        return default
    return (child.text or "").strip()


def safe_basename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
    return s.strip("_") or "untitled"


def safe_blog_dir(site_path: str, bid: str) -> str:
    """site_path から安全なディレクトリ名を作る（絶対パスや特殊文字を除去）"""
    if not site_path:
        return f"blog_{bid}"
    # 末尾の basename を採用、無理なら ID
    name = Path(site_path).name or site_path.strip("/").split("/")[-1]
    name = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    return name or f"blog_{bid}"


def main():
    if not SRC_XML.exists():
        print(f"NOT FOUND: {SRC_XML}", file=sys.stderr)
        sys.exit(1)

    print(f"parsing: {SRC_XML}")
    tree = ET.parse(SRC_XML)
    root = tree.getroot()

    OUT.mkdir(parents=True, exist_ok=True)

    # --- blogs ---
    blogs = {}
    for b in root.findall(tag("blog")):
        bid = b.get("id")
        blogs[bid] = {
            "id": bid,
            "name": b.get("name"),
            "site_path": b.get("site_path"),
            "site_url": b.get("site_url"),
            "parent_id": b.get("parent_id"),
            "created_on": b.get("created_on"),
            "modified_on": b.get("modified_on"),
            "theme_id": b.get("theme_id"),
            "language": b.get("language"),
        }
    website = root.find(tag("website"))
    if website is not None:
        blogs[website.get("id")] = {
            "id": website.get("id"),
            "name": website.get("name"),
            "site_path": website.get("site_path"),
            "site_url": website.get("site_url"),
            "parent_id": None,
            "kind": "website",
            "theme_id": website.get("theme_id"),
        }
    (OUT / "blogs.json").write_text(
        json.dumps(blogs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ブログIDから安全なディレクトリ名への辞書（絶対パスを避けるため）
    bid_to_path = {bid: safe_blog_dir(b.get("site_path", ""), bid) for bid, b in blogs.items()}

    # --- folders ---
    folders = []
    for f in root.findall(tag("folder")):
        folders.append({
            "id": f.get("id"),
            "blog_id": f.get("blog_id"),
            "basename": f.get("basename"),
            "label": f.get("label"),
            "parent": f.get("parent"),
        })
    (OUT / "folders.json").write_text(
        json.dumps(folders, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- authors ---
    authors = []
    for a in root.findall(tag("author")):
        authors.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "nickname": a.get("nickname"),
            "email": a.get("email"),
        })
    (OUT / "authors.json").write_text(
        json.dumps(authors, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- images / assets ---
    assets = []
    for im in root.findall(tag("image")):
        assets.append({
            "id": im.get("id"),
            "blog_id": im.get("blog_id"),
            "label": im.get("label"),
            "file_name": im.get("file_name"),
            "file_path": im.get("file_path"),
            "url": im.get("url"),
            "mime_type": im.get("mime_type"),
            "image_width": im.get("image_width"),
            "image_height": im.get("image_height"),
            "parent": im.get("parent"),
            "description": im.get("description"),
        })
    (OUT / "assets.json").write_text(
        json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- pages ---
    pages_dir = OUT / "pages"
    pages_dir.mkdir(exist_ok=True)
    pages_meta = []
    for p in root.findall(tag("page")):
        bid = p.get("blog_id")
        basename = p.get("basename") or f"page_{p.get('id')}"
        # MTでは title は属性、本文は子要素
        title = p.get("title") or text_of(p, "title")
        body = text_of(p, "text")
        more = text_of(p, "text_more")
        excerpt = text_of(p, "excerpt")
        keywords = text_of(p, "keywords")
        # field.* 形式のカスタムフィールド属性を拾う
        custom_fields = {k.replace("field.", ""): v for k, v in p.attrib.items() if k.startswith("field.")}
        data = {
            "id": p.get("id"),
            "blog_id": bid,
            "blog_path": bid_to_path.get(bid),
            "basename": basename,
            "title": title,
            "subtitle": custom_fields.get("pagedatasubtitle", ""),
            "custom_fields": custom_fields,
            "text": body,
            "text_more": more,
            "excerpt": excerpt,
            "keywords": keywords,
            "status": p.get("status"),
            "created_on": p.get("created_on"),
            "modified_on": p.get("modified_on"),
            "author_id": p.get("author_id"),
        }
        subdir = pages_dir / (bid_to_path.get(bid) or f"blog_{bid}")
        subdir.mkdir(parents=True, exist_ok=True)
        # ファイル名に id を含めて basename 重複を回避
        fname = f"{p.get('id')}__{safe_basename(basename)}.json"
        (subdir / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        pages_meta.append({k: data[k] for k in ("id", "blog_id", "blog_path", "basename", "title", "status")})
    (OUT / "pages_index.json").write_text(
        json.dumps(pages_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- entries ---
    entries_dir = OUT / "entries"
    entries_dir.mkdir(exist_ok=True)
    entries_meta = []
    for e in root.findall(tag("entry")):
        bid = e.get("blog_id")
        basename = e.get("basename") or f"entry_{e.get('id')}"
        title = e.get("title") or text_of(e, "title")
        body = text_of(e, "text")
        more = text_of(e, "text_more")
        excerpt = text_of(e, "excerpt")
        keywords = text_of(e, "keywords")
        custom_fields = {k.replace("field.", ""): v for k, v in e.attrib.items() if k.startswith("field.")}
        data = {
            "id": e.get("id"),
            "blog_id": bid,
            "blog_path": bid_to_path.get(bid),
            "basename": basename,
            "title": title,
            "custom_fields": custom_fields,
            "text": body,
            "text_more": more,
            "excerpt": excerpt,
            "keywords": keywords,
            "status": e.get("status"),
            "created_on": e.get("created_on"),
            "modified_on": e.get("modified_on"),
            "authored_on": e.get("authored_on"),
            "author_id": e.get("author_id"),
        }
        subdir = entries_dir / (bid_to_path.get(bid) or f"blog_{bid}")
        subdir.mkdir(parents=True, exist_ok=True)
        fname = f"{e.get('id')}__{safe_basename(basename)}.json"
        (subdir / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        entries_meta.append({k: data[k] for k in ("id", "blog_id", "blog_path", "basename", "title", "status", "authored_on")})
    (OUT / "entries_index.json").write_text(
        json.dumps(entries_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- templates ---
    tpl_dir = OUT / "templates"
    tpl_dir.mkdir(exist_ok=True)
    tpl_meta_by_blog = {}
    for t in root.findall(tag("template")):
        bid = t.get("blog_id") or "0"
        name = t.get("name") or "untitled"
        ttype = t.get("type") or "unknown"
        identifier = t.get("identifier") or ""
        outfile = t.get("outfile") or ""
        text = text_of(t, "text")
        sub = tpl_dir / (bid_to_path.get(bid) or f"blog_{bid}")
        sub.mkdir(parents=True, exist_ok=True)
        # ファイル名は重複防止のためIDを含める
        fname = f"{t.get('id')}__{ttype}__{safe_basename(name)}.html"
        (sub / fname).write_text(text, encoding="utf-8")
        meta = {
            "id": t.get("id"),
            "blog_id": bid,
            "blog_path": bid_to_path.get(bid),
            "name": name,
            "type": ttype,
            "identifier": identifier,
            "outfile": outfile,
            "build_type": t.get("build_type"),
            "linked_file": t.get("linked_file"),
            "file": fname,
            "byte_size": len(text.encode("utf-8")),
        }
        tpl_meta_by_blog.setdefault(bid, []).append(meta)

    for bid, metas in tpl_meta_by_blog.items():
        sub = tpl_dir / (bid_to_path.get(bid) or f"blog_{bid}")
        (sub / "index.json").write_text(
            json.dumps(metas, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # --- structure summary ---
    summary = {
        "blogs": {bid: {"name": b["name"], "site_path": b.get("site_path")} for bid, b in blogs.items()},
        "counts": {
            "blogs": len(blogs),
            "folders": len(folders),
            "authors": len(authors),
            "assets": len(assets),
            "pages": len(pages_meta),
            "entries": len(entries_meta),
            "templates": sum(len(v) for v in tpl_meta_by_blog.values()),
        },
        "templates_per_blog": {
            (bid_to_path.get(bid) or f"blog_{bid}"): len(v) for bid, v in tpl_meta_by_blog.items()
        },
        "pages_per_blog": {},
        "entries_per_blog": {},
    }
    for p in pages_meta:
        key = p["blog_path"] or f"blog_{p['blog_id']}"
        summary["pages_per_blog"][key] = summary["pages_per_blog"].get(key, 0) + 1
    for e in entries_meta:
        key = e["blog_path"] or f"blog_{e['blog_id']}"
        summary["entries_per_blog"][key] = summary["entries_per_blog"].get(key, 0) + 1

    (OUT / "structure.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))
    print("done.")


if __name__ == "__main__":
    main()
