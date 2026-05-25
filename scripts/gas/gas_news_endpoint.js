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
function verifyAuth(authHash) {
  var props = PropertiesService.getScriptProperties();
  var expected = props.getProperty("ADMIN_AUTH_HASH");
  if (!expected) throw new Error("Server is not configured: ADMIN_AUTH_HASH is missing");
  if (!authHash || authHash !== expected) throw new Error("Unauthorized");
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
    date: date,
    datetime: datetime,
    author: data.author || "",
    summary: summary,
    body_html: body
  };
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

// ── 削除 ──
function deleteTopic(index) {
  var obj = readTopics();
  var list = obj.topics || [];
  if (index < 0 || index >= list.length) throw new Error("Invalid index: " + index);
  var removed = list.splice(index, 1)[0];
  obj.topics = list;
  return commitTopics(obj, "news: delete '" + (removed.title || "no title") + "'");
}
