# Starrydata HP 情報アーキテクチャ再編 提案 v1

作成: 2026-08-04 / 対象: Katsura 先生・Starrydata チーム
リポジトリ: `starrydata/starrydata_HP_nims`

---

## 1. 目的

現状のホームページは要素が揃っている一方で、以下の 3 点が利用者体験を弱くしています。

1. **トップナビが 7 項目 + 「使いたい機能」への導線が薄い**
   `About / Use Data / Research / Members / Publications / News / Contact` — Members・News がヘッダーの一等地を占め、ユーザーが探す「システム」「マニュアル」「ダウンロード」は Use Data の下に埋もれる。
2. **ダウンロード経路が複数あるのに導線が不明瞭**
   Latest CSV(Datasets)/ Figshare / NIMS MDR / GitHub の 4 経路があるが、Use Data ページで一覧化されているだけで「どれを選ぶか」の案内が薄い。
3. **引用方法(How to cite)が独立導線を持たない**
   Manual 4.7 節の中に埋もれている。データを使った後の自然なアクションなのに 3 クリック必要。

この提案では、**ヘッダーナビを 6 項目に整理し、「Data ▾」から下方向に横幅いっぱいのメガメニューを開いて全経路を一望できる**構造にします。あわせて `/cite/` ページを新設し、引用文言を単一のソースにします。

---

## 2. 新しい情報アーキテクチャ

### 2.1 トップナビ(6 項目に削減)

```
About | Data ▾ | Research | Systems | Publications | Contact
                                                    [JA / EN] [Search]
```

削除・移動:
- **Members** → About ページ内のセクションへ(独立ページ `/members/` は残す)
- **News** → フッターへ降格(記事数が少なく更新頻度も低いため)
- **Use Data** → **Data ▾**(メガメニュー化)にリネーム・拡張

### 2.2 「Data ▾」メガメニュー

ヘッダー真下、**ブラウザ横幅いっぱい**に開く 3 カラムのパネル。プルダウン(narrow)ではない。

```
┌────────────────────────────────────────────────────────────────────────────┐
│  EXPLORE                    DOWNLOAD                    DOCUMENTATION      │
│                                                                            │
│  🔍  Search (Starrydata)      📦  Latest CSV (Datasets)   📖  Manual        │
│      試料・論文検索                毎日更新の分野別 CSV       検索・登録手順   │
│                                                                            │
│  📊  Visualizer               🔖  Figshare (citable)      📄  REST API      │
│      物性値の散布図ブラウザ         DOI 付き凍結スナップショット  API リファレンス │
│                                                                            │
│  🧭  Sample Explorer          📚  NIMS MDR (citable)      📐  Data schema   │
│      組成検索                       引用可能な永続版             CSV 仕様       │
│                                                                            │
│  🌐  Explorer 3D              📝  How to cite             ❓  FAQ           │
│      3D 物性プロット               引用すべき論文一覧          よくある質問     │
└────────────────────────────────────────────────────────────────────────────┘
```

**分類の根拠**
- **EXPLORE**: ブラウザで対話的に触るツール(認証あり・状態あり)
- **DOWNLOAD**: バルクデータを持ち帰る経路(認証なし・静的ファイル)
- **DOCUMENTATION**: 使い方・仕様の参照文書

**挙動**
- ホバー/クリックで開閉、Escape / 外側クリックで閉じる
- モバイル(≤900px)は accordion に fallback、mega panel は表示しない
- キーボード操作(Tab / ↓ / Enter)対応、`aria-expanded` / `role="menu"` 付与

### 2.3 全体ツリー

```
starrydata_HP_nims (このリポジトリ)
├── /                     Home
├── /about/               目的・特徴・運営体制(Members セクション内包)
├── /data/                Data ハブ(メガメニューと同じ内容の landing)
│   ├── /manual/          Manual(既存を維持、パンくずのみ Data 配下に)
│   ├── /cite/            How to cite ← 新規
│   ├── /api/             REST API リファレンス(将来)
│   └── /schema/          Data schema(将来)
├── /research/            研究分野・成果
├── /systems/             (別リポジトリ `starrydata/links` を統合予定、範囲外)
├── /publications/        論文一覧
├── /members/             メンバー一覧(独立ページは残す)
├── /news/                ニュース一覧(降格するが URL は残す)
└── /contact/             問い合わせ
```

---

## 3. 変更詳細と実装順

### 変更 A: `/cite/` ページ新設 【低リスク・独立】

**内容**: 引用すべき論文 2 件を掲載する固定ページ。JA / EN 両言語。

