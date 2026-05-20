"""
Starrydata の curves CSV から Temperature × Seebeck 散布図用 Plotly Figure JSON を生成する。

visualize_all.py の (H) 主要物性散布図と同じ Plotly Express スタイル：
  - color="composition" で組成別カラフル
  - color_discrete_sequence: Light24 + Bold + Alphabet
  - template="plotly_dark"
  - opacity=0.55, marker size=3
  - showlegend=False

入力:
  --csv <path>       starrydata_curves.csv のパス
                     既定: ~/Desktop/starrydata_dataset/starrydata_dataset_latest/starrydata_curves.csv
  --snapshot <label> snapshot ラベル（GitHub Actions 用）

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
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "src/_data/chart_temp_seebeck.json"
DEFAULT_CSV = Path.home() / "Desktop/starrydata_dataset/starrydata_dataset_latest/starrydata_curves.csv"
SNAPSHOT_FILE = DEFAULT_CSV.parent / "db_snapshot.txt"

MAX_POINTS = 20000   # visualize_all.py と同じ


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
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--snapshot", type=str, default=None)
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

    mask = (
        curves["prop_x"].str.contains("Temperature", case=False, na=False)
        & (curves["prop_y"] == "Seebeck coefficient")
    )
    sub = curves[mask].reset_index(drop=True)
    print(f"  Seebeck (T-x) curves: {len(sub):,}")

    # データポイント展開
    pts_T, pts_S, pts_C = [], [], []
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
                pts_C.append(row["composition"] or "(unknown)")
        if len(pts_T) >= cap:
            break

    df = pd.DataFrame({"T": pts_T, "S": pts_S, "composition": pts_C})
    print(f"  raw points: {len(df):,}")

    # 1-99 percentile で外れ値除去
    if len(df) > 100:
        lo, hi = np.nanpercentile(df["S"], [1, 99])
        df = df[(df["S"] >= lo) & (df["S"] <= hi)]
    if len(df) > MAX_POINTS:
        df = df.sample(MAX_POINTS, random_state=42)
    df = df.reset_index(drop=True)
    n_pts = len(df)
    n_comps = df["composition"].nunique()
    print(f"  final points: {n_pts:,}  / unique compositions: {n_comps:,}")

    # ----- Plotly Express でダッシュボードと同等の図を生成 -----
    fig = px.scatter(
        df, x="T", y="S",
        color="composition",
        opacity=0.55,
        color_discrete_sequence=(
            px.colors.qualitative.Light24
            + px.colors.qualitative.Bold
            + px.colors.qualitative.Alphabet
        ),
        hover_data=["composition"],
    )
    fig.update_layout(
        template="plotly_dark",
        height=520,
        showlegend=False,
        xaxis_title="Temperature [K]",
        yaxis_title="Seebeck coefficient [μV/K]",
        margin=dict(t=20, r=12, b=56, l=68),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f0c29",
        font=dict(family='Inter, "Noto Sans JP", sans-serif'),
    )
    fig.update_traces(marker=dict(size=3))

    fig_dict = json.loads(pio.to_json(fig))

    snapshot = args.snapshot
    if snapshot is None and SNAPSHOT_FILE.exists():
        snapshot = SNAPSHOT_FILE.read_text().strip()
    jst = timezone(timedelta(hours=9))
    out = {
        "source": "Starrydata snapshot",
        "snapshot": snapshot or "",
        "fetched_at": datetime.now(jst).isoformat(timespec="seconds"),
        "point_count": n_pts,
        "composition_count": n_comps,
        "figure": fig_dict,   # Plotly newPlot にそのまま渡せる {data, layout}
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    size_kb = OUT_JSON.stat().st_size / 1024
    print(f"\n✅ Saved: {OUT_JSON}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
