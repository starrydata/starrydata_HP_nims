"""
data 配下の 7 ページ (index + 6 分野) を解析し、
src/_data/projects.json を生成する。

スキーマ:
{
  "page": {
    "title": "進行中のデータ収集プロジェクト",
    "intro_html": "...",
    "list_heading": "データ収集プロジェクト一覧"
  },
  "projects": [
    {
      "slug": "thermoelectric",
      "card_title": "熱電材料",
      "card_class": "p01",
      "full_title": "ThermoelectricMaterials: 熱電材料プロジェクト",
      "owner": "担当：田中敦美",
      "body_html": "<p>...</p>",      # 編集対象 (HTML)
      "figure": {
        "image": "/data/img/img_thermoelectric_01.png",
        "caption": "..."
      }
    }
  ]
}
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "_source/extracted/pages/data"
DST = ROOT / "src/_data/projects.json"


def load_page(filename: str) -> dict:
    return json.loads((SRC_DIR / filename).read_text(encoding="utf-8"))


def parse_index_cards(html: str):
    """data/index の box リンクを抽出してカード情報を返す"""
    # <div class="box"><a href="thermoelectric.html" class="p01"><div class="inner"><div class="ttl">熱電材料</div></div></a></div>
    box_re = re.compile(
        r'<div class="box">\s*<a href="([^"]+)" class="([^"]+)">\s*<div class="inner">\s*<div class="ttl">([^<]+)</div>',
        re.S,
    )
    cards = []
    for m in box_re.finditer(html):
        href, klass, title = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        slug = Path(href).stem  # thermoelectric.html -> thermoelectric
        cards.append({"slug": slug, "card_title": title, "card_class": klass, "href": href})
    return cards


def split_intro(html: str):
    """data/index の本文を、リスト直前までの導入 HTML として返す"""
    # box_data ブロックを境界に
    idx = html.find('<div class="box_data">')
    if idx == -1:
        return html, ""
    # box_data の親 <!-- Column --><div class="b60"> を遡る
    before = html[:idx]
    # 最後の <h3 class="ttl_second">データ収集プロジェクト一覧</h3> 周辺を切り出す
    list_heading_re = re.compile(r'<h3 class="ttl_second">([^<]+)</h3>')
    matches = list(list_heading_re.finditer(before))
    list_heading = ""
    if matches:
        last = matches[-1]
        list_heading = last.group(1).strip()
        # その見出しを囲むブロックも除外
        block_start = before.rfind('<!-- Title -->', 0, last.start())
        if block_start == -1:
            block_start = last.start()
        intro_html = before[:block_start].rstrip()
    else:
        intro_html = before.rstrip()
    return intro_html, list_heading


def parse_field_page(doc: dict):
    """各分野ページから本文と図を抽出"""
    html = doc["text"]
    # 図の検出: <div class="...alignC..."><img src="img/xxx.png"><p>caption</p></div>
    fig_re = re.compile(
        r'<div class="[^"]*alignC[^"]*">\s*<img src="([^"]+)"[^>]*>\s*<p>(.*?)</p>\s*</div>',
        re.S,
    )
    fig = None
    fig_match = fig_re.search(html)
    if fig_match:
        img = fig_match.group(1).strip()
        # 相対 img/... を /data/img/... に変換
        if img.startswith("img/"):
            img = "/data/" + img
        caption = re.sub(r'<br[^>]*>', '\n', fig_match.group(2)).strip()
        caption = re.sub(r'<[^>]+>', '', caption).strip()
        fig = {"image": img, "caption": caption}
        # 図ブロックを本文から除去
        html = html[:fig_match.start()] + html[fig_match.end():]

    # コメントを除去
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    # 連続改行を整理
    html = re.sub(r'\n{3,}', '\n\n', html).strip()

    return {
        "slug": doc["basename"],
        "full_title": doc["title"],
        "owner": doc.get("subtitle", ""),
        "body_html": html,
        "figure": fig,
    }


def fix_img_paths_in_html(html: str, blog_path: str) -> str:
    """相対 'img/...' を '/{blog_path}/img/...' に書き換え"""
    return re.sub(r'(src|href)="img/', f'\\1="/{blog_path}/img/', html)


def main():
    index_doc = load_page("19__index.json")
    field_files = [
        "20__thermoelectric.json",
        "21__magnetic.json",
        "22__quasicrystal.json",
        "23__condensed.json",
        "24__battery.json",
        "25__piezoelectric.json",
    ]

    intro_html, list_heading = split_intro(index_doc["text"])
    # index ページの画像パスも書き換え
    intro_html = fix_img_paths_in_html(intro_html, "data")

    cards = parse_index_cards(index_doc["text"])
    card_by_slug = {c["slug"]: c for c in cards}

    projects = []
    for fn in field_files:
        doc = load_page(fn)
        info = parse_field_page(doc)
        info["body_html"] = fix_img_paths_in_html(info["body_html"], "data")
        if info["figure"]:
            info["figure"]["image"] = fix_img_paths_in_html(
                info["figure"]["image"], "data"
            ) if info["figure"]["image"].startswith("img/") else info["figure"]["image"]
        card = card_by_slug.get(info["slug"], {})
        info["card_title"] = card.get("card_title", info["full_title"])
        info["card_class"] = card.get("card_class", "")
        projects.append(info)

    out = {
        "page": {
            "title": index_doc["title"],
            "intro_html": intro_html,
            "list_heading": list_heading,
        },
        "projects": projects,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"projects: {len(projects)}")
    for p in projects:
        fig = "yes" if p["figure"] else "no"
        print(f"  - {p['slug']:15} {p['card_title']:10} (figure: {fig})")


if __name__ == "__main__":
    main()