```
To use the Starrydata2 web system and datasets, please cite one of the
following papers and, if necessary, cite the original source papers.

[1] Starrydata: from published plots to shared materials data (2025).
    Yukari Katsura, Masaya Kumagai, Tomoya Mato, Yu Takada, Yuki Ando,
    Erina Fujita, Fumikazu Hosono, Eiji Koyama, Farhan Mudasar,
    Ton Nu Thanh Phuong, Naoto Saito, Yoshihiro Sakamoto, Atsumi Tanaka,
    Dewi Yana, Kaoru Kimura, Koji Tsuda, Masahiko Demura,
    Science and Technology of Advanced Materials: Methods 5, 1 (2025) 2506976.
    DOI: 10.1080/27660400.2025.2506976

[2] Data-driven analysis of electron relaxation times in PbTe-type
    thermoelectric materials (2019).
    Yukari Katsura, Masaya Kumagai, Takushi Kodani, Mitsunori Kaneshige,
    Yuki Ando, Sakiko Gunji, Yoji Imai, Hideyasu Ouchi, Kazuki Tobita,
    Kaoru Kimura, Koji Tsuda,
    Science and Technology of Advanced Materials 20 (2019) 511-520.
    DOI: 10.1080/14686996.2019.1603885
```

**影響ファイル**
- `src/cite/index.njk`(JA、新規)
- `src/en/cite/index.njk`(EN、新規)
- `_data/i18n.json` に `cite_page` エントリ追加

**工数**: 1 時間 / **リスク**: 新規のため既存 URL 影響なし

### 変更 B: メガメニュー実装 + ナビ再編 【中リスク・全ページ影響】

**内容**: `modern_header.njk` を改修し、Data 項目にメガメニュートリガー + 下方展開パネルを追加。同時に nav 項目を 6 個に整理。

**影響ファイル**
- `src/_includes/modern_header.njk`(改修)
- `src/_data/i18n.json` の `nav.*` セクション(項目削除 / データ構造追加)
- `src/common/css/modern.css` に `.mega-menu-*` クラス追加
- 小さな JS(mega-menu 開閉、モバイル accordion fallback)

**工数**: 4〜5 時間 / **リスク**: 全ページのヘッダーが変わる。動作確認が必要

### 変更 C: `/systems/` ページ再設計 【範囲外・別リポジトリ】

`starrydata/links` リポジトリの再設計になるため、本提案では方針のみ記載:
- ページ名を「Systems」に統一(現行「Links」)
- Core Database / Explore & Visualize / Create & Analyze / Data & Documentation の 4 カテゴリ
- メインシステム(Starrydata2)は大型カードで差別化
- URL は互換のため `/links/` のまま or `/systems/` 新設 + 旧 URL リダイレクト

**別リポジトリのオーナーとの調整が必要**

### 変更 D: `/documentation/` への再編 【中リスク・URL 変更あり】

現行 `/manual/`(Chapter 1〜4)は先日クリーンアップ済み。以下の 5 カテゴリに再配置:

```
/documentation/
├── /getting-started/     (アカウント / 検索 / ダウンロード基本)
├── /data-curation/       (StarryDigitizer / 登録手順)
├── /data-access/         (Web / CSV / API)
├── /data-specification/  (papers / samples / curves schema)
└── /faq/                 (よくある質問)
```

**互換性**: `/manual/` から `/documentation/` へ 301 リダイレクト(HTML の `<meta refresh>` + `<link rel=canonical>`)。既存アンカー(`/manual/download/#api` など)は `/documentation/data-access/#api` 相当へマッピング。

**工数**: 1 日 / **リスク**: 直近整理した Chapter 構造を再度動かす。URL 変更は SEO 影響あり

---

## 4. 実装順序(推奨)

| 順 | 変更 | 依存 | 工数 | 累積 |
|----|------|------|------|------|
| 1 | A. `/cite/` 新設 | なし | 1h | 1h |
| 2 | B. メガメニュー + ナビ再編 | A (メガメニューが `/cite/` を参照) | 4-5h | 6h |
| 3 | D. `/documentation/` 再編 | B (メガメニューが新 URL を参照) | 1d | 2d |
| 4 | C. `/systems/` 再設計 | 別リポジトリ調整 | 別途 | — |

---

## 5. リスク・懸念

| リスク | 対策 |
|--------|------|
| メガメニューのモバイル体験劣化 | ≤900px は accordion fallback、実機確認必須 |
| `/manual/` 既存ブックマークの失効 | 全ページに 301 リダイレクト + `canonical` タグ設置 |
| Members / News が「格下げされた」と受け取られる | About / Footer からのリンクは目立たせる、削除ではないことを明示 |
| `/systems/` 統合が別リポジトリ調整で遅れる | Systems ページは現行 `/links/` を暫定リンク先として先行公開 |
| BibTeX / RIS 形式の要望 | 第 2 弾で対応(v2)、v1 はプレーンテキスト引用のみ |

---

## 6. 未確定事項(Katsura 先生への確認事項)

1. **Members ページを About 配下に階層化することの是非**(独立性は保つが nav 露出は下がる)
2. **News セクションを主要ナビから外すことの是非**
3. **`/systems/` (旧 `/links/`) の統合方針**(別リポジトリオーナーとの調整優先度)
4. **`/manual/` → `/documentation/` の URL 変更の是非**(SEO / 既存被リンクへの影響)
5. **引用形式に BibTeX / RIS ボタンを追加するか**(v1 では未実装)

---

## 7. 変更しないこと

- サイト全体のカラー / タイポ / ロゴ(現行 modern.css を維持)
- Hero / What is / Featured Publications / Get Involved の構造
- 既存の Manual 内容(Chapter 1〜4 の内容は活かして再配置のみ)
- News の記事内容(topics.json)自体は残す
