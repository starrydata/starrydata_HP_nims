# Starrydata HP (NIMS edition)

Starrydata プロジェクトの公式ホームページ。

🌐 **Live**: https://starrydata.github.io/starrydata_HP_nims/

## 構成

[Eleventy (11ty)](https://www.11ty.dev/) ベースの静的サイトジェネレータ。`src/_data/*.json` を編集するだけで全テキスト・データを更新できる JSON 駆動構成。

```
starrydata_HP_nims/
├── src/
│   ├── _data/               全テキスト・データ（JSON）
│   │   ├── i18n.json           サイト共通テキスト（日英）
│   │   ├── members.json        メンバー
│   │   ├── projects.json       研究領域
│   │   ├── papers.json         論文（OpenAlex 連動・自動更新）
│   │   ├── topics.json         ニュース／トピックス
│   │   ├── starrydata_seeds.json  論文取得の seed DOI
│   │   ├── pages_all.json      旧ページ（移行中）
│   │   ├── site.json           旧サイト設定（移行中）
│   │   └── authors.json        著者マスタ
│   ├── _layouts/            ページレイアウト
│   │   ├── modern.njk          新デザイン（スタートアップ系）
│   │   ├── base.njk            旧レイアウト（移行中）
│   │   └── page.njk            旧ページ用
│   ├── _includes/           部品テンプレート
│   ├── assets/
│   │   └── images/             画像（用途別フォルダ）
│   │       ├── team/              メンバー写真
│   │       ├── research/          7分野のキー画像
│   │       ├── partners/          支援機関ロゴ
│   │       ├── hero/              Hero 用大判画像
│   │       ├── og/                OGP/SNS用
│   │       └── icons/             favicon, logo
│   ├── common/              CSS / JS / SSI
│   │   ├── css/
│   │   │   └── modern.css         新デザイン CSS
│   │   └── ...
│   ├── index.njk            日本語トップ
│   ├── en/index.njk         English top
│   └── <section>/...        各ページ
├── scripts/
│   └── fetch_papers.py      OpenAlex + Crossref から論文情報取得（月次）
├── .github/workflows/
│   ├── deploy.yml           main push → GitHub Pages 公開
│   └── update-papers.yml    毎月1日 papers.json を自動更新
├── eleventy.config.js       Eleventy 設定（pathPrefix 対応）
└── package.json
```

## 開発

```bash
# 依存関係インストール
npm install

# 開発サーバ起動
npm run serve
# → http://localhost:8080/   (日本語)
# → http://localhost:8080/en/  (English)

# 本番ビルド
npm run build
# → _site/ に出力
```

## デプロイ

main ブランチに push すると GitHub Actions が走り、数分後に GitHub Pages に反映されます：

- Build: `.github/workflows/deploy.yml`
- URL: https://starrydata.github.io/starrydata_HP_nims/

## 論文情報の更新

`src/_data/papers.json` は OpenAlex + OpenCitations API から自動取得されます。

- **手動更新**: `python3 scripts/fetch_papers.py`
- **自動更新**: 毎月 1 日 0:15 JST（GitHub Actions: `update-papers.yml`）
- **対象 DOI の編集**: `src/_data/starrydata_seeds.json` で seed DOI を追加・削除

## ニュース・メンバー・研究領域の更新

それぞれ `src/_data/<name>.json` を編集 → `npm run build` または push で反映されます。

| 編集対象 | ファイル |
|---|---|
| サイト共通テキスト（ナビ・hero 文言） | `src/_data/i18n.json` |
| メンバー（追加・写真・所属） | `src/_data/members.json` |
| 研究領域（各分野の説明） | `src/_data/projects.json` |
| ニュース／トピックス | `src/_data/topics.json` |
| 論文 seed DOI | `src/_data/starrydata_seeds.json` |

## 画像の追加

用途別フォルダに配置し、JSON の `photo` / `image` フィールドにパスを記載：

```jsonc
{ "photo": "/assets/images/team/katsura_yukari.jpg" }
```

各フォルダの `README.md` に推奨仕様（サイズ・形式）を記載しています。

## ライセンス

リポジトリ内容については各ファイルのライセンスに準じます。
