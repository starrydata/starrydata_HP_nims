/**
 * Google Apps Script: Starrydata News (topics.json) を GitHub 経由で更新する
 *
 * === セットアップ手順 ===
 *
 * 1. https://script.google.com/ で新しいプロジェクトを作成
 * 2. このファイルの内容をコピペ
 * 3. スクリプトプロパティ (歯車 → スクリプトプロパティ) に以下を設定:
 *    - GITHUB_TOKEN     : GitHub Personal Access Token (repo スコープ)
 *    - GITHUB_REPO      : starrydata/starrydata_HP_nims
 *    - GITHUB_BRANCH    : main  (任意、省略時は main)
 *    - TOPICS_PATH      : src/_data/topics.json (任意、省略時はこれ)
 *    - ADMIN_AUTH_HASH  : SHA-256("id:pw") の 16 進文字列
 * 4. デプロイ → 新しいデプロイ → ウェブアプリ
 *    - 実行するユーザー: 自分
 *    - アクセスできるユーザー: 全員
 * 5. 表示された URL を admin/index.html の GAS_URL に貼る
 *
 * topics.json の構造（既存）:
 *   { "topics": [
 *     { id, slug, title, date, datetime, author, summary, body_html }, ...
 *   ] }
 */

const DEFAULT_BRANCH = "main";
const DEFAULT_PATH = "src/_data/topics.json";

// ── 認証 ──
// GAS 側は共有 ID/パスワードの SHA-256 を預かる軽量な作りだが、公開 URL なので
// 総当たりを現実的な時間で止めるためのレート制限と、ハッシュ比較の定数時間化を入れる。
var AUTH_FAIL_WINDOW_SEC = 15 * 60; // 15 分
var AUTH_FAIL_THRESHOLD = 10;        // 15 分で 10 回失敗したら以後拒否

function constantTimeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  // SHA-256 hex は常に 64 文字なので長さ差は本来発生しない。長さが違う入力は
  // そのまま弾くが、同じ長さでも必ず全文字を XOR してからビットを集めることで、
  // 文字一致位置の情報が応答時間に乗らないようにする。
  if (a.length !== b.length) return false;
  var diff = 0;
  for (var i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

function verifyAuth(authHash) {
  var cache = CacheService.getScriptCache();
  var failCount = parseInt(cache.get("auth_fail_count") || "0", 10) || 0;
  if (failCount >= AUTH_FAIL_THRESHOLD) {
    throw new Error("Too many failed attempts. Try again later.");
  }
  var props = PropertiesService.getScriptProperties();
  var expected = props.getProperty("ADMIN_AUTH_HASH");
  if (!expected) throw new Error("Server is not configured: ADMIN_AUTH_HASH is missing");
  if (!authHash || !constantTimeEqual(authHash, expected)) {
    cache.put("auth_fail_count", String(failCount + 1), AUTH_FAIL_WINDOW_SEC);
    throw new Error("Unauthorized");
  }
  // 成功したらカウンタをリセット
  cache.remove("auth_fail_count");
}

// ── GET / POST ──
function doGet(e) {
  try {
    var auth = (e && e.parameter && e.parameter.auth) || "";
    verifyAuth(auth);
    var data = readTopics();
    return json({ status: "ok", data: data });
  } catch (err) {
    return json({ status: "error", message: err.message });
  }
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    verifyAuth(data.auth || "");
    var action = data.action || "list";

    if (action === "list") {
      return json({ status: "ok", data: readTopics() });
    } else if (action === "add") {
      return json({ status: "ok", result: addTopic(data.entry) });
    } else if (action === "edit") {
      return json({ status: "ok", result: editTopic(data.index, data.entry) });
    } else if (action === "delete") {
      return json({ status: "ok", result: deleteTopic(data.index) });
    } else if (action === "upload_image") {
      return json({ status: "ok", url: uploadImage(data.filename, data.content_b64) });
    } else if (action === "translate") {
      return json({ status: "ok", translated: translateText(data.text, data.source, data.target) });
    } else {
      throw new Error("Unknown action: " + action);
    }
  } catch (err) {
    return json({ status: "error", message: err.message });
  }
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// ── GitHub API 共通 ──
function ghApi(method, path, payload) {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty("GITHUB_TOKEN");
  var repo = props.getProperty("GITHUB_REPO");
  var url = "https://api.github.com/repos/" + repo + "/" + path;
  var options = {
    method: method,
    headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github.v3+json" },
    muteHttpExceptions: true
  };
  if (payload !== undefined) {
    options.contentType = "application/json";
    options.payload = JSON.stringify(payload);
  }
  var resp = UrlFetchApp.fetch(url, options);
  var code = resp.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error("GitHub API " + method + " " + path + " " + code + ": " + resp.getContentText());
  }
  return JSON.parse(resp.getContentText());
}

