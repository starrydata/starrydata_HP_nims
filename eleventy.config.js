/**
 * Eleventy 設定
 * 入力: src/
 * 出力: _site/
 * データ: src/_data/  （JSON ファイルを置くだけで全テンプレートから参照可）
 *
 * pathPrefix:
 *   ローカル開発時: "/" （http://localhost:8080/）
 *   GitHub Pages : "/starrydata_HP_nims/"
 *   env PATHPREFIX で上書き可能
 */
const PATH_PREFIX = process.env.PATHPREFIX || "/";

export default function (eleventyConfig) {
  // 静的アセットはコピーするだけ
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addPassthroughCopy({ "src/common": "common" });
  // ルートの画像（MovableType 元配置: /img/）
  eleventyConfig.addPassthroughCopy({ "src/img": "img" });
  // 各ブログ配下の img/ ディレクトリ（MovableType の元配置）
  eleventyConfig.addPassthroughCopy("src/*/img/**");
  // 散布図用 JSON を /data/ で配信
  eleventyConfig.addPassthroughCopy({ "src/_data/chart_temp_seebeck.json": "data/chart_temp_seebeck.json" });
  // News admin (GAS 経由で topics.json を編集する管理画面)
  eleventyConfig.addPassthroughCopy({ "src/admin": "admin" });

  // pathPrefix を HTML 内の絶対パスにも適用
  // (href="/..." / src="/..." / fetch('/...') / url('/...') 等を書き換え)
  if (PATH_PREFIX !== "/" && PATH_PREFIX !== "") {
    const trimmed = PATH_PREFIX.replace(/\/$/, "");
    eleventyConfig.addTransform("pathprefix-rewrite", function (content, outputPath) {
      if (!outputPath || !outputPath.endsWith(".html")) return content;
      return content
        // href="/..." / src="/..."
        .replace(
          /(href|src)="\/(?!\/)([^"]*)"/g,
          (m, attr, rest) => `${attr}="${trimmed}/${rest}"`
        )
        // JSON 内のエスケープ済み属性 href=\"/...\" / src=\"/...\" (news_modal などで body_html を埋め込んでいる箇所)
        .replace(
          /(href|src)=\\"\/(?!\/)([^\\"]*)\\"/g,
          (m, attr, rest) => `${attr}=\\"${trimmed}/${rest}\\"`
        )
        // inline JS: fetch('/...') / fetch("/...")
        .replace(
          /(fetch\(\s*['"`])\/(?!\/)([^'"`]*)/g,
          (m, p, rest) => `${p}${trimmed}/${rest}`
        )
        // inline CSS: url('/...') / url("/...") / url(/...)
        .replace(
          /(url\(\s*['"]?)\/(?!\/)([^'")]*)/g,
          (m, p, rest) => `${p}${trimmed}/${rest}`
        );
    });
  }

  // Watch
  eleventyConfig.addWatchTarget("src/_data");
  eleventyConfig.addWatchTarget("src/assets");

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
      layouts: "_layouts",
      data: "_data",
    },
    templateFormats: ["njk", "md"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
    pathPrefix: PATH_PREFIX,
  };
}
