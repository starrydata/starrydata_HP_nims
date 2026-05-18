"""
Desktop/Movable/ の画像（{id}-{file_name} 形式）を、
MovableType のオリジナル配置にしたがって src/ 配下に振り分ける。

assets.json の blog_id を元に、各ブログの site_path/img/<file_name> に配置。
blog_id=1 (ルート) は src/common/img/ ではなく src/assets/img/ にする。
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "_source/assets"
DST_ROOT = ROOT / "src"
ASSETS_JSON = ROOT / "_source/extracted/assets.json"
BLOGS_JSON = ROOT / "_source/extracted/blogs.json"


def main():
    assets = json.loads(ASSETS_JSON.read_text(encoding="utf-8"))
    blogs = json.loads(BLOGS_JSON.read_text(encoding="utf-8"))

    # blog_id -> site_path
    blog_path = {}
    for bid, b in blogs.items():
        sp = b.get("site_path", "") or ""
        # ルートサイトは特殊扱い
        if sp.startswith("/") or sp == "":
            blog_path[bid] = ""  # ルート
        else:
            blog_path[bid] = sp
    blog_path["1"] = ""  # 明示的にルート

    # 既存 src/assets/img と src/img をクリーンアップ
    for p in (DST_ROOT / "assets/img", DST_ROOT / "img"):
        if p.exists():
            shutil.rmtree(p)

    placed = []
    missing = []
    for a in assets:
        bid = a["blog_id"]
        fname = a["file_name"]
        if not fname:
            continue
        src = SRC_DIR / f"{a['id']}-{fname}"
        if not src.exists():
            missing.append(str(src.name))
            continue

        bpath = blog_path.get(bid, "")
        if bpath:
            dst = DST_ROOT / bpath / "img" / fname
        else:
            # ルート（mt）の画像は /img/ へ（MTオリジナル配置に合わせる）
            dst = DST_ROOT / "img" / fname

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        placed.append({"id": a["id"], "blog_id": bid, "blog_path": bpath, "dest": str(dst.relative_to(ROOT))})

    print(f"placed:  {len(placed)}")
    print(f"missing: {len(missing)}")
    if missing[:5]:
        print("missing samples:", missing[:5])

    # 配置レポート保存
    (ROOT / "_source/extracted/asset_placement.json").write_text(
        json.dumps(placed, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
