"""
OpenAlex API から論文情報を取得し、src/_data/papers.json を更新する。

入力: src/_data/starrydata_seeds.json
  - seeds: Starrydata プロジェクトの代表論文の DOI リスト

出力: src/_data/papers.json
  - project_papers: seed 論文の最新メタデータ（年・タイトル・著者・ジャーナル・DOI 等）
  - citing_papers : seed 論文を引用している外部論文（重複排除、新しい順）

API:
- 論文取得:   GET https://api.openalex.org/works/https://doi.org/{doi}
- 被引用取得: GET https://api.openalex.org/works?filter=cites:{work_id}&per-page=200&cursor=*

OpenAlex は無料・認証不要だが、mailto を指定すると polite pool に入る（速い・安定）。

GitHub Actions で毎月 1 日に自動実行することを想定。
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEDS_FILE = ROOT / "src/_data/starrydata_seeds.json"
OUT_FILE = ROOT / "src/_data/papers.json"

API = "https://api.openalex.org"
MAILTO = "starrydata1@gmail.com"


def get_json(url: str) -> dict:
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}mailto={urllib.parse.quote(MAILTO)}"
    req = urllib.request.Request(full, headers={"User-Agent": "starrydata-hp/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_paper(work: dict) -> dict:
    """OpenAlex work オブジェクトから表示用フィールドを抽出"""
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    title = work.get("title") or work.get("display_name") or ""
    year = work.get("publication_year")
    biblio = work.get("biblio") or {}
    venue = (work.get("primary_location") or {}).get("source") or {}
    journal = venue.get("display_name") or ""

    authorships = work.get("authorships") or []
    authors = ", ".join(a["author"]["display_name"] for a in authorships)

    # OpenAlex work id (W123456789)
    work_id = (work.get("id") or "").rsplit("/", 1)[-1]

    return {
        "openalex_id": work_id,
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "volume": biblio.get("volume") or "",
        "issue": biblio.get("issue") or "",
        "start_page": biblio.get("first_page") or "",
        "end_page": biblio.get("last_page") or "",
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "cited_by_count": work.get("cited_by_count", 0),
    }


def fetch_seed(doi: str) -> dict | None:
    """seed DOI から OpenAlex work を取得"""
    url = f"{API}/works/https://doi.org/{urllib.parse.quote(doi, safe='/.')}"
    try:
        return get_json(url)
    except Exception as e:
        print(f"WARN: seed not found for {doi}: {e}", file=sys.stderr)
        return None


def fetch_cited_by(work_id: str) -> list[dict]:
    """指定 work を引用している論文を全件取得（cursor pagination）"""
    out = []
    cursor = "*"
    while True:
        params = {
            "filter": f"cites:{work_id}",
            "per-page": "200",
            "cursor": cursor,
            "select": "id,doi,title,display_name,publication_year,biblio,primary_location,authorships,cited_by_count",
        }
        url = f"{API}/works?" + urllib.parse.urlencode(params)
        data = get_json(url)
        out.extend(data.get("results", []))
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.2)
    return out


def main():
    seeds_doc = json.loads(SEEDS_FILE.read_text(encoding="utf-8"))
    seed_dois = seeds_doc.get("seeds", [])
    print(f"Seeds: {len(seed_dois)}")

    project_papers = []
    seed_work_ids = []

    for doi in seed_dois:
        work = fetch_seed(doi)
        if not work:
            continue
        project_papers.append(extract_paper(work))
        wid = (work.get("id") or "").rsplit("/", 1)[-1]
        if wid:
            seed_work_ids.append(wid)
        time.sleep(0.3)

    project_papers.sort(key=lambda p: (p.get("year") or 0), reverse=True)

    # 被引用論文を集約（重複排除: openalex_id ベース）
    citing_by_id: dict[str, dict] = {}
    cited_seeds: dict[str, list[str]] = {}  # citing_paper_id -> [cited seed DOIs]
    for wid in seed_work_ids:
        print(f"Fetching cited_by for {wid} ...")
        cites = fetch_cited_by(wid)
        print(f"  -> {len(cites)} citing works")
        seed_doi = next((p["doi"] for p in project_papers if p["openalex_id"] == wid), "")
        for w in cites:
            wid_cit = (w.get("id") or "").rsplit("/", 1)[-1]
            if not wid_cit:
                continue
            if wid_cit not in citing_by_id:
                citing_by_id[wid_cit] = extract_paper(w)
                cited_seeds[wid_cit] = []
            cited_seeds[wid_cit].append(seed_doi)

    # 引用元 seed の DOI を埋め込む
    citing_papers = []
    for wid_cit, paper in citing_by_id.items():
        paper["cites_seeds"] = cited_seeds[wid_cit]
        citing_papers.append(paper)

    # 自プロジェクト論文は除外（seed 論文同士が引用し合っているケース）
    seed_doi_set = {d.lower() for d in seed_dois}
    citing_papers = [p for p in citing_papers if (p["doi"] or "").lower() not in seed_doi_set]

    # 新しい順
    citing_papers.sort(key=lambda p: (p.get("year") or 0, p.get("cited_by_count") or 0), reverse=True)

    jst = timezone(timedelta(hours=9))
    out = {
        "description": "Starrydata プロジェクト関連論文（seed）と、それらを引用している外部論文",
        "fetched_at": datetime.now(jst).isoformat(timespec="seconds"),
        "data_source": "OpenAlex (https://openalex.org)",
        "researcher": "Yukari Katsura and the Starrydata team",
        "project_papers_count": len(project_papers),
        "citing_papers_count": len(citing_papers),
        "project_papers": project_papers,
        "citing_papers": citing_papers,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"project_papers: {len(project_papers)}")
    for p in project_papers:
        print(f"  {p['year']}  {p['doi']:35}  {p['title'][:60]}")
    print()
    print(f"citing_papers : {len(citing_papers)}")
    for p in citing_papers[:10]:
        print(f"  {p['year']}  {p['doi']:35}  {p['title'][:60]}")
    if len(citing_papers) > 10:
        print(f"  ... and {len(citing_papers) - 10} more")


if __name__ == "__main__":
    main()
