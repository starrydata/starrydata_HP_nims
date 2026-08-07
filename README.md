# Starrydata HP (NIMS edition)

Starrydata プロジェクトの公式ホームページ (NIMS 版)。

## 公開 URL

| URL | 役割 |
|-----|------|
| https://starrydata.nims.go.jp/ | **公式窓口 (一般公開)**。URL バーは NIMS のまま、中身は `links/` を NIMS プロキシで配信 |
| https://starrydata.github.io/links/ | 上記の実体。ここに置かれた HTML がプロキシ経由で公式窓口に出る |
| https://starrydata.github.io/starrydata_HP_nims/ | GitHub Pages 直配信 (プレビュー・直リンク用) |

## 構成と役割

```
[一般利用者]
     │
     ▼
starrydata.nims.go.jp/                    ← 公式窓口 (URL バーはここ)
     │  NIMS プロキシ (パス /links/ を吸収)
     ▼
starrydata/starrydata.github.io           ← 配信用リポジトリ (触らない)
   ├── links/                             ← 公式窓口の実体 (自動生成)
   ├── links_archive/                     ← 旧 Systems ページ (バックアップ)
   └── starrydata_HP_nims/                ← プレビュー用 (自動生成)
                                                 ▲
                                                 │ 自動同期 (GitHub Actions)
                                                 │
starrydata/starrydata_HP_nims  ← 【編集はここだけ】 ソースリポジトリ (本リポ)
     (ローカル: /Users/atsumitanaka/Documents/starrydata_HP/)
```

| コンポーネント | 種類 | 役割 | 編集 |
|---|---|---|---|
| `starrydata_HP_nims` (本リポ) | ソース | Eleventy テンプレート・データ・画像の原本 | **編集する (唯一の編集対象)** |
| `starrydata.github.io/links/` | 成果物 | 公式窓口が配信する HTML/JSON | 触らない (次回同期で上書きされる) |
| `starrydata.github.io/starrydata_HP_nims/` | 成果物 | プレビュー用 GitHub Pages | 触らない (自動生成) |
| `starrydata.github.io/links_archive/` | バックアップ | 旧 Systems ページ (2026-08-07 以前の `links/`) | 触らない |
| NIMS プロキシ | インフラ | `starrydata.nims.go.jp/` で `links/` を配信 | NIMS 情シス管理 (触らない) |

## 編集ワークフロー

**編集するのは常に本リポジトリ `starrydata_HP_nims` のみ。**
`starrydata.github.io` 側の `links/` や `starrydata_HP_nims/` を直接編集してはいけない (次の自動同期で上書きされて消える)。

一般的な流れ:

```bash
# 1. 編集
#    src/_data/*.json  (テキスト・メンバー・トピック等)
#    src/**/*.njk      (テンプレート)
#    src/assets/images/  (画像)

# 2. ローカル確認
npm install          # 初回のみ
npm run serve        # http://localhost:8080/ でプレビュー

# 3. push → 自動デプロイ (下記「リリース」参照)
git add -A && git commit -m "..." && git push origin main
```

編集ファイルの詳細は下記 [メンバー・研究領域・ニュース等の更新](#メンバー研究領域ニュース等の更新) を参照。

## リリース (自動デプロイ)

**`main` ブランチに push すると 2 つの GitHub Actions workflow が同時に走り、両方に自動反映される。**

| Workflow | PATHPREFIX | 反映先 | 用途 |
|---|---|---|---|
| `deploy.yml` | `/starrydata_HP_nims/` | https://starrydata.github.io/starrydata_HP_nims/ | プレビュー・直リンク |
| `sync-to-links.yml` | `/` (NIMS プロキシが `/links/` を吸収) | `starrydata.github.io/links/` → **https://starrydata.nims.go.jp/** | **公式窓口** |

**注意: プレビューと本番が同時に更新される。** 「プレビューで確認してから本番に出す」というワンクッションはないため、push 前に必ずローカル (`npm run serve`) で動作確認すること。壊れた変更はそのまま公式窓口に反映される。

preview → production を分けたい場合 (例: `develop` push でプレビューだけ更新、`main` merge で公式窓口反映) は workflow の書き換えが必要 (現状未対応)。

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

## デプロイ詳細 (workflow 設定)

上記「[リリース (自動デプロイ)](#リリース-自動デプロイ)」の内部仕様。

### 1. `deploy.yml` (プレビュー)
- ファイル: `.github/workflows/deploy.yml`
- ビルド: `PATHPREFIX="/starrydata_HP_nims/"`
- 公開先: https://starrydata.github.io/starrydata_HP_nims/
- 権限: GitHub Pages 標準 (`permissions: pages: write, id-token: write`)

### 2. `sync-to-links.yml` (公式窓口)
- ファイル: `.github/workflows/sync-to-links.yml`
- ビルド: `PATHPREFIX="/"` (NIMS プロキシが `/links/` プレフィックスを吸収するため、生成 HTML 内のリンクはルート相対)
- 同期先: `starrydata/starrydata.github.io` の `links/` サブディレクトリ (Actions が別リポに commit + push)
- 公開先: https://starrydata.nims.go.jp/ (NIMS プロキシ経由)
- 必要な設定: リポジトリ Secrets に `PAGES_SYNC_TOKEN` を登録
  - **推奨: fine-grained PAT**
    - Resource owner: `starrydata`
    - Repository access: `starrydata/starrydata.github.io` のみ
    - Permissions → Contents: **Read and write**
    - `starrydata` org は「Require administrator approval」ポリシーを設定済のため、PAT 発行後は org admin (`kumagallium` / `t29mato`) の承認が必要
    - 承認画面: https://github.com/organizations/starrydata/settings/personal-access-tokens/pending_requests
  - 代替: Classic PAT `repo` scope (即発行可、ただし権限が広いので非推奨)

**PAT 期限切れ時の更新手順**
1. 新しい fine-grained PAT を再発行 (期限 1 年推奨)
2. admin に承認依頼
3. https://github.com/starrydata/starrydata_HP_nims/settings/secrets/actions で `PAGES_SYNC_TOKEN` を **Update**
4. Actions タブから `sync-to-links.yml` を手動実行して動作確認

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
