"""
starrydata_curves.csv を project_names 別に集計し、各プロジェクトのデータ収集対象
（代表的な prop_x × prop_y ペア）を抽出する。

出力: 標準出力で各プロジェクトの統計を表示
      src/_data/research_raw.json に JSON で保存
"""

import argparse
import ast
import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = Path.home() / "Desktop/starrydata_dataset/starrydata_dataset_latest/starrydata_curves.csv"
OUT = ROOT / "src/_data/research_raw.json"


def parse_projects(s):
    if not isinstance(s, str) or not s.strip():
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    return [s]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = ap.parse_args()

    print(f"Loading {args.csv} ...")
    df = pd.read_csv(
        args.csv,
        usecols=["DOI", "composition", "prop_x", "prop_y", "project_names"],
        dtype=str,
        low_memory=False,
    )
    print(f"  rows: {len(df):,}")

    df["projects"] = df["project_names"].apply(parse_projects)
    df = df.explode("projects")
    df = df.dropna(subset=["projects"])

    grouped = df.groupby("projects")

    out = {}
    for proj, g in grouped:
        pairs = (g["prop_x"].fillna("?") + " vs " + g["prop_y"].fillna("?")).value_counts()
        prop_y_counts = g["prop_y"].fillna("?").value_counts()
        n_dois = g["DOI"].nunique()
        n_comps = g["composition"].nunique()
        out[proj] = {
            "curves": int(len(g)),
            "papers": int(n_dois),
            "compositions": int(n_comps),
            "top_pairs": [{"pair": p, "n": int(n)} for p, n in pairs.head(8).items()],
            "top_props": [{"prop_y": p, "n": int(n)} for p, n in prop_y_counts.head(8).items()],
        }

    # 並び順: curves 数の多い順
    out_sorted = dict(sorted(out.items(), key=lambda kv: -kv[1]["curves"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_sorted, ensure_ascii=False, indent=2), encoding="utf-8")

    # 標準出力で要約
    for proj, stats in out_sorted.items():
        print(f"\n=== {proj} ===")
        print(f"  curves: {stats['curves']:,}  /  papers: {stats['papers']:,}  /  compositions: {stats['compositions']:,}")
        print(f"  Top property pairs:")
        for p in stats["top_pairs"][:5]:
            print(f"    {p['pair']:<60} {p['n']:>6,}")


if __name__ == "__main__":
    main()
