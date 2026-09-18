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
import re
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
FIGSHARE = "https://api.figshare.com/v2"
FIGSHARE_PROJECT_ID = 155129   # Starrydata datasets プロジェクト
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


TYPE_MAP = {
    # OpenAlex types
    "article": "article",
    "review": "review",
    "preprint": "preprint",
    "book-chapter": "book-chapter",
    "editorial": "editorial",
    "letter": "letter",
    "dataset": "dataset",
    "data-paper": "data-paper",
    "conference-paper": "proceedings",
    "book": "book",
    "report": "report",
    "dissertation": "dissertation",
    "other": "",
    # Crossref types
    "journal-article": "article",
    "review-article": "review",
    "posted-content": "preprint",
    "proceedings-article": "proceedings",
    "reference-entry": "reference",
    "monograph": "book",
}


def normalize_type(t: str) -> str:
    return TYPE_MAP.get((t or "").lower(), (t or "").lower())


def openalex_work_type(work: dict) -> str:
    """OpenAlex work から type を決定。type_crossref も見て review 検出を強化"""
    t = normalize_type(work.get("type") or "")
    if t == "article":
        # type_crossref が review-article なら review に昇格
        tcr = normalize_type(work.get("type_crossref") or "")
        if tcr == "review":
            return "review"
    return t


PREPRINT_HOSTS = {
    "arxiv", "arxiv (cornell university)", "chemrxiv", "biorxiv", "medrxiv",
    "research square", "researchsquare", "ssrn", "techrxiv",
    "hal (le centre pour la communication scientifique directe)", "hal",
    "figshare", "zenodo", "osf preprints",
    "institutional repositories database",
}


def normalize_title(t: str) -> str:
    """タイトルを比較用に正規化（英数字のみ、小文字、先頭 80 文字）"""
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())[:80]


def is_preprint_host(journal: str, work_type: str) -> bool:
    if (work_type or "").lower() == "preprint":
        return True
    j = (journal or "").lower()
    # 括弧内 (e.g. "(IRDB)" や "(Cornell University)") を除去してから比較
    j_stripped = re.sub(r"\s*\([^)]*\)", "", j).strip()
    return j_stripped in PREPRINT_HOSTS or j.strip() in PREPRINT_HOSTS


def extract_countries(work: dict) -> list[str]:
    """OpenAlex work から著者所属機関の country_code をユニーク抽出（大文字 ISO α-2）"""
    seen: dict[str, None] = {}
    for a in (work.get("authorships") or []):
        for c in (a.get("countries") or []):
            if c:
                seen.setdefault(c.upper(), None)
        for inst in (a.get("institutions") or []):
            c = inst.get("country_code") or ""
            if c:
                seen.setdefault(c.upper(), None)
    return list(seen.keys())


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
        "work_type": openalex_work_type(work),
        "countries": extract_countries(work),
    }


def fetch_seed(doi: str) -> dict | None:
    """seed DOI から OpenAlex work を取得"""
    url = f"{OPENALEX}/works/https://doi.org/{urllib.parse.quote(doi, safe='/.')}"
    try:
        return get_json(url, attach_mailto=True)
    except Exception as e:
        print(f"WARN: seed not found for {doi}: {e}", file=sys.stderr)
        return None


def fetch_openalex_fulltext(query: str) -> list[dict]:
    """OpenAlex 全文検索。dataset / paratext を除外し、work を返す"""
    out: list[dict] = []
    cursor = "*"
    while True:
        params = {
            "search": query,
            "per-page": "200",
            "cursor": cursor,
            "select": "id,doi,title,display_name,publication_year,biblio,primary_location,authorships,cited_by_count,type,type_crossref",
        }
        url = f"{OPENALEX}/works?" + urllib.parse.urlencode(params)
        try:
            data = get_json(url, attach_mailto=True)
        except Exception as e:
            print(f"WARN: fulltext search failed for '{query}': {e}", file=sys.stderr)
            break
        for w in data.get("results", []):
            t = (w.get("type") or "").lower()
            # figshare スナップショット等の dataset や目次的な paratext は除外
            if t in ("dataset", "paratext"):
                continue
            out.append(w)
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.2)
    return out


