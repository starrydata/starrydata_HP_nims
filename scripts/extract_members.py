"""
project/members ページの本文 HTML を解析し、構造化 JSON を生成する。

入力: _source/extracted/pages/project/12__members.json
出力: src/_data/members.json

スキーマ:
{
  "groups": [
    {
      "key": "primary",
      "label": "コアメンバー",
      "members": [
        {
          "name_ja": "桂 ゆかり",
          "name_en": "Yukari Katsura",
          "role": "プロジェクトリーダー",
          "photo": "/project/img/profile_katsura.jpg",
          "affiliation": "...",     // 改行は \n
          "links": [{"label":"Twitter","href":"..."}]
        }
      ]
    },
    {"key": "secondary", "label": "メンバー", "members": [...]}
  ]
}
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_source/extracted/pages/project/12__members.json"
DST = ROOT / "src/_data/members.json"


class MembersParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []          # 開いている要素のスタック (tag, attrs)
        self.cur_group = None    # "primary" | "secondary"
        self.cur_member = None
        self.cur_field = None    # "h3" | "h4" | "career" | "link_label"
        self.cur_link_href = None
        self.groups = {"primary": [], "secondary": []}
        self.buf = []

    def _classes(self, attrs):
        d = dict(attrs)
        return d.get("class", "").split()

    def handle_starttag(self, tag, attrs):
        classes = self._classes(attrs)
        d = dict(attrs)

        if tag == "div":
            if "primary-members" in classes:
                self.cur_group = "primary"
            elif "secondary-members" in classes:
                self.cur_group = "secondary"
            elif "area_members" in classes and self.cur_group is not None:
                self.cur_member = {
                    "name_ja": "", "name_en": "", "role": "",
                    "photo": "", "affiliation": "", "links": [],
                }
            elif "career" in classes and self.cur_member is not None:
                self.cur_field = "career"
                self.buf = []
        elif tag == "img" and self.cur_member is not None and not self.cur_member["photo"]:
            # 最初の img をプロフィール写真として採用（飾り画像は無視）
            src = d.get("src", "")
            cls = classes
            if "members_img_01" not in cls and "members_img_02" not in cls:
                # 相対 "img/..." を /project/img/... に変換
                if src.startswith("img/"):
                    src = "/project/" + src
                self.cur_member["photo"] = src
        elif tag == "h3" and self.cur_member is not None:
            self.cur_field = "h3"
            self.buf = []
        elif tag == "h4" and self.cur_member is not None:
            self.cur_field = "h4"
            self.buf = []
        elif tag == "span" and self.cur_field == "h3":
            # name_en に切替
            # h3 までで集めた buf を name_ja として確定
            self.cur_member["name_ja"] = "".join(self.buf).strip()
            self.buf = []
            self.cur_field = "h3_span"
        elif tag == "br" and self.cur_field in ("career", "h4"):
            self.buf.append("\n")
        elif tag == "a" and self.cur_field is None and self.cur_member is not None:
            # link
            self.cur_link_href = d.get("href", "")
            self.cur_field = "link_label"
            self.buf = []

        self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        # 対応する開始タグまで戻す
        while self.stack and self.stack[-1][0] != tag:
            self.stack.pop()
        if self.stack:
            self.stack.pop()

        if tag == "h3" and self.cur_field == "h3_span" and self.cur_member is not None:
            self.cur_member["name_en"] = "".join(self.buf).strip()
            self.cur_field = None
        elif tag == "h4" and self.cur_field == "h4" and self.cur_member is not None:
            self.cur_member["role"] = "".join(self.buf).strip()
            self.cur_field = None
        elif tag == "div" and self.cur_field == "career" and self.cur_member is not None:
            text = "".join(self.buf)
            # 連続空白を整理
            text = re.sub(r"[ \t]+\n", "\n", text)
            text = re.sub(r"\n{2,}", "\n", text).strip()
            self.cur_member["affiliation"] = text
            self.cur_field = None
        elif tag == "a" and self.cur_field == "link_label" and self.cur_member is not None:
            label = "".join(self.buf).strip()
            if label and self.cur_link_href:
                self.cur_member["links"].append({"label": label, "href": self.cur_link_href})
            self.cur_field = None
            self.cur_link_href = None
        elif tag == "div":
            # area_members 終了でメンバー確定
            # スタックから area_members を出た瞬間を検出する単純化：
            # cur_member が埋まっていて、まだ追加してなければ追加
            if self.cur_member is not None and self.cur_member.get("name_ja"):
                # まだリストに無ければ追加
                if self.cur_member not in self.groups[self.cur_group]:
                    # 直近の area_members タグの閉じだとは限らないので
                    # name と photo が両方あればここで追加とする
                    if self.cur_member["name_ja"] and not getattr(self, "_just_added", False):
                        self.groups[self.cur_group].append(self.cur_member)
                        self.cur_member = None

    def handle_data(self, data):
        if self.cur_field in ("h3", "h3_span", "h4", "career", "link_label"):
            self.buf.append(data)


def main():
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    html = doc["text"]

    parser = MembersParser()
    parser.feed(html)

    # group ラベル
    out = {
        "page_title": doc["title"],
        "page_subtitle": doc.get("subtitle", ""),
        "groups": [
            {"key": "primary", "label": "コアメンバー", "members": parser.groups["primary"]},
            {"key": "secondary", "label": "メンバー", "members": parser.groups["secondary"]},
        ],
    }

    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"primary  : {len(out['groups'][0]['members'])} members")
    print(f"secondary: {len(out['groups'][1]['members'])} members")
    for g in out["groups"]:
        for m in g["members"]:
            print(f"  - {m['name_ja']} ({m['name_en']}) / {m['role']}")


if __name__ == "__main__":
    main()
