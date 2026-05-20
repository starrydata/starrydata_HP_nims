"""
Figshare から Starrydata の最新月次スナップショットを取得し、
Temperature × Seebeck の散布図用 JSON を生成する。

実行: python3 scripts/fetch_chart_temp_seebeck.py
出力: src/_data/chart_temp_seebeck.json

GitHub Actions で毎月実行する想定（.github/workflows/update-chart.yml）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "src/_data/chart_temp_seebeck.json"
WORK_DIR = Path(os.environ.get("STARRYDATA_WORK_DIR", "/tmp/starrydata_chart_build"))
FIGSHARE_PROJECT_ID = 155129

UA = "starrydata-hp/1.0"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_latest_snapshot() -> dict:
    """Figshare project から最新の dataset article を取得"""
    arts = get_json(
        f"https://api.figshare.com/v2/projects/{FIGSHARE_PROJECT_ID}/articles?page_size=20"
    )
    arts.sort(key=lambda a: a.get("published_date") or "", reverse=True)
    if not arts:
        raise RuntimeError("Figshare project has no articles")
    return arts[0]


def get_article_files(article_id: int) -> list[dict]:
    return get_json(f"https://api.figshare.com/v2/articles/{article_id}/files")


def download(url: str, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        print(f"  cached: {dst.name} ({dst.stat().st_size / 1024 / 1024:.1f} MB)")
        return
    print(f"  downloading {url} → {dst.name}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as r, dst.open("wb") as f:
        shutil.copyfileobj(r, f)
    print(f"  done ({dst.stat().st_size / 1024 / 1024:.1f} MB)")


def main():
    # 1. Figshare 最新 snapshot
    print("[1/4] Finding latest Figshare snapshot ...", flush=True)
    snap = get_latest_snapshot()
    title = snap["title"]
    doi = snap.get("doi", "")
    print(f"  → {title} (DOI: {doi})")

    # 2. ファイル一覧
    files = get_article_files(snap["id"])
    zip_file = next((f for f in files if f["name"].endswith(".zip")), None)
    if not zip_file:
        # zip がない場合は CSV を直接取得する候補も
        csv_file = next((f for f in files if "curves" in f["name"].lower() and f["name"].endswith(".csv")), None)
        if not csv_file:
            print("ERROR: no zip or curves.csv in snapshot files", file=sys.stderr)
            sys.exit(1)
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        curves_csv = WORK_DIR / csv_file["name"]
        download(csv_file["download_url"], curves_csv)
    else:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = WORK_DIR / zip_file["name"]
        download(zip_file["download_url"], zip_path)

        # 3. 解凍
        print(f"[2/4] Extracting {zip_path.name} ...", flush=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(WORK_DIR)
        candidates = list(WORK_DIR.rglob("starrydata_curves.csv"))
        if not candidates:
            print("ERROR: starrydata_curves.csv not found in zip", file=sys.stderr)
            sys.exit(1)
        curves_csv = candidates[0]
        print(f"  curves CSV: {curves_csv} ({curves_csv.stat().st_size / 1024 / 1024:.1f} MB)")

    # 4. build_chart_temp_seebeck.py を呼び出して JSON 生成
    print("[3/4] Building chart JSON ...", flush=True)
    snapshot_label = title  # e.g. "20260501_starrydata2"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_chart_temp_seebeck.py"),
            "--csv", str(curves_csv),
            "--snapshot", snapshot_label,
        ],
        check=True,
    )

    print("[4/4] Cleaning up workdir ...")
    # zip と解凍ファイルは消しておく（CI 容量節約）
    try:
        for p in WORK_DIR.iterdir():
            if p.is_file() and (p.suffix == ".zip" or p.name.startswith("starrydata_")):
                p.unlink()
            elif p.is_dir() and p.name.startswith("starrydata_"):
                shutil.rmtree(p, ignore_errors=True)
    except Exception as e:
        print(f"  cleanup warn: {e}")

    print(f"\n✅ Done. JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
