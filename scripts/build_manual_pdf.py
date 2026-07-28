#!/usr/bin/env python3
"""
Starrydata2 マニュアル PDF ビルダー
src/manual/*.njk を読み、確認用 PDF を生成する。
出力: docs/Starrydata2_Manual_ja.pdf
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    ListFlowable, ListItem, KeepTogether, Preformatted, Image,
)
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont


# ---- フォント登録 ----
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

FONT_JP = "HeiseiKakuGo-W5"
FONT_JP_MIN = "HeiseiMin-W3"
FONT_MONO = "Courier"

INK = HexColor("#0f172a")
MUTED = HexColor("#64748b")
ACCENT = HexColor("#4f46e5")
LINE = HexColor("#e2e8f0")
WARN_BG = HexColor("#fff7e6")
WARN_BAR = HexColor("#f0b429")
INFO_BG = HexColor("#e8f5e9")
INFO_BAR = HexColor("#43a047")
CODE_BG = HexColor("#0d1b3e")
CODE_FG = HexColor("#e2e8f0")
TABLE_HEAD = HexColor("#eef2ff")


# ---- スタイル ----
H1 = ParagraphStyle(
    "H1", fontName=FONT_JP, fontSize=22, leading=30,
    textColor=INK, spaceBefore=4, spaceAfter=10,
)
EYEBROW = ParagraphStyle(
    "Eyebrow", fontName=FONT_JP_MIN, fontSize=9, leading=12,
    textColor=MUTED, spaceAfter=4,
)
LEAD = ParagraphStyle(
    "Lead", fontName=FONT_JP_MIN, fontSize=11, leading=18,
    textColor=INK, spaceAfter=14,
)
H2 = ParagraphStyle(
    "H2", fontName=FONT_JP, fontSize=15, leading=22,
    textColor=INK, spaceBefore=18, spaceAfter=8,
)
H3 = ParagraphStyle(
    "H3", fontName=FONT_JP, fontSize=12, leading=18,
    textColor=ACCENT, spaceBefore=12, spaceAfter=6,
)
BODY = ParagraphStyle(
    "Body", fontName=FONT_JP_MIN, fontSize=10, leading=17,
    textColor=INK, spaceAfter=8, allowWidows=0, allowOrphans=0,
)
LI = ParagraphStyle(
    "Li", parent=BODY, leftIndent=0, bulletIndent=0,
)
NOTE = ParagraphStyle(
    "Note", fontName=FONT_JP_MIN, fontSize=10, leading=16,
    textColor=INK, spaceAfter=0,
)
CODE = ParagraphStyle(
    "Code", fontName=FONT_MONO, fontSize=8.5, leading=12,
    textColor=CODE_FG, backColor=CODE_BG,
    leftIndent=10, rightIndent=10, spaceBefore=6, spaceAfter=12,
)
TABLE_CELL = ParagraphStyle(
    "TableCell", fontName=FONT_JP_MIN, fontSize=9, leading=14,
    textColor=INK,
)
TABLE_HEAD_CELL = ParagraphStyle(
    "TableHeadCell", fontName=FONT_JP, fontSize=9, leading=14,
    textColor=INK,
)
FIGCAPTION = ParagraphStyle(
    "Figcaption", fontName=FONT_JP_MIN, fontSize=8.5, leading=13,
    textColor=MUTED, alignment=1, spaceBefore=4, spaceAfter=14,
)


# ---- 画像 ----
REPO_ROOT = Path("/Users/atsumitanaka/Documents/starrydata_HP")


def src_to_path(src: str) -> Path:
    """img の src 属性 (/manual/img/...) を src/ 配下の実ファイルに解決。"""
    s = src.lstrip("/")
    return REPO_ROOT / "src" / s


def image_flowable(src: str, max_w: float, max_h: float = 360):
    """src の画像を、最大幅/高さに収まる Image Flowable として返す。"""
    p = src_to_path(src)
    if not p.exists():
        return Paragraph(f"[画像なし: {src}]", BODY)
    ir = ImageReader(str(p))
    iw, ih = ir.getSize()
    scale = min(max_w / iw, max_h / ih, 1.0)
    return Image(str(p), width=iw * scale, height=ih * scale, kind="proportional")


# ---- ユーティリティ ----
def clean_njk(text: str) -> str:
    """njk のフロントマターとテンプレートタグを除去。"""
    text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    text = re.sub(r"\{%-?\s*set\s+[^%]+%\}", "", text)
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    return text


def inline_html(node) -> str:
    """インライン要素を <b>/<i>/<font color> の Paragraph 互換 HTML に。"""
    if isinstance(node, NavigableString):
        return str(node).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    name = node.name
    inner = "".join(inline_html(c) for c in node.children)
    if name in ("strong", "b"):
        return f"<b>{inner}</b>"
    if name in ("em", "i"):
        return f"<i>{inner}</i>"
    if name == "code":
        return f'<font face="{FONT_MONO}" color="#1e293b">{inner}</font>'
    if name == "a":
        href = node.get("href", "")
        return f'<font color="#4f46e5"><u>{inner}</u></font> <font size="7" color="#64748b">({href})</font>'
    if name == "br":
        return "<br/>"
    return inner


def render_block(node, story, doc_width):
    """ブロック要素を Flowable に変換して story に追加。"""
    name = getattr(node, "name", None)

    if name is None:
        text = str(node).strip()
        if text:
            story.append(Paragraph(text, BODY))
        return

    classes = node.get("class", []) or []

    # スキップ: スクリプト・スタイル・空コンテナ
    if name in ("script", "style"):
        return

    # eyebrow （セクション直下の小見出しラベル）
    if "eyebrow" in classes:
        story.append(Paragraph(inline_html(node), EYEBROW))
        return

    if name == "h1":
        story.append(Paragraph(inline_html(node), H1))
        return

    if name == "h2":
        story.append(Paragraph(inline_html(node), H2))
        return

    if name == "h3":
        story.append(Paragraph(inline_html(node), H3))
        return

    if name == "p":
        if "lead" in classes:
            story.append(Paragraph(inline_html(node), LEAD))
        else:
            story.append(Paragraph(inline_html(node), BODY))
        return

    if name in ("ul", "ol"):
        items = []
        for li in node.find_all("li", recursive=False):
            items.append(ListItem(
                Paragraph(inline_html(li), LI),
                leftIndent=12, bulletColor=ACCENT,
            ))
        bullet = "bullet" if name == "ul" else "1"
        story.append(ListFlowable(
            items, bulletType=bullet, start="•" if name == "ul" else "1",
            leftIndent=16, bulletFontName=FONT_JP_MIN, bulletFontSize=9,
        ))
        story.append(Spacer(1, 6))
        return

    if name == "pre":
        code_text = node.get_text("\n")
        # コードブロックは Preformatted で
        story.append(Preformatted(code_text, CODE))
        return

    if name == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            row = []
            for c in cells:
                style = TABLE_HEAD_CELL if c.name == "th" else TABLE_CELL
                row.append(Paragraph(inline_html(c), style))
            rows.append(row)
        if not rows:
            return
        col_count = max(len(r) for r in rows)
        col_w = doc_width / col_count
        t = Table(rows, colWidths=[col_w] * col_count, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))
        return

    # figure / img / figcaption
    if name == "figure":
        img = node.find("img")
        cap = node.find("figcaption")
        if img is not None:
            flow_img = image_flowable(img.get("src", ""), doc_width * 0.85)
            # 中央寄せのためテーブルでラップ
            wrap = Table([[flow_img]], colWidths=[doc_width], hAlign="CENTER")
            wrap.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            block = [wrap]
            if cap is not None:
                block.append(Paragraph(inline_html(cap), FIGCAPTION))
            story.append(KeepTogether(block))
        return

    if name == "img":
        story.append(image_flowable(node.get("src", ""), doc_width * 0.85))
        story.append(Spacer(1, 8))
        return

    # 警告 / 情報ボックス (prose div w/ inline style)
    style_attr = (node.get("style") or "")
    if name == "div" and "border-left:4px solid" in style_attr.replace(" ", ""):
        bg = WARN_BG if "f0b429" in style_attr else INFO_BG
        bar = WARN_BAR if "f0b429" in style_attr else INFO_BAR
        # 中の段落として描画
        inner_paras = []
        for c in node.children:
            if isinstance(c, NavigableString):
                t = str(c).strip()
                if t:
                    inner_paras.append(Paragraph(t, NOTE))
            elif c.name == "br":
                continue
            else:
                inner_paras.append(Paragraph(inline_html(c), NOTE))
        if not inner_paras:
            inner_paras = [Paragraph(inline_html(node), NOTE)]
        box = Table([[inner_paras]], colWidths=[doc_width - 4])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(box)
        story.append(Spacer(1, 10))
        return

    # それ以外のコンテナはネスト走査
    for child in node.children:
        render_block(child, story, doc_width)


def render_file(path: Path, story, doc_width, is_first=False):
    """1 つの njk を Flowable リストに変換。"""
    raw = path.read_text(encoding="utf-8")
    body_html = clean_njk(raw)
    soup = BeautifulSoup(body_html, "html.parser")

    if not is_first:
        story.append(PageBreak())

    # トップレベル <section> 単位で順に処理
    for sec in soup.find_all("section", recursive=False):
        for child in sec.children:
            if isinstance(child, NavigableString):
                continue
            # .container / .container-narrow-prose は素通し
            if child.name == "div" and any(c.startswith("container") for c in (child.get("class") or [])):
                for grand in child.children:
                    if isinstance(grand, NavigableString):
                        continue
                    render_block(grand, story, doc_width)
            else:
                render_block(child, story, doc_width)
        story.append(Spacer(1, 14))


# ---- ヘッダ・フッタ ----
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_JP_MIN, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "Starrydata2 マニュアル（確認用ドラフト）")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"– {doc.page} –")
    canvas.restoreState()


def main():
    repo = Path("/Users/atsumitanaka/Documents/starrydata_HP")
    src_dir = repo / "src" / "manual"
    out_path = repo / "docs" / "Starrydata2_Manual_ja.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = [
        src_dir / "index.njk",
        src_dir / "account.njk",
        src_dir / "search.njk",
        src_dir / "register.njk",
        src_dir / "download.njk",
    ]

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="Starrydata2 マニュアル", author="Starrydata Project",
    )
    doc_width = A4[0] - 40 * mm

    story = []
    for i, f in enumerate(files):
        if not f.exists():
            print(f"WARN missing {f}")
            continue
        render_file(f, story, doc_width, is_first=(i == 0))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"OK -> {out_path}")


if __name__ == "__main__":
    main()
