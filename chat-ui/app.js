const SAME_ORIGIN_BASE = window.location.origin;
const REMOTE_API_BASE = "https://helpcentre-dsi-mdr.emergentai.ug";
const DEFAULT_API_BASE = window.__API_BASE__ || REMOTE_API_BASE;
const API_STORAGE_KEY = "helpcentre_api_base";
const API_FALLBACKS = [
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

const sessionId =
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;

let apiBase = normalizeApiBase(localStorage.getItem(API_STORAGE_KEY) || DEFAULT_API_BASE);

const chatBox = document.getElementById("chat-box");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const searchResults = document.getElementById("search-results");
const apiBaseInput = document.getElementById("api-base-input");
const applyApiBtn = document.getElementById("apply-api-btn");
const testApiBtn = document.getElementById("test-api-btn");
const apiStatus = document.getElementById("api-status");
const topStatus = document.getElementById("top-status");

function normalizeApiBase(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function endpoint(path) {
  return `${apiBase}${path}`;
}

function setApiStatus(message, statusClass = "status-unknown") {
  if (apiStatus) {
    apiStatus.className = `api-status ${statusClass}`;
    apiStatus.innerText = message;
  }

  if (topStatus) {
    topStatus.className = "status-pill";
    if (statusClass === "status-ok") {
      topStatus.style.background = "#dcfce7";
      topStatus.style.color = "#166534";
      topStatus.innerText = "API Connected";
    } else if (statusClass === "status-bad") {
      topStatus.style.background = "#fef2f2";
      topStatus.style.color = "#991b1b";
      topStatus.innerText = "API Offline";
    } else {
      topStatus.style.background = "#eef2ff";
      topStatus.style.color = "#3730a3";
      topStatus.innerText = "API Unknown";
    }
  }
}

function applyApiBase(nextBase) {
  const normalized = normalizeApiBase(nextBase);
  if (!normalized) {
    setApiStatus("Enter a valid API base URL before applying.", "status-warn");
    return;
  }
  apiBase = normalized;
  localStorage.setItem(API_STORAGE_KEY, apiBase);
  if (apiBaseInput) apiBaseInput.value = apiBase;
  setApiStatus(`API base set to ${apiBase}`, "status-unknown");
}

function scrollToBottom() {
  if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function addMessage(text, sender) {
  if (!chatBox) return;

  const wrapper = document.createElement("div");
  wrapper.className = `message ${sender}`;

  const messageText = document.createElement("div");
  messageText.className = "message-text";
  messageText.innerText = text;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.innerText = sender === "user" ? "You" : "Assistant";

  wrapper.appendChild(messageText);
  wrapper.appendChild(meta);
  chatBox.appendChild(wrapper);
  scrollToBottom();
}

function addTypingBubble() {
  if (!chatBox) return null;
  const bubble = document.createElement("div");
  bubble.className = "message ai typing";
  bubble.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
  chatBox.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

function addSources(sources = []) {
  if (!Array.isArray(sources) || !sources.length || !chatBox) return;

  const sourceBlock = document.createElement("div");
  sourceBlock.className = "message ai";

  const sourceText = sources
    .slice(0, 3)
    .map((source, index) => {
      const sourceName = source.source_name || source.source_file || `Source ${index + 1}`;
      const sourceUrl = source.source_url ? ` (${source.source_url})` : "";
      return `- ${sourceName}${sourceUrl}`;
    })
    .join("\n");

  sourceBlock.innerHTML = `
    <div class="message-text"><strong>Sources</strong>\n${escapeHtml(sourceText)}</div>
    <div class="message-meta">Retrieved context</div>
  `;

  chatBox.appendChild(sourceBlock);
  scrollToBottom();
}

function addRatingStars() {
  if (!chatBox) return;

  const ratingDiv = document.createElement("div");
  ratingDiv.className = "rating";

  const label = document.createElement("div");
  label.className = "rating-label";
  label.innerText = "Rate this answer";
  ratingDiv.appendChild(label);

  const stars = [];
  for (let i = 1; i <= 5; i += 1) {
    const star = document.createElement("span");
    star.className = "star";
    star.innerText = "★";
    star.onclick = async () => {
      stars.forEach((s, idx) => s.classList.toggle("active", idx < i));
      await sendRating(i);
      label.innerText = "Thanks for your feedback";
    };
    stars.push(star);
    ratingDiv.appendChild(star);
  }

  chatBox.appendChild(ratingDiv);
  scrollToBottom();
}

async function fetchJson(path, payload, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(endpoint(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out.");
    }
    if (error instanceof TypeError) {
      throw new Error(
        `Could not reach ${apiBase}. Check CORS, DNS, network, and that this page is served over http(s) not file://.`
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function testApiConnection() {
  if (testApiBtn) testApiBtn.disabled = true;
  setApiStatus(`Testing ${apiBase} ...`, "status-unknown");

  try {
    const response = await fetch(endpoint("/health"), { method: "GET" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (data && data.status === "ok") {
      setApiStatus(`Connected to ${apiBase} (health: ok).`, "status-ok");
      return true;
    }
    setApiStatus(`Connected to ${apiBase}, but health payload is unexpected.`, "status-warn");
    return false;
  } catch (error) {
    if (window.location.protocol === "https:" && apiBase.startsWith("http://")) {
      setApiStatus(
        `Connection blocked: page is HTTPS but API is HTTP (${apiBase}). Use an HTTPS API URL.`,
        "status-bad"
      );
      return false;
    }
    const msg =
      error instanceof TypeError
        ? `Connection failed for ${apiBase}: Failed to fetch (likely DNS/CORS/network).`
        : `Connection failed for ${apiBase}: ${error.message}`;
    setApiStatus(msg, "status-bad");
    return false;
  } finally {
    if (testApiBtn) testApiBtn.disabled = false;
  }
}

async function probeApiHealth(baseUrl) {
  const normalized = normalizeApiBase(baseUrl);
  if (!normalized) return false;
  try {
    const response = await fetch(`${normalized}/health`, { method: "GET" });
    if (response.status === 404 && normalized === SAME_ORIGIN_BASE) {
      setApiStatus(
        `The current site (${SAME_ORIGIN_BASE}) is a static server, not your API (/health returned 404).`,
        "status-warn"
      );
      return false;
    }
    if (!response.ok) return false;
    const data = await response.json();
    return Boolean(data && data.status === "ok");
  } catch (error) {
    return false;
  }
}

async function sendMessage() {
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";
  input.focus();
  if (sendBtn) sendBtn.disabled = true;

  const typingBubble = addTypingBubble();

  try {
    const data = await fetchJson("/chat", {
      query: text,
      session_id: sessionId,
      k: 5,
    });
    setApiStatus(`Connected to ${apiBase}.`, "status-ok");
    if (typingBubble) typingBubble.remove();
    addMessage(data.answer || "No response available.", "ai");
    addSources(data.sources || []);
    addRatingStars();
  } catch (error) {
    if (typingBubble) typingBubble.remove();
    setApiStatus(error.message, "status-bad");
    addMessage(`Error: ${error.message}`, "ai");
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

async function sendRating(value) {
  try {
    await fetchJson("/rate", { rating: value }, 10000);
  } catch (error) {
    console.error("Rating failed:", error);
  }
}

function renderSearchResults(matches = [], query = "") {
  if (!searchResults) return;
  searchResults.innerHTML = "";

  if (!Array.isArray(matches) || !matches.length) {
    const empty = document.createElement("div");
    empty.className = "search-empty";
    empty.innerText = query ? `No matches found for "${query}".` : "Search results will appear here.";
    searchResults.appendChild(empty);
    return;
  }

  matches.slice(0, 5).forEach((match, index) => {
    const item = document.createElement("article");
    item.className = "search-item";

    const title = match.source_name || match.source_file || `Match ${index + 1}`;
    const sourceFile = match.source_file || "Unknown file";
    const chunkSize = Number(match.chunk_size) || 0;
    const sourceUrl = match.source_url || "";
    const text = match.full_text || "";
    const excerpt = text.length > 520 ? `${text.slice(0, 520)}...` : text;

    item.innerHTML = `
      <div class="search-item-title">${escapeHtml(title)}</div>
      <div class="search-item-meta">${escapeHtml(sourceFile)} | chunk: ${chunkSize}${sourceUrl ? ` | <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">open source</a>` : ""}</div>
      <p class="search-item-text">${escapeHtml(excerpt)}</p>
    `;

    searchResults.appendChild(item);
  });
}

async function runSemanticSearch() {
  if (!searchInput || !searchBtn || !searchResults) return;

  const query = searchInput.value.trim();
  if (!query) {
    renderSearchResults([], "");
    return;
  }

  searchBtn.disabled = true;
  searchBtn.innerText = "Searching...";
  searchResults.innerHTML = '<div class="search-empty">Searching...</div>';

  try {
    const data = await fetchJson("/search", { query, k: 5 });
    setApiStatus(`Connected to ${apiBase}.`, "status-ok");
    renderSearchResults(data.matches || [], query);
  } catch (error) {
    setApiStatus(error.message, "status-bad");
    searchResults.innerHTML = `<div class="search-empty">Search failed: ${escapeHtml(error.message)}</div>`;
  } finally {
    searchBtn.disabled = false;
    searchBtn.innerText = "Search";
  }
}

function initChatUI() {
  if (apiBaseInput) apiBaseInput.value = apiBase;

  if (sendBtn) sendBtn.addEventListener("click", sendMessage);
  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  if (searchBtn) searchBtn.addEventListener("click", runSemanticSearch);
  if (searchInput) {
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runSemanticSearch();
      }
    });
  }

  if (applyApiBtn) {
    applyApiBtn.addEventListener("click", () => {
      applyApiBase(apiBaseInput ? apiBaseInput.value : "");
      if (window.location.protocol === "https:" && apiBase.startsWith("http://")) {
        setApiStatus(
          `Blocked by browser mixed-content rules: page is HTTPS but API is HTTP (${apiBase}).`,
          "status-warn"
        );
        return;
      }
      testApiConnection();
    });
  }

  if (testApiBtn) {
    testApiBtn.addEventListener("click", testApiConnection);
  }

  setApiStatus(`Using API base ${apiBase}.`, "status-unknown");

  (async () => {
    const candidates = [apiBase, ...API_FALLBACKS].filter(
      (value, index, arr) => Boolean(value) && arr.indexOf(value) === index
    );

    const primaryOk = await probeApiHealth(apiBase);
    if (primaryOk) {
      setApiStatus(`Connected to ${apiBase} (health: ok).`, "status-ok");
      return;
    }

    for (const candidate of candidates) {
      if (candidate === apiBase) continue;
      if (window.location.protocol === "https:" && candidate.startsWith("http://")) continue;
      const ok = await probeApiHealth(candidate);
      if (ok) {
        applyApiBase(candidate);
        setApiStatus(
          `Primary API unreachable. Switched to reachable API: ${candidate}`,
          "status-warn"
        );
        return;
      }
    }

    setApiStatus(
      `Connection failed for ${apiBase}: Failed to fetch. Verify DNS/CORS or switch API base to a reachable server.`,
      "status-bad"
    );
  })();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChatUI);
} else {
  initChatUI();
}