function getBranch() {
  return PropertiesService.getScriptProperties().getProperty("GITHUB_BRANCH") || DEFAULT_BRANCH;
}
function getPath() {
  return PropertiesService.getScriptProperties().getProperty("TOPICS_PATH") || DEFAULT_PATH;
}

// ── topics.json の読み込み ──
function readTopics() {
  var info = ghApi("GET", "contents/" + getPath() + "?ref=" + getBranch());
  var content = Utilities.newBlob(Utilities.base64Decode(info.content)).getDataAsString();
  return JSON.parse(content);
}

// ── topics.json を Git Data API で 1 コミットに ──
function commitTopics(topicsObj, message) {
  var branch = getBranch();
  var ref = ghApi("GET", "git/ref/heads/" + branch);
  var parentSha = ref.object.sha;
  var parentCommit = ghApi("GET", "git/commits/" + parentSha);
  var baseTree = parentCommit.tree.sha;

  var content = JSON.stringify(topicsObj, null, 2) + "\n";
  var blob = ghApi("POST", "git/blobs", { content: content, encoding: "utf-8" });

  var newTree = ghApi("POST", "git/trees", {
    base_tree: baseTree,
    tree: [{ path: getPath(), mode: "100644", type: "blob", sha: blob.sha }]
  });
  var commit = ghApi("POST", "git/commits", {
    message: message, tree: newTree.sha, parents: [parentSha]
  });
  ghApi("PATCH", "git/refs/heads/" + branch, { sha: commit.sha });
  return commit.sha;
}

