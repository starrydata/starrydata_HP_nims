/**
 * Eleventy 設定
 * 入力: src/
 * 出力: _site/
 * データ: src/_data/  （JSON ファイルを置くだけで全テンプレートから参照可）
 */
export default function (eleventyConfig) {
  // 静的アセットはコピーするだけ
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addPassthroughCopy({ "src/common": "common" });

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
  };
}
