#!/usr/bin/env bash
# 公開サイトから common/ 配下の静的リソースを取得する
# 取得先: _source/public/common/

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/_source/public"
BASE_URL="https://starrydata.org"

mkdir -p "$DEST"
cd "$DEST"

URLS=(
  # CSS（MTテンプレに含まれない外部CSS）
  "common/css/modaal.css"
  "common/css/swiper.min.css"

  # JS
  "common/js/jquery-3.5.1.min.js"
  "common/js/jquery.heightLine.js"
  "common/js/jquery.plugin.js"
  "common/js/modaal.js"
  "common/js/swiper.min.js"

  # 画像
  "common/img/img_fb.gif"
  "common/img/img_index_noimg.png"
  "common/img/img_topics_noimg.png"
  "common/img/logo_footer.png"
  "common/img/logo.png"

  # SSI インクルード
  "common/include/analytics.html"
  "common/include/btn_use.html"
  "common/include/footer_menu.html"
  "common/include/footer.html"
  "common/include/header.html"
)

OK=0
FAIL=0
FAILED=()

for path in "${URLS[@]}"; do
  url="$BASE_URL/$path"
  # ディレクトリ作成
  dir=$(dirname "$path")
  mkdir -p "$dir"
  if curl -fsS -o "$path" "$url"; then
    echo "OK  $path"
    OK=$((OK+1))
  else
    echo "NG  $path"
    FAIL=$((FAIL+1))
    FAILED+=("$path")
  fi
done

echo ""
echo "Done. OK=$OK NG=$FAIL"
if [ $FAIL -gt 0 ]; then
  echo "Failed:"
  printf '  %s\n' "${FAILED[@]}"
fi
