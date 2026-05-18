"""
papers の 24 記事を構造化 JSON に変換する。

各論文は表形式（タイトル/著者名/出版年/出版物名/DOI/Open Access）または
画像+リンク形式で記載されている。両方をサポート。

スキーマ:
{
  "papers": [
    {
      "id": "40",
      "slug": "weighted_mobility",
      "title": "Weighted Mobility",
      "title_original": "...",            # MT のエントリタイトル
      "url": "https://...",
      "authors": "Snyder, G.J., ...",
      "year": "2020",
      "journal": "Advanced Materials",
      "doi": "10.1002/adma.202001537",
      "open_access": "All Open Access, Green",
      "thumbnail": "/papers/.../*.png",   // 画像形式の場合
      "date": "2020-06-24",
      "datetime": "2020-06-24T00:00:00+09:00",
      "comment_html": "",                 // 表の後にあるコメント本文
      "raw_html": "..."                   // 元の text 全体（変換できなかった項目用）
    }
  ]
}
"""

import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "_source/extracted/entries/papers"
DST = ROOT / "src/_data/papers.json"


LABEL_MAP = {
    "タイトル": "title",
    "著者名": "authors",
    "出版年": "year",
    "出版物名": "journal",
    "doi": "doi",
    "open access": "open_access",
}


class TableParser(HTMLParser):
    """論文記事の <table> 内の <tr><td>label</td><td>value</td></tr> をパースする"""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_tr = False
        self.cells = []       # 現在の tr の td テキスト/HTML
        self.buf = []
        self.capture = False
        self.rows = []        # [(label, value_text, value_html_links)]
        self.last_a_href = None
        self.cell_links = []  # [(label, href)] そのセル内のリンク

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_tr = True
            self.cells = []
            self.cell_links = []
        elif tag == "td" and self.in_tr:
            self.capture = True
            self.buf = []
            self.cur_cell_links = []
        elif tag == "a" and self.capture:
            href = dict(attrs).get("href", "")
            self.cur_cell_links.append({"href": href})
            self.buf.append(("__a_start__", href))
        elif tag == "br" and self.capture:
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            if len(self.cells) >= 2:
                label = self._cell_text(self.cells[0]["buf"]).strip().lower()
                value = self._cell_text(self.cells[1]["buf"]).strip()
                links = self.cells[1].get("links", [])
                self.rows.append({"label": label, "value": value, "links": links})
        elif tag == "td" and self.capture:
            self.cells.append({"buf": self.buf, "links": self.cur_cell_links})
            self.capture = False
        elif tag == "a" and self.capture:
            # リンクの中身を確定して末端マーカーを置く
            self.buf.append("__a_end__")

    def handle_data(self, data):
        if self.capture:
            self.buf.append(data)

    def _cell_text(self, buf):
        text_parts = []
        link_text_buf = []
        in_link = False
        cur_href = None
        for piece in buf:
            if isinstance(piece, tuple) and piece[0] == "__a_start__":
                in_link = True
                cur_href = piece[1]
                link_text_buf = []
            elif piece == "__a_end__":
                if in_link:
                    text_parts.append("".join(link_text_buf))
                in_link = False
            else:
                if in_link:
                    link_text_buf.append(piece)
                else:
                    text_parts.append(piece)
        return "".join(text_parts)


def parse_paper_table(html: str) -> dict:
    """論文記事の表をパースして辞書で返す。リンクも抽出。"""
    parser = TableParser()
    parser.feed(html)
    out = {}
    for row in parser.rows:
        label_key = LABEL_MAP.get(row["label"])
        if not label_key:
            continue
        out[label_key] = row["value"]
        # タイトルセルのリンクは url として保存
        if label_key == "title" and row["links"]:
            out["url"] = row["links"][0]["href"]
    return out


def parse_paper_image_form(html: str) -> dict:
    """表が無い形式：<a href="..."><img src="..."></a>"""
    out = {}
    # 最初の <a href="..."> のURL
    m = re.search(r'<a href="([^"]+)"[^>]*>\s*<img[^>]*src="([^"]+)"', html)
    if m:
        out["url"] = m.group(1)
        out["thumbnail"] = m.group(2)
    return out


def parse_mt_date(s: str) -> tuple[str, str]:
    if not s or len(s) < 8:
        return "", ""
    try:
        dt = datetime.strptime(s, "%Y%m%d%H%M%S")
    except ValueError:
        try:
            dt = datetime.strptime(s, "%Y%m%d")
        except ValueError:
            return "", ""
    return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%dT%H:%M:%S+09:00")


def extract_comment_after_table(html: str) -> str:
    """</table> の後にあるコメント部分を抽出"""
    m = re.search(r'</table>\s*(.*)$', html, re.S)
    if not m:
        return ""
    rest = m.group(1).strip()
    return rest


def main():
    papers = []
    for jf in sorted(SRC_DIR.glob("*.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        html = (d.get("text") or "")
        more = (d.get("text_more") or "").strip()
        date, iso = parse_mt_date(d.get("authored_on", ""))

        rec = {
            "id": d["id"],
            "slug": d["basename"],
            "title": d["title"],
            "title_original": d["title"],
            "url": "",
            "authors": "",
            "year": "",
            "journal": "",
            "doi": "",
            "open_access": "",
            "thumbnail": "",
            "date": date,
            "datetime": iso,
            "comment_html": "",
            "raw_html": html,
        }

        if "<table" in html:
            parsed = parse_paper_table(html)
            for k, v in parsed.items():
                if v:
                    rec[k] = v
            rec["comment_html"] = extract_comment_after_table(html)
        else:
            parsed = parse_paper_image_form(html)
            for k, v in parsed.items():
                if v:
                    rec[k] = v

        # title が表内のセルから取れた場合はそちらを採用
        # （title_original は MT のエントリタイトル）
        # text_more があれば comment に追加
        if more:
            rec["comment_html"] = (rec["comment_html"] + "\n" + more).strip()

        papers.append(rec)

    # 出版年→authored_on の順で新しい順に並べる
    papers.sort(
        key=lambda x: (x.get("year") or "", x.get("datetime") or ""),
        reverse=True,
    )

    DST.write_text(
        json.dumps({"papers": papers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"papers: {len(papers)}")
    print()
    print(f"{'YEAR':6}{'DOI':30}{'TITLE'}")
    for p in papers:
        title = (p['title'] or '')[:60]
        print(f"{p['year']:6}{p['doi']:30}{title}")


if __name__ == "__main__":
    main()
