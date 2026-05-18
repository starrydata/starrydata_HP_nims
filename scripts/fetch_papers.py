"""
論文情報を OpenAlex + OpenCitations の併用で取得し src/_data/papers.json を更新する。

引用情報の取り方:
- OpenAlex      : seed の cited_by_count + 全 citing works の詳細メタデータ
- OpenCitations : Crossref Open Citations（COCI）の被引用 DOI リスト
- 不足分は Crossref からメタデータ補完（OpenAlex に未登録の論文）

入力: src/_data/starrydata_seeds.json
  - seeds: Starrydata プロジェクトの代表論文の DOI リスト

出力: src/_data/papers.json
  - project_papers: seed 論文の最新メタデータ
  - citing_papers : seed 論文を引用している外部論文（重複排除、新しい順）
                    各論文に "sources" フィールド: ["openalex"] / ["opencitations"] / ["openalex","opencitations"]

エンドポイント:
- OpenAlex 論文:    GET https://api.openalex.org/works/https://doi.org/{doi}
- OpenAlex 被引用:  GET https://api.openalex.org/works?filter=cites:{work_id}
- OpenCitations:    GET https://api.opencitations.net/index/v2/citations/doi:{doi}
- Crossref 補完:    GET https://api.crossref.org/works/{doi}

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

OPENALEX = "https://api.openalex.org"
OPENCITATIONS = "https://api.opencitations.net/index/v2"
CROSSREF = "https://api.crossref.org"
MAILTO = "starrydata1@gmail.com"


def get_json(url: str, headers: dict | None = None, attach_mailto: bool = False) -> dict:
    if attach_mailto:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}mailto={urllib.parse.quote(MAILTO)}"
    h = {"User-Agent": f"starrydata-hp/1.0 (mailto:{MAILTO})"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_doi_from_omid(s: str) -> str:
    """'omid:br/xxx doi:10.x/y openalex:Wxxx' から DOI を抽出"""
    for tok in (s or "").split():
        if tok.startswith("doi:"):
            return tok[4:]
    return ""


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
    url = f"{OPENALEX}/works/https://doi.org/{urllib.parse.quote(doi, safe='/.')}"
    try:
        return get_json(url, attach_mailto=True)
    except Exception as e:
        print(f"WARN: seed not found for {doi}: {e}", file=sys.stderr)
        return None


def fetch_cited_by_openalex(work_id: str) -> list[dict]:
    """OpenAlex で指定 work を引用している論文を全件取得（cursor pagination）"""
    out = []
    cursor = "*"
    while True:
        params = {
            "filter": f"cites:{work_id}",
            "per-page": "200",
            "cursor": cursor,
            "select": "id,doi,title,display_name,publication_year,biblio,primary_location,authorships,cited_by_count",
        }
        url = f"{OPENALEX}/works?" + urllib.parse.urlencode(params)
        data = get_json(url, attach_mailto=True)
        out.extend(data.get("results", []))
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.2)
    return out


def fetch_cited_by_opencitations(doi: str) -> list[str]:
    """OpenCitations で被引用 DOI のリストを取得"""
    url = f"{OPENCITATIONS}/citations/doi:{urllib.parse.quote(doi, safe='/.')}"
    try:
        data = get_json(url)
    except Exception as e:
        print(f"WARN: OpenCitations failed for {doi}: {e}", file=sys.stderr)
        return []
    dois = []
    for c in data:
        d = extract_doi_from_omid(c.get("citing", ""))
        if d:
            dois.append(d.lower())
    return dois


def fetch_crossref_meta(doi: str) -> dict | None:
    """Crossref から論文メタデータを取得"""
    url = f"{CROSSREF}/works/{urllib.parse.quote(doi, safe='/.')}"
    try:
        data = get_json(url, attach_mailto=True)
    except Exception as e:
        print(f"WARN: Crossref miss for {doi}: {e}", file=sys.stderr)
        return None
    msg = data.get("message") or {}
    title = (msg.get("title") or [""])[0]
    authors = ", ".join(
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in (msg.get("author") or [])
    )
    journal = (msg.get("container-title") or [""])[0]
    issued = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0]
    year = issued[0] if issued else None
    page = msg.get("page") or ""
    if "-" in page:
        start_page, end_page = page.split("-", 1)
    else:
        start_page, end_page = page, ""
    return {
        "openalex_id": "",
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "volume": msg.get("volume") or "",
        "issue": msg.get("issue") or "",
        "start_page": start_page,
        "end_page": end_page,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "cited_by_count": msg.get("is-referenced-by-count", 0),
    }


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

    # ===== 引用論文の集約（DOI をキーに重複排除） =====
    # citing_by_doi[doi] -> {"paper": {...}, "sources": set, "cites_seeds": set}
    citing_by_doi: dict[str, dict] = {}
    seed_doi_set = {d.lower() for d in seed_dois}

    def merge_paper(doi_lower: str, paper: dict, source: str, seed_doi: str):
        if not doi_lower:
            return
        if doi_lower in seed_doi_set:
            return  # seed 同士は除外
        if doi_lower not in citing_by_doi:
            citing_by_doi[doi_lower] = {
                "paper": paper,
                "sources": set(),
                "cites_seeds": set(),
            }
        entry = citing_by_doi[doi_lower]
        entry["sources"].add(source)
        entry["cites_seeds"].add(seed_doi)
        # メタデータが不足している場合は補完
        existing = entry["paper"]
        for k, v in paper.items():
            if not existing.get(k) and v:
                existing[k] = v

    # --- (1) OpenAlex から取得 ---
    # 各 seed の citing papers 件数を記録
    for project in project_papers:
        project["citation_counts"] = {
            "openalex": 0,
            "opencitations": 0,
            "unique": 0,        # 後で計算（重複排除後）
        }
        project["citing_dois_oa"] = set()
        project["citing_dois_oc"] = set()

    for project in project_papers:
        wid = project["openalex_id"]
        if not wid:
            continue
        print(f"[OpenAlex] cited_by {wid} ({project['doi']}) ...")
        cites = fetch_cited_by_openalex(wid)
        print(f"  -> {len(cites)} citing works")
        project["citation_counts"]["openalex"] = len(cites)
        for w in cites:
            paper = extract_paper(w)
            doi_l = (paper["doi"] or "").lower()
            if doi_l:
                merge_paper(doi_l, paper, "openalex", project["doi"])
                if doi_l not in seed_doi_set:
                    project["citing_dois_oa"].add(doi_l)

    # --- (2) OpenCitations から取得（不足を埋める） ---
    new_dois_from_oc: dict[str, str] = {}  # doi -> seed_doi
    for project in project_papers:
        seed_doi = project["doi"]
        if not seed_doi:
            continue
        print(f"[OpenCitations] citations of {seed_doi} ...")
        oc_dois = fetch_cited_by_opencitations(seed_doi)
        print(f"  -> {len(oc_dois)} citing DOIs")
        project["citation_counts"]["opencitations"] = len(oc_dois)
        for d in oc_dois:
            if d in seed_doi_set:
                continue
            project["citing_dois_oc"].add(d)
            if d in citing_by_doi:
                citing_by_doi[d]["sources"].add("opencitations")
                citing_by_doi[d]["cites_seeds"].add(seed_doi)
            else:
                new_dois_from_oc[d] = seed_doi
        time.sleep(0.2)

    # 各 seed のユニーク件数を確定し、内部用フィールドを削除
    for project in project_papers:
        union = project["citing_dois_oa"] | project["citing_dois_oc"]
        project["citation_counts"]["unique"] = len(union)
        # 内部一時フィールドを削除
        del project["citing_dois_oa"]
        del project["citing_dois_oc"]

    # --- (3) OpenCitations のみで見つかった DOI を Crossref で補完 ---
    if new_dois_from_oc:
        print(f"[Crossref] enriching {len(new_dois_from_oc)} new DOIs ...")
    for doi, seed_doi in new_dois_from_oc.items():
        meta = fetch_crossref_meta(doi)
        if meta:
            merge_paper(doi, meta, "opencitations", seed_doi)
        time.sleep(0.1)

    # --- (4) 出力用配列に整形 ---
    citing_papers = []
    for doi_l, entry in citing_by_doi.items():
        p = entry["paper"]
        p["sources"] = sorted(entry["sources"])
        p["cites_seeds"] = sorted(entry["cites_seeds"])
        citing_papers.append(p)

    # 新しい順
    citing_papers.sort(key=lambda p: (p.get("year") or 0, p.get("cited_by_count") or 0), reverse=True)

    jst = timezone(timedelta(hours=9))
    out = {
        "description": "Starrydata プロジェクト関連論文（seed）と、それらを引用している外部論文",
        "fetched_at": datetime.now(jst).isoformat(timespec="seconds"),
        "data_sources": [
            "OpenAlex (https://openalex.org)",
            "OpenCitations / Crossref Open Citations (https://opencitations.net)",
        ],
        "researcher": "Yukari Katsura and the Starrydata team",
        "project_papers_count": len(project_papers),
        "citing_papers_count": len(citing_papers),
        "citing_papers_by_source": {
            "openalex_only": sum(1 for p in citing_papers if p["sources"] == ["openalex"]),
            "opencitations_only": sum(1 for p in citing_papers if p["sources"] == ["opencitations"]),
            "both": sum(1 for p in citing_papers if len(p["sources"]) == 2),
        },
        "project_papers": project_papers,
        "citing_papers": citing_papers,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"project_papers: {len(project_papers)}")
    print(f"{'YEAR':5}{'DOI':38}{'OA':>5}{'OC':>5}{'UNI':>5}  TITLE")
    sum_oa = sum_oc = sum_uni = 0
    for p in project_papers:
        c = p["citation_counts"]
        sum_oa += c["openalex"]
        sum_oc += c["opencitations"]
        sum_uni += c["unique"]
        print(f"  {p['year'] or '----':4} {p['doi']:38}{c['openalex']:>5}{c['opencitations']:>5}{c['unique']:>5}  {p['title'][:50]}")
    print(f"  {'':4} {'(sum incl. duplicates)':38}{sum_oa:>5}{sum_oc:>5}{sum_uni:>5}")
    print(f"  {'':4} {'(unique across all seeds)':38}{'':>5}{'':>5}{len(citing_papers):>5}")
    print()
    print(f"citing_papers (unique): {len(citing_papers)}")


if __name__ == "__main__":
    main()
