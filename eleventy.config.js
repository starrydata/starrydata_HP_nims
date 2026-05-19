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

  // pathPrefix を HTML 内の絶対パスにも適用（href="/..." / src="/..." を書き換え）
  if (PATH_PREFIX !== "/" && PATH_PREFIX !== "") {
    const trimmed = PATH_PREFIX.replace(/\/$/, "");
    eleventyConfig.addTransform("pathprefix-rewrite", function (content, outputPath) {
      if (!outputPath || !outputPath.endsWith(".html")) return content;
      // href="/..." と src="/..." を書き換え（"//" や "http(s)://" は除外）
      return content.replace(
        /(href|src)="\/(?!\/)([^"]*)"/g,
        (m, attr, rest) => `${attr}="${trimmed}/${rest}"`
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
