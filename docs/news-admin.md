# Starrydata News Admin

ニュース（`src/_data/topics.json`）を Web UI から追加・編集・削除するための管理画面。

```
ブラウザ admin/  ──HTTPS POST──▶  Google Apps Script  ──GitHub API──▶  リポジトリ更新
                  (SHA-256 認証)                       (Personal Access Token)
```

## 構成

- **管理画面**: `src/admin/index.html` (GitHub Pages で配信される)
  - 公開 URL: `https://starrydata.github.io/starrydata_HP_nims/admin/`
- **バックエンド**: `scripts/gas/gas_news_endpoint.js` (Google Apps Script に貼る)
- **更新先**: `src/_data/topics.json`

## セットアップ手順

### 1. GitHub Personal Access Token (PAT) を作成

1. https://github.com/settings/tokens → **Generate new token (classic)**
2. Scope: `repo` (fine-grained でも可、starrydata_HP_nims への Contents 書込権限)
3. 発行された **トークン文字列** を控える

### 2. Google Apps Script プロジェクトを作成

1. https://script.google.com/ → **新しいプロジェクト**
2. `scripts/gas/gas_news_endpoint.js` の内容を **すべてコピペ**
3. 左サイドバーの**歯車** → **スクリプトプロパティ** で以下を設定:

| キー | 値 |
|---|---|
| `GITHUB_TOKEN` | (1) で発行した PAT |
| `GITHUB_REPO` | `starrydata/starrydata_HP_nims` |
| `GITHUB_BRANCH` | `main` (任意) |
| `TOPICS_PATH` | `src/_data/topics.json` (任意) |
| `ADMIN_AUTH_HASH` | 下記 (3) のハッシュ |

### 3. 管理者 ID / パスワードを決めて SHA-256 ハッシュ化

ターミナルで:

```bash
# 例: id=admin, pw=YourPasswordHere の場合
echo -n "admin:YourPasswordHere" | shasum -a 256
# 出力例: 9a3b7c1d... (64文字)
```

この **64文字の hex 文字列** を `ADMIN_AUTH_HASH` に設定。

> ⚠ パスワードは絶対にリポジトリにコミットしない。Slack/メール等で関係者にのみ共有。

### 4. GAS をウェブアプリとしてデプロイ

1. 右上の **デプロイ** → **新しいデプロイ**
2. 種類: **ウェブアプリ**
3. 設定:
   - 実行するユーザー: **自分** (オーナー)
   - アクセスできるユーザー: **全員**
4. **デプロイ** → 表示された URL (`https://script.google.com/macros/s/.../exec`) をコピー

### 5. 管理画面に GAS URL を設定

`src/admin/index.html` の以下の行を編集:

```js
const GAS_URL = "";  // ← ここに (4) の URL を貼る
```

修正 → コミット → push して GitHub Pages にデプロイ。

### 6. 動作確認

ブラウザで:

```
https://starrydata.github.io/starrydata_HP_nims/admin/
```

ID / パスワードを入力してログイン。

## 使い方

| 操作 | 動作 |
|---|---|
| **新規投稿** | フォームに入力 → 「投稿する」→ GitHub にコミット → topics.json に追加 |
| **編集** | 一覧の「編集」→ フォームに既存値が入る → 「更新する」 |
| **削除** | 一覧の「削除」→ 確認 → GitHub からエントリ削除 |
| **再読込** | 「Reload」で GitHub から最新を取得 |
| **ログアウト** | localStorage の認証ハッシュを削除 |

## フィールド

| フィールド | 必須 | 説明 |
|---|---|---|
| 日付 | ✓ | `YYYY-MM-DD`。`datetime` も自動生成 |
| スラッグ | - | URL 末尾 (`/topics/<slug>.html`)。空欄ならタイトルから自動生成 |
| タイトル | ✓ | ニュースの見出し |
| 概要 | - | 一覧で表示される 1〜2 行のリード文 |
| 本文 (HTML) | - | `<p>...</p>` 等の HTML 直接記述 |
| 著者 | - | 任意 |

## トラブルシューティング

- **401 Unauthorized**: パスワードが違う or `ADMIN_AUTH_HASH` がスクリプトプロパティに未設定
- **403 Forbidden (GitHub)**: PAT のスコープが不足、または期限切れ
- **404 Not Found**: `GITHUB_REPO` のスペルミス、または `TOPICS_PATH` が間違い
- **CORS エラー**: GAS デプロイ時の「アクセスできるユーザー」が **全員** になっているか確認
- **コードを更新した後反映されない**: GAS で **デプロイ → デプロイを管理 → 編集 (鉛筆) → 新しいバージョン → デプロイ**