def fetch_cited_by_openalex(work_id: str) -> list[dict]:
    """OpenAlex で指定 work を引用している論文を全件取得（cursor pagination）"""
    out = []
    cursor = "*"
    while True:
        params = {
            "filter": f"cites:{work_id}",
            "per-page": "200",
            "cursor": cursor,
            "select": "id,doi,title,display_name,publication_year,biblio,primary_location,authorships,cited_by_count,type,type_crossref,institutions_distinct_count",
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


def fetch_figshare_dataset_dois() -> list[dict]:
    """figshare project 155129 (Starrydata datasets) の全 dataset を取得"""
    url = f"{FIGSHARE}/projects/{FIGSHARE_PROJECT_ID}/articles?page_size=1000"
    try:
        arts = get_json(url)
    except Exception as e:
        print(f"WARN: figshare fetch failed: {e}", file=sys.stderr)
        return []
    out = []
    for a in arts:
        doi = a.get("doi") or ""
        if not doi:
            continue
        # 末尾の .vN を取り除いた canonical DOI も保持
        canonical = re.sub(r"\.v\d+$", "", doi)
        out.append({
            "doi": doi,
            "doi_canonical": canonical,
            "title": a.get("title") or "",
            "published_date": (a.get("published_date") or "")[:10],
            "figshare_id": a.get("id"),
        })
    return out


def fetch_crossref_count(doi: str) -> int | None:
    """Crossref の is-referenced-by-count を取得（出版社サイトと同じ引用数）"""
    url = f"{CROSSREF}/works/{urllib.parse.quote(doi, safe='/.')}"
    try:
        data = get_json(url, attach_mailto=True)
    except Exception as e:
        print(f"WARN: Crossref count miss for {doi}: {e}", file=sys.stderr)
        return None
    msg = data.get("message") or {}
    return msg.get("is-referenced-by-count")


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
        "work_type": normalize_type(msg.get("type") or ""),
        "countries": [],
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

    # --- 各 seed の Crossref 引用数（出版社サイトに表示されるのと同じソース）---
    for project in project_papers:
        doi = project.get("doi", "")
        if not doi:
            continue
        cnt = fetch_crossref_count(doi)
        if cnt is not None:
            # OpenAlex 由来の cited_by_count を Crossref で上書き
            project["cited_by_count_openalex"] = project.get("cited_by_count", 0)
            project["cited_by_count"] = cnt
            project["cited_by_source"] = "crossref"
        time.sleep(0.1)

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

    # --- (3.3) OpenAlex 全文検索で "starrydata" を含む論文を検出 ---
    # → figshare データセット経由で Starrydata を使っているが seed 引用が薄い/無い論文を拾う
    print("[OpenAlex] fulltext search 'starrydata' ...")
    mention_works = fetch_openalex_fulltext("starrydata")
    print(f"  -> {len(mention_works)} works mention 'starrydata'")
    n_new = 0
    n_existing = 0
    for w in mention_works:
        paper = extract_paper(w)
        doi_l = (paper["doi"] or "").lower()
        if not doi_l or doi_l in seed_doi_set:
            continue
        if doi_l in citing_by_doi:
            citing_by_doi[doi_l]["sources"].add("openalex-fulltext")
            n_existing += 1
        else:
            citing_by_doi[doi_l] = {
                "paper": paper,
                "sources": {"openalex-fulltext"},
                "cites_seeds": set(),
            }
            n_new += 1
        citing_by_doi[doi_l]["mentions_starrydata"] = True
    print(f"  -> {n_existing} already tracked, {n_new} newly added")

    # --- (3.4) 重複除外: seed の preprint 版と、published + preprint 両方が citing_papers に居るケースをまとめる ---
    seed_titles_norm = {
        normalize_title(p.get("title") or ""): (p.get("doi") or "").lower()
        for p in project_papers
    }

    # 3.4a: seed と同じタイトルの preprint/dataset を citing から除外（seed 自身の別バージョン）
    skipped_seed_variants = 0
    for doi_l in list(citing_by_doi.keys()):
        entry = citing_by_doi[doi_l]
        p = entry["paper"]
        t_norm = normalize_title(p.get("title"))
        if t_norm and t_norm in seed_titles_norm and is_preprint_host(p.get("journal"), p.get("work_type")):
            del citing_by_doi[doi_l]
            skipped_seed_variants += 1
    if skipped_seed_variants:
        print(f"[dedupe] seed preprint/dataset variants: dropped {skipped_seed_variants}")

    # 3.4b: 正規化タイトルが同じ複数エントリで、preprint と published が両方あれば preprint を落とす。
    #       その際、preprint 側の cites_seeds と mentions_starrydata フラグを published 側にマージ。
    from collections import defaultdict
    by_title: dict[str, list[str]] = defaultdict(list)
    for doi_l, entry in citing_by_doi.items():
        t = normalize_title(entry["paper"].get("title"))
        if t:
            by_title[t].append(doi_l)
    dedup_dropped = 0
    for t, dois in by_title.items():
        if len(dois) < 2:
            continue
        preprints = [d for d in dois if is_preprint_host(
            citing_by_doi[d]["paper"].get("journal"),
            citing_by_doi[d]["paper"].get("work_type"),
        )]
        published = [d for d in dois if d not in preprints]
        if not preprints or not published:
            continue
        # published 側 (最初の1件) にマージして preprint を落とす
        keeper = citing_by_doi[published[0]]
        for pd in preprints:
            pe = citing_by_doi[pd]
            keeper["cites_seeds"] |= pe.get("cites_seeds", set())
            keeper["sources"] |= pe.get("sources", set())
            if pe.get("mentions_starrydata"):
                keeper["mentions_starrydata"] = True
            del citing_by_doi[pd]
            dedup_dropped += 1
    if dedup_dropped:
        print(f"[dedupe] preprint duplicates of published papers: dropped {dedup_dropped}")

    # --- (3.5) サニティフィルタ: blocklist / 時系列矛盾を除外 ---
    blocklist = {d.lower() for d in seeds_doc.get("blocklist", [])}
    seed_year_by_doi = {
        (p.get("doi") or "").lower(): p.get("year")
        for p in project_papers if p.get("doi")
    }

    skipped_blocklist = 0
    skipped_time_inconsistent: list[tuple[str, int, str, int]] = []
    filtered: dict[str, dict] = {}
    for doi_l, entry in citing_by_doi.items():
        if doi_l in blocklist:
            skipped_blocklist += 1
            continue
        citing_year = entry["paper"].get("year")
        valid_seeds = set()
        for seed_doi in entry["cites_seeds"]:
            seed_year = seed_year_by_doi.get(seed_doi.lower())
            if citing_year and seed_year and citing_year < seed_year:
                skipped_time_inconsistent.append(
                    (doi_l, citing_year, seed_doi, seed_year)
                )
                continue
            valid_seeds.add(seed_doi)
        # seed 引用が全滅した場合でも、"starrydata" fulltext hit なら残す
        if not valid_seeds and not entry.get("mentions_starrydata"):
            continue
        entry["cites_seeds"] = valid_seeds
        filtered[doi_l] = entry
    citing_by_doi = filtered

    if skipped_blocklist:
        print(f"[filter] blocklist: dropped {skipped_blocklist} paper(s)")
    if skipped_time_inconsistent:
        print(f"[filter] time-inconsistent: dropped {len(skipped_time_inconsistent)} (citing_year < seed_year)")
        for doi_l, cy, sd, sy in skipped_time_inconsistent:
            print(f"    - {doi_l} ({cy}) claims to cite {sd} ({sy})")

    # 各 seed の unique 件数をフィルタ後の値で上書き
    for project in project_papers:
        seed_doi = project.get("doi") or ""
        project["citation_counts"]["unique"] = sum(
            1 for entry in citing_by_doi.values() if seed_doi in entry["cites_seeds"]
        )

    # --- (3.7) 活用度判定: featured/unfeatured リスト + cites_seeds 件数 ---
    featured_manual = {d.lower() for d in seeds_doc.get("featured_dois", [])}
    unfeatured_manual = {d.lower() for d in seeds_doc.get("unfeatured_dois", [])}

    def compute_usage_tier(doi_l: str, entry: dict) -> str:
        if doi_l in unfeatured_manual:
            return "regular"
        if doi_l in featured_manual:
            return "heavy"
        # 自動判定 (a): 本文で "starrydata" を言及していれば heavy（figshare 経由ユーザー等）
        if entry.get("mentions_starrydata"):
            return "heavy"
        # 自動判定 (b): 2 本以上の seed を引用していれば heavy
        if len(entry["cites_seeds"]) >= 2:
            return "heavy"
        return "regular"

    # --- (4) 出力用配列に整形 ---
    citing_papers = []
    for doi_l, entry in citing_by_doi.items():
        p = entry["paper"]
        p["sources"] = sorted(entry["sources"])
        p["cites_seeds"] = sorted(entry["cites_seeds"])
        p["mentions_starrydata"] = bool(entry.get("mentions_starrydata"))
        p["usage_tier"] = compute_usage_tier(doi_l, entry)
        citing_papers.append(p)

    # 新しい順
    citing_papers.sort(key=lambda p: (p.get("year") or 0, p.get("cited_by_count") or 0), reverse=True)

    # 国別に集計（citing_paper に少なくとも 1 人の著者が所属している国をカウント）
    citations_by_country: dict[str, int] = {}
    for p in citing_papers:
        for c in p.get("countries") or []:
            citations_by_country[c] = citations_by_country.get(c, 0) + 1
    citations_by_country_sorted = sorted(
        citations_by_country.items(), key=lambda kv: kv[1], reverse=True
    )
    citations_by_country_list = [
        {"country_code": code, "count": n} for code, n in citations_by_country_sorted
    ]
    citing_papers_with_country = sum(1 for p in citing_papers if p.get("countries"))

    # 活用度別に分割
    heavy_papers = [p for p in citing_papers if p.get("usage_tier") == "heavy"]
    regular_papers = [p for p in citing_papers if p.get("usage_tier") != "heavy"]

    def group_by_year(papers: list[dict]) -> list[dict]:
        by_year: dict[int, list[dict]] = {}
        for p in papers:
            by_year.setdefault(p.get("year") or 0, []).append(p)
        return [
            {"year": y if y else None, "count": len(by_year[y]), "papers": by_year[y]}
            for y in sorted(by_year.keys(), reverse=True)
        ]

    citing_papers_by_year = group_by_year(citing_papers)
    heavy_papers_by_year = group_by_year(heavy_papers)
    regular_papers_by_year = group_by_year(regular_papers)

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
        "citations_by_country": citations_by_country_list,
        "citing_papers_with_country_count": citing_papers_with_country,
        "heavy_papers_count": len(heavy_papers),
        "regular_papers_count": len(regular_papers),
        "project_papers": project_papers,
        "citing_papers": citing_papers,
        "citing_papers_by_year": citing_papers_by_year,
        "heavy_papers_by_year": heavy_papers_by_year,
        "regular_papers_by_year": regular_papers_by_year,
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
    print(f"citing_papers with country info: {citing_papers_with_country} / {len(citing_papers)}")
    print(f"countries: {len(citations_by_country_list)}")
    for c in citations_by_country_list[:10]:
        print(f"  {c['country_code']}: {c['count']}")


if __name__ == "__main__":
    main()
