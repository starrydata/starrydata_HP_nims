# Starrydata HP (NIMS edition)

Starrydata プロジェクトの公式ホームページ。

🌐 **Main URL (公式窓口)**: https://starrydata.nims.go.jp/
🌐 **GitHub Pages 直リンク**: https://starrydata.github.io/starrydata_HP_nims/

## 公開構成

本サイトは **2 箇所** に同じ内容がデプロイされる:

| URL | 用途 | 中身 |
|-----|------|------|
| `https://starrydata.nims.go.jp/` | **公式窓口(推奨)** | NIMS 側のプロキシで `starrydata.github.io/links/` の内容を配信、URL バーは NIMS のまま |
| `https://starrydata.github.io/links/` | 上記のプロキシ実体 | `starrydata_HP_nims` のビルド出力 (PATHPREFIX=/links/) を格納 |
| `https://starrydata.github.io/starrydata_HP_nims/` | GitHub Pages 直配信 | 開発確認・プレビュー用 |

```
[利用者]
   │
   ▼
starrydata.nims.go.jp/     ← 公式窓口 (URL バーはここのまま)
   │  (NIMS プロキシ)
   ▼
starrydata.github.io/links/               ← 実コンテンツ配信
   │  (GitHub Actions: sync-to-links.yml)
   ▼
starrydata/starrydata_HP_nims             ← ソース (本リポジトリ)
```

デプロイパイプライン:
- **main への push** → 2 つの workflow が並列で動く:
  - `deploy.yml`: `PATHPREFIX="/starrydata_HP_nims/"` でビルド → GitHub Pages に配信 (`starrydata.github.io/starrydata_HP_nims/`)
  - `sync-to-links.yml`: `PATHPREFIX="/links/"` でビルド → `starrydata/starrydata.github.io` の `links/` サブディレクトリに commit + push

旧 Systems ページ (2026-08-07 以前の `links/` 内容) は `starrydata.github.io/links_archive/` に退避してある (バックアップ)。

## リポジトリ構成

[Eleventy (11ty)](https://www.11ty.dev/) ベースの静的サイトジェネレータ。`src/_data/*.json` を編集するだけで全テキスト・データを更新できる JSON 駆動構成。

```
starrydata_HP_nims/
├── src/
│   ├── _data/               全テキスト・データ (JSON)
│   │   ├── i18n.json           サイト共通テキスト (日英)
│   │   ├── members.json        メンバー
│   │   ├── projects.json       研究領域
│   │   ├── papers.json         論文 (OpenAlex 連動・自動更新)
│   │   ├── topics.json         ニュース／トピックス
│   │   ├── apps.json           関連ツール
│   │   ├── starrydata_seeds.json  論文取得の seed DOI
│   │   ├── pages_all.json      旧ページ (移行中)
│   │   ├── site.json           旧サイト設定 (移行中)
│   │   └── authors.json        著者マスタ
│   ├── _layouts/            ページレイアウト
│   │   ├── modern.njk          現行デザイン
│   │   ├── base.njk / page.njk 旧レイアウト (移行中)
│   ├── _includes/           部品テンプレート (modern_header / modern_footer / manual_chapter_nav 等)
│   ├── assets/
│   │   └── images/             画像 (team / apps / logo など用途別)
│   ├── common/              CSS / JS
│   │   └── css/modern.css      新デザイン CSS
│   ├── index.njk            日本語トップ
│   ├── en/index.njk         English top
│   ├── resources/           Resources ハブ (JA/EN)
│   ├── cite/                引用ページ (JA/EN)
│   ├── manual/              マニュアル (Chapter 1〜4)
│   └── <section>/...        各ページ
├── scripts/
│   └── fetch_papers.py      OpenAlex + Crossref から論文情報取得 (月次)
├── .github/workflows/
│   ├── deploy.yml           main push → GitHub Pages 公開 (/starrydata_HP_nims/)
│   ├── sync-to-links.yml    main push → starrydata.github.io/links/ に自動同期
│   ├── update-papers.yml    毎月1日 papers.json を自動更新
│   └── update-chart.yml     チャート用 JSON の定期更新
├── eleventy.config.js       Eleventy 設定 (pathPrefix 対応)
└── package.json
```

## 開発

```bash
# 依存関係インストール
npm install

# 開発サーバ起動
npm run serve
# → http://localhost:8080/       (日本語)
# → http://localhost:8080/en/    (English)

# 本番ビルド (ローカル確認用)
npm run build
# → _site/ に出力
```

## デプロイ

main ブランチに push すると 2 つの GitHub Actions が並列で動く:

### 1. GitHub Pages (直配信)
- Workflow: `.github/workflows/deploy.yml`
- ビルド設定: `PATHPREFIX="/starrydata_HP_nims/"`
- 公開先: https://starrydata.github.io/starrydata_HP_nims/
- 用途: 開発プレビュー、直リンク

### 2. links/ 同期 (公式窓口)
- Workflow: `.github/workflows/sync-to-links.yml`
- ビルド設定: `PATHPREFIX="/"` (NIMS プロキシが /links/ プレフィックスを吸収するため、生成 HTML 内のリンクはルート相対)
- 同期先: `starrydata/starrydata.github.io` の `links/` サブディレクトリ
- 公開先: https://starrydata.nims.go.jp/ (NIMS プロキシ経由)
- 用途: **公式窓口**
- 必要な設定: リポジトリ Secrets に `PAGES_SYNC_TOKEN` (Classic PAT `repo` scope または fine-grained PAT: `starrydata/starrydata.github.io` の Contents Read/Write) を登録

### 手動同期 (workflow が失敗した時の緊急用)

```bash
cd /path/to/starrydata_HP_nims
PATHPREFIX=/ npx @11ty/eleventy
# _site/ を starrydata.github.io の links/ に反映
cd /path/to/starrydata.github.io   # gh repo clone starrydata/starrydata.github.io
rm -rf links/*
cp -R /path/to/starrydata_HP_nims/_site/. links/
git add links
git commit -m "Manual sync from starrydata_HP_nims"
git push origin main
```

## 論文情報の更新

`src/_data/papers.json` は OpenAlex + OpenCitations API から自動取得される。

- **手動更新**: `python3 scripts/fetch_papers.py`
- **自動更新**: 毎月 1 日 0:15 JST (GitHub Actions: `update-papers.yml`)
- **対象 DOI の編集**: `src/_data/starrydata_seeds.json` で seed DOI を追加・削除

## メンバー・研究領域・ニュース等の更新

それぞれ `src/_data/<name>.json` を編集 → `npm run build` (ローカル確認) → push で反映される。

| 編集対象 | ファイル |
|---|---|
| サイト共通テキスト (ナビ・hero 文言・メガメニュー等) | `src/_data/i18n.json` |
| メンバー (追加・写真・所属) | `src/_data/members.json` |
| 研究領域 (各分野の説明) | `src/_data/projects.json` |
| ニュース／トピックス | `src/_data/topics.json` |
| 関連ツール (Resources) | `src/_data/apps.json` |
| 論文 seed DOI | `src/_data/starrydata_seeds.json` |

## 画像の追加

用途別フォルダに配置し、JSON の `photo` / `image` フィールドにパスを記載:

```jsonc
{ "photo": "/assets/images/team/katsura_yukari.jpg" }
```

各フォルダの `README.md` に推奨仕様 (サイズ・形式) を記載。

## ライセンス

リポジトリ内容については各ファイルのライセンスに準じる。