// ── ヘルパー ──
function slugify(s) {
  if (!s) return "untitled";
  return s.toString().toLowerCase()
    .replace(/[^\w\-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .substring(0, 100) || "untitled";
}

function nextId(list) {
  var maxId = 0;
  list.forEach(function (t) {
    var n = parseInt(t.id || "0", 10);
    if (!isNaN(n) && n > maxId) maxId = n;
  });
  return String(maxId + 1);
}

function normalizeEntry(data, existing) {
  var date = data.date || "";
  var datetime = data.datetime || (date ? date + "T00:00:00+09:00" : "");
  var title = data.title || "";
  var slug = data.slug || (existing && existing.slug) || slugify(title);
  var summary = (data.summary || "").trim();
  var body = (data.body_html || "").trim();
  return {
    id: (existing && existing.id) || data.id || "new",
    slug: slug,
    title: title,
    title_en: (data.title_en || "").trim(),
    date: date,
    datetime: datetime,
    category: data.category || "",
    subcategory: data.subcategory || "",
    author: data.author || "",
    summary: summary,
    summary_en: (data.summary_en || "").trim(),
    body_html: body,
    body_html_en: (data.body_html_en || "").trim(),
    paper_title: (data.paper_title || "").trim(),
    doi: (data.doi || "").trim().replace(/^https?:\/\/(dx\.)?doi\.org\//i, ""),
    url: (data.url || "").trim()
  };
}

// ── 翻訳 (Google Apps Script の組み込み LanguageApp、無料) ──
function translateText(text, source, target) {
  if (!text) return "";
  source = source || "ja";
  target = target || "en";
  // 長文も 1 リクエストで送れるが、安定性のため段落単位に分割
  var parts = String(text).split(/\n{2,}/);
  return parts.map(function (p) {
    if (!p.trim()) return p;
    return LanguageApp.translate(p, source, target);
  }).join("\n\n");
}

function sortByDateDesc(topics) {
  topics.sort(function (a, b) { return (b.datetime || "").localeCompare(a.datetime || ""); });
}

// ── 追加 ──
function addTopic(entry) {
  var obj = readTopics();
  var list = obj.topics || [];
  var normalized = normalizeEntry(entry);
  if (normalized.id === "new") normalized.id = nextId(list);
  list.unshift(normalized);
  sortByDateDesc(list);
  obj.topics = list;
  return commitTopics(obj, "news: add '" + (normalized.title || "no title") + "'");
}

// ── 編集 ──
function editTopic(index, entry) {
  var obj = readTopics();
  var list = obj.topics || [];
  if (index < 0 || index >= list.length) throw new Error("Invalid index: " + index);
  list[index] = normalizeEntry(entry, list[index]);
  sortByDateDesc(list);
  obj.topics = list;
  return commitTopics(obj, "news: edit '" + (list[index].title || "no title") + "'");
}

// ── 画像アップロード ──
// 画像を src/assets/images/news/<timestamp>_<filename> にコミットし、
// プレビュー用に raw.githubusercontent の URL を返す。
// 保存時の Markdown 上は admin 側で /assets/... の相対パスに正規化される。
var ALLOWED_IMAGE_EXT = ["png", "jpg", "jpeg", "gif", "webp"];
// SVG は <script> と on* 属性を含められ、同一オリジンで任意 JS が走るため許可しない。
// HTML も不可。拡張子だけだと evil.html.png のような詐称が通るので、下でマジック
// ナンバーと突き合わせて拡張子詐称を落とす。
var IMAGE_MAGIC = {
  png:  ["89504e47"],
  gif:  ["47494638"],
  jpg:  ["ffd8ff"],
  jpeg: ["ffd8ff"],
  webp: ["52494646"] // "RIFF" (WEBP は 4-7 バイト目に "WEBP" が入るが、ここは軽い篩)
};

function uploadImage(filename, contentB64) {
  if (!filename) throw new Error("filename is required");
  if (!contentB64) throw new Error("content_b64 is required");
  var safe = String(filename).replace(/[^a-zA-Z0-9._-]/g, "_");

  // 二重拡張子 (evil.html.png など) 対策で、"." 区切りで全要素を見る。
  // 全要素が英数字かつ、末尾が allowlist に合致する場合のみ許可。
  var parts = safe.split(".");
  if (parts.length < 2) throw new Error("Invalid filename (no extension)");
  var ext = parts[parts.length - 1].toLowerCase();
  if (ALLOWED_IMAGE_EXT.indexOf(ext) < 0) {
    throw new Error("Unsupported extension: " + ext + " (allowed: " + ALLOWED_IMAGE_EXT.join(", ") + ")");
  }
  for (var i = 0; i < parts.length - 1; i++) {
    if (!/^[A-Za-z0-9_-]+$/.test(parts[i])) {
      throw new Error("Invalid filename segment: " + parts[i]);
    }
  }

  // 中身のマジックナンバーを拡張子と突き合わせる。拡張子詐称を落とす。
  // Utilities.base64Decode は Byte[]（Java 由来、Array メソッドは使えない）を返すので
  // for ループで読む。先頭 24 base64 文字 = 18 バイトなら、必要な先頭 8 バイトを取れる。
  var decoded = Utilities.base64Decode(contentB64.substring(0, 24));
  var header = "";
  var maxBytes = Math.min(8, decoded.length);
  for (var j = 0; j < maxBytes; j++) {
    header += ("0" + (decoded[j] & 0xff).toString(16)).slice(-2);
  }
  var allowedMagic = IMAGE_MAGIC[ext] || [];
  var magicOk = allowedMagic.some(function (m) { return header.indexOf(m) === 0; });
  if (!magicOk) {
    throw new Error("Content does not match extension ." + ext);
  }

  var ts = new Date().toISOString().replace(/[:.]/g, "-").substring(0, 19);
  var pathInRepo = "src/assets/images/news/" + ts + "_" + safe;
  var branch = getBranch();
  ghApi("PUT", "contents/" + pathInRepo, {
    message: "news: upload image " + safe,
    content: contentB64,
    branch: branch
  });
  var props = PropertiesService.getScriptProperties();
  var repo = props.getProperty("GITHUB_REPO");
  // raw.githubusercontent はコミット直後にアクセス可能 → エディタプレビュー用に返す
  return "https://raw.githubusercontent.com/" + repo + "/" + branch + "/" + pathInRepo;
}

// ── 削除 ──
function deleteTopic(index) {
  var obj = readTopics();
  var list = obj.topics || [];
  if (index < 0 || index >= list.length) throw new Error("Invalid index: " + index);
  var removed = list.splice(index, 1)[0];
  obj.topics = list;
  return commitTopics(obj, "news: delete '" + (removed.title || "no title") + "'");
}
