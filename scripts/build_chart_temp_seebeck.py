"""
Starrydata の curves CSV から Temperature × Seebeck 散布図用 JSON を生成する。

入力:
  --csv <path>   : starrydata_curves.csv のパス
                   既定: ~/Desktop/starrydata_dataset/starrydata_dataset_latest/starrydata_curves.csv

出力:
  src/_data/chart_temp_seebeck.json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "src/_data/chart_temp_seebeck.json"
DEFAULT_CSV = Path.home() / "Desktop/starrydata_dataset/starrydata_dataset_latest/starrydata_curves.csv"
SNAPSHOT_FILE = DEFAULT_CSV.parent / "db_snapshot.txt"

MAX_POINTS = 12000   # トップに置く軽量チャート向け


def parse_array(s):
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        return np.array(json.loads(s), dtype=float)
    except Exception:
        try:
            return np.array(ast.literal_eval(s), dtype=float)
        except Exception:
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="starrydata_curves.csv path")
    ap.add_argument("--snapshot", type=str, default=None, help="snapshot label (e.g. 20260501)")
    args = ap.parse_args()

    csv_path = args.csv
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    print(f"Loading: {csv_path}  ({csv_path.stat().st_size / 1024 / 1024:.1f} MB)")

    curves = pd.read_csv(
        csv_path,
        usecols=["DOI", "composition", "prop_x", "prop_y", "x", "y"],
        dtype=str,
        low_memory=False,
    )
    print(f"  rows: {len(curves):,}")

    # Temperature × Seebeck をフィルタ
    mask = (
        curves["prop_x"].str.contains("Temperature", case=False, na=False)
        & (curves["prop_y"] == "Seebeck coefficient")
    )
    sub = curves[mask].reset_index(drop=True)
    print(f"  Seebeck (T-x) curves: {len(sub):,}")

    # データポイント展開
    pts_T = []
    pts_S = []
    pts_C = []
    pts_DOI = []
    cap = MAX_POINTS * 3
    for _, row in sub.iterrows():
        xs = parse_array(row["x"])
        ys = parse_array(row["y"])
        if xs is None or ys is None or len(xs) != len(ys) or len(xs) == 0:
            continue
        for xv, yv in zip(xs, ys):
            if 50.0 < xv < 2000.0 and np.isfinite(yv):
                pts_T.append(float(xv))
                pts_S.append(float(yv))
                pts_C.append(row["composition"] or "")
                pts_DOI.append(row["DOI"] or "")
        if len(pts_T) >= cap:
            break

    df = pd.DataFrame({"T": pts_T, "S": pts_S, "comp": pts_C, "doi": pts_DOI})
    print(f"  raw points: {len(df):,}")

    # 1-99 percentile で外れ値除去
    if len(df) > 100:
        lo, hi = np.nanpercentile(df["S"], [1, 99])
        df = df[(df["S"] >= lo) & (df["S"] <= hi)]
    if len(df) > MAX_POINTS:
        df = df.sample(MAX_POINTS, random_state=42)
    df = df.reset_index(drop=True)
    print(f"  final points: {len(df):,}")

    # JSON 出力
    snapshot = args.snapshot
    if snapshot is None and SNAPSHOT_FILE.exists():
        snapshot = SNAPSHOT_FILE.read_text().strip()
    jst = timezone(timedelta(hours=9))
    out = {
        "source": "Starrydata snapshot",
        "snapshot": snapshot or "",
        "fetched_at": datetime.now(jst).isoformat(timespec="seconds"),
        "x_label": "Temperature (K)",
        "y_label": "Seebeck coefficient (μV/K)",
        "point_count": int(len(df)),
        "data": {
            "T":    df["T"].round(2).tolist(),
            "S":    df["S"].round(3).tolist(),
            "comp": df["comp"].tolist(),
            "doi":  df["doi"].tolist(),
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Saved: {OUT_JSON}  ({OUT_JSON.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
