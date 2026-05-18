"""
extracted/pages, extracted/entries の JSON を Eleventy 用の
src/_data/ 配下に整理する。

- src/_data/pages_all.json:
    通常ページ（mt ブログ＝ホーム埋め込み用は除外）。pagination 用配列。
- src/_data/home_sections.json:
    mt ブログ配下のページ。トップページのセクション素材。
- src/_data/topics.json:
    topics の entries 一覧（記事 7 件）
- src/_data/papers.json:
    papers の entries 一覧（記事 24 件）
- src/_data/blogs.json:
    ブログメタ（既存をそのままコピー）
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "_source/extracted"
DATA = ROOT / "src/_data"

DATA.mkdir(parents=True, exist_ok=True)


def load_dir(rel: str):
    """extracted/<rel>/<blog>/*.json を読み込んで配列で返す"""
    base = EXTRACTED / rel
    items = []
    for blog_dir in sorted(base.iterdir()):
        if not blog_dir.is_dir():
            continue
        for jf in sorted(blog_dir.glob("*.json")):
            items.append(json.loads(jf.read_text(encoding="utf-8")))
    return items


# 構造化 JSON 専用にして pages_all から除外するページ
# (blog_path, basename) のセット
STRUCTURED_PAGES = {
    ("project", "members"),
    ("data", "index"),
    ("data", "thermoelectric"),
    ("data", "magnetic"),
    ("data", "quasicrystal"),
    ("data", "condensed"),
    ("data", "battery"),
    ("data", "piezoelectric"),
}


def main():
    all_pages = load_dir("pages")
    all_entries = load_dir("entries")

    # mt(home 埋め込み) と それ以外を分離
    home_sections_list = [p for p in all_pages if p["blog_path"] == "mt"]
    # tag (@top_xxx) をキーとした dict にする
    # 例: @top_main_img_slider -> page
    home_sections = {}
    for p in home_sections_list:
        for t in p.get("tags", []) or []:
            if t.startswith("@top_"):
                key = t.lstrip("@")  # "top_main_img_slider"
                home_sections[key] = p
                break
    other_pages = [
        p for p in all_pages
        if p["blog_path"] != "mt"
        and (p["blog_path"], p["basename"]) not in STRUCTURED_PAGES
    ]

    # 通常ページは URL 用にスラッグ計算
    for p in other_pages:
        p["url"] = f"/{p['blog_path']}/{p['basename']}.html"

    # entries
    # topics/papers は構造化版を extract_topics.py / extract_papers.py で別途生成するため、ここでは出力しない

    (DATA / "pages_all.json").write_text(
        json.dumps(other_pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA / "home_sections.json").write_text(
        json.dumps(home_sections, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # blogs / authors もコピー（参考用）
    shutil.copy(EXTRACTED / "blogs.json", DATA / "blogs.json")
    shutil.copy(EXTRACTED / "authors.json", DATA / "authors.json")
    shutil.copy(EXTRACTED / "assets.json", DATA / "mt_assets.json")

    print(f"pages_all     : {len(other_pages)}")
    print(f"home_sections : {len(home_sections)}")


if __name__ == "__main__":
    main()
