"""
抽出済みテンプレートを役割別に仕分ける。

入力: _source/extracted/templates/<blog>/*.html + index.json
出力:
  _source/classified/
    layouts/<blog>/             # type=index で .html 出力 → ページレイアウト
    pages/<blog>/               # type=page          → 固定ページ用テンプレ
    entries/<blog>/             # type=individual    → 記事用テンプレ
    archives/<blog>/            # type=archive       → 一覧テンプレ
    modules/<blog>/             # type=custom        → モジュール（header,footer等）
    widgets/<blog>/             # type=widget/widgetset
    feeds/<blog>/               # outfile が .xml
    _ignore/<blog>/             # backup, comment_*, search 等
  assets/
    css/                        # 拡張 .css のテンプレ
    js/                         # 拡張 .js のテンプレ
  classification_report.json    # 仕分け結果サマリ
"""

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "_source/extracted/templates"
CLASSIFIED = ROOT / "_source/classified"
ASSETS_OUT = ROOT / "_source/classified/assets"

# 役割を判定する
IGNORE_TYPES = {
    "backup",
    "comment_listing",
    "comment_preview",
    "comment_response",
    "search_results",
    "cd_search_results",
    "dynamic_error",
    "popup_image",
}

ROLE_BY_TYPE = {
    "page": "pages",
    "individual": "entries",
    "archive": "archives",
    "custom": "modules",
    "widget": "widgets",
    "widgetset": "widgets",
}


def role_of(meta: dict) -> str:
    t = meta.get("type", "")
    outfile = meta.get("outfile") or ""
    ext = Path(outfile).suffix.lower()

    if t in IGNORE_TYPES:
        return "_ignore"
    if t == "index":
        if ext == ".css":
            return "css"
        if ext == ".js":
            return "js"
        if ext == ".xml":
            return "feeds"
        if ext in (".html", ".htm", ""):
            return "layouts"
        return "layouts"
    return ROLE_BY_TYPE.get(t, "_ignore")


def main():
    if CLASSIFIED.exists():
        shutil.rmtree(CLASSIFIED)
    CLASSIFIED.mkdir(parents=True)
    ASSETS_OUT.mkdir(parents=True, exist_ok=True)
    (ASSETS_OUT / "css").mkdir(parents=True, exist_ok=True)
    (ASSETS_OUT / "js").mkdir(parents=True, exist_ok=True)

    report = {"counts": {}, "items": []}

    for blog_dir in sorted(EXTRACTED.iterdir()):
        if not blog_dir.is_dir():
            continue
        idx_path = blog_dir / "index.json"
        if not idx_path.exists():
            continue
        metas = json.loads(idx_path.read_text(encoding="utf-8"))

        for m in metas:
            blog = blog_dir.name
            role = role_of(m)
            src_file = blog_dir / m["file"]
            if not src_file.exists():
                continue
            content = src_file.read_text(encoding="utf-8")

            if role in ("css", "js"):
                # outfile のパス構造を尊重して assets 下に置く
                outfile = m["outfile"] or ""
                # MTのoutfileは "common/css/contents.css" のような相対パス
                # blog 別にしたい場合もあるが、mt(共通) は共通、それ以外は blog プレフィックスを付ける
                if blog == "mt":
                    rel = outfile
                else:
                    rel = f"{blog}/{outfile}"
                dst = ASSETS_OUT / role / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(content, encoding="utf-8")
                report["items"].append({
                    "blog": blog, "id": m["id"], "name": m["name"],
                    "type": m["type"], "outfile": outfile, "role": role,
                    "dest": str(dst.relative_to(ROOT)),
                })
            else:
                dst_dir = CLASSIFIED / role / blog
                dst_dir.mkdir(parents=True, exist_ok=True)
                # ファイル名は元の安全名を流用
                dst = dst_dir / m["file"]
                dst.write_text(content, encoding="utf-8")
                report["items"].append({
                    "blog": blog, "id": m["id"], "name": m["name"],
                    "type": m["type"], "outfile": m.get("outfile") or "",
                    "role": role,
                    "dest": str(dst.relative_to(ROOT)),
                })

    # counts
    for it in report["items"]:
        key = it["role"]
        report["counts"][key] = report["counts"].get(key, 0) + 1

    (CLASSIFIED / "classification_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    print(f"\n出力: {CLASSIFIED}")


if __name__ == "__main__":
    main()
