# Team photos

メンバーのプロフィール写真。

## 命名規則

`<last_name_lower>_<first_name_lower>.jpg`

例:
- `katsura_yukari.jpg`
- `tanaka_atsumi.jpg`

## 推奨仕様

| 項目 | 推奨 |
|---|---|
| サイズ | 600 × 800 px（縦 3:4） |
| 形式 | JPG（ポートレート）／ PNG（透過必要時） |
| ファイル容量 | 300 KB 以下 |
| 圧縮 | mozjpeg quality 80 程度 |

## 利用箇所

- `/team` ページ（全員）
- トップページ Team セクション（コアメンバー）
- `src/_data/members.json` の `photo` フィールドに `/assets/images/team/xxx.jpg` を指定
