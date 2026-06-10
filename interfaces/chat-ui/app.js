const SAME_ORIGIN_BASE = window.location.origin;
const REMOTE_API_BASE = "https://helpcentre-dsi-mdr.emergentai.ug";
const DEFAULT_API_BASE = window.__API_BASE__ || REMOTE_API_BASE;
const API_FALLBACKS = ["http://localhost:8000", "http://127.0.0.1:8000"];
let apiBase = normalizeApiBase(DEFAULT_API_BASE);

const DEFAULT_QUERY = "How do I reset my password?";
const DEFAULT_ANSWER_TEXT = `To reset your password on the MDR web platform, follow the steps below:

1. Go to the login page.
2. Click on "Forgot Password?" below the password field.
3. Enter the email address associated with your account.
4. Check your email for a password reset link.
5. Click the link and follow the instructions to set a new password.
6. Use your new password to log in to the platform.

If you do not receive the email, please check your spam or junk folder.
If the issue persists, contact support for further assistance.`;

const DEFAULT_SOURCES = [
  {
    title: "MDR Web Platform - User Guide",
    label: "Help Article",
    section: "Section 2.3",
    snippet:
      'To reset your password, users must click on the "Forgot Password?" link on the login page and enter the email associated with their account.',
    url: "https://mdrweb.emergentai.ug/help/reset-password",
  },
  {
    title: "MDR Web Platform - Account Management",
    label: "Help Article",
    section: "Section 3.1",
    snippet:
      "Account recovery is done via email verification. Ensure the email used during registration is active to receive reset instructions.",
    url: "https://mdrweb.emergentai.ug/help/account-management",
  },
  {
    title: "MDR Web Platform - FAQ",
    label: "Help Article",
    section: "Q&A 12",
    snippet:
      "If you do not receive the reset email, check your spam folder or contact support if the problem continues.",
    url: "https://mdrweb.emergentai.ug/help/faq",
  },
];

const quickGuides = [
  {
    icon: "✈",
    title: "Getting Started",
    text: "New to the MDR web platform? Learn the basics and set up your account.",
  },
  {
    icon: "▶",
    title: "Demo Videos",
    text: "Watch step-by-step videos to see how the platform works.",
  },
  {
    icon: "★",
    title: "Platform Features",
    text: "Explore key features and how they support TB management.",
  },
];

const faqs = [
  {
    question: "How do I create an account on the MDR web platform?",
    answer: "Open the registration page, enter your details, verify your email, and follow the on-screen prompts to complete setup.",
  },
  {
    question: "How do I reset my password?",
    answer: "On the login screen select 'Forgot Password?', enter your registered email, then follow the reset link sent to your inbox.",
  },
  {
    question: "How do I log in to the MDR web platform?",
    answer: "Go to the login page, enter your email and password, and complete any required two-factor or confirmation steps.",
  },
  {
    question: "What are the early signs of tuberculosis (TB)?",
    answer: "Watch for a persistent cough (>2 weeks), unexplained weight loss, fever, night sweats, and fatigue; seek clinical assessment if present.",
  },
];

const feedbackButtons = Array.from(document.querySelectorAll("[data-feedback]"));
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const answerBox = document.getElementById("answer-box");
const answerMeta = document.getElementById("answer-meta");
const sourcesList = document.getElementById("sources-list");
const faqViewBtn = document.getElementById("faq-view-btn");
const quickGuidesContainer = document.getElementById("quick-guides");
const faqList = document.getElementById("faq-list");
const popularSearchButtons = Array.from(document.querySelectorAll(".search-chip"));
const answerTitle = document.getElementById("answer-title");
const pageView = document.body?.dataset?.view || "landing";
const isLandingPage = pageView === "landing";
const isResultsPage = pageView === "results";

function normalizeApiBase(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function endpoint(path) {
  return `${apiBase}${path}`;
}

function buildPageUrl(pageName, query = "") {
  const url = new URL(pageName, window.location.href);
  if (query) {
    url.searchParams.set("q", query);
  }
  return url.toString();
}

function getInitialQuery() {
  const params = new URLSearchParams(window.location.search);
  return String(params.get("q") || "").trim();
}

function navigateToResults(query) {
  window.location.href = buildPageUrl("results.html", query);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setAnswerState(html, meta = "") {
  if (answerBox) answerBox.innerHTML = html;
  if (answerMeta) answerMeta.innerText = meta;
}

function formatInline(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function renderAnswerHtml(text) {
  const normalized = String(text || "").trim();
  if (!normalized) {
    return '<div class="answer-empty">No answer is available right now.</div>';
  }

  const blocks = normalized.split(/\n\s*\n/);
  const html = blocks
    .map((block) => {
      const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
      const numbered = lines.length > 0 && lines.every((line) => /^\d+\.\s+/.test(line));
      const bulleted = lines.length > 0 && lines.every((line) => /^[-*]\s+/.test(line));
      if (numbered) {
        const items = lines
          .map((line) => line.replace(/^\d+\.\s+/, ""))
          .map((line) => `<li>${formatInline(line)}</li>`)
          .join("");
        return `<ol>${items}</ol>`;
      }
      if (bulleted) {
        const items = lines
          .map((line) => line.replace(/^[-*]\s+/, ""))
          .map((line) => `<li>${formatInline(line)}</li>`)
          .join("");
        return `<ul>${items}</ul>`;
      }
      return `<p>${formatInline(lines.join(" "))}</p>`;
    })
    .join("");

  return `<div class="answer-content">${html}</div>`;
}

function renderSources(sources = []) {
  if (!sourcesList) return;
  sourcesList.innerHTML = "";

  const sourceItems = Array.isArray(sources) && sources.length ? sources.slice(0, 3) : DEFAULT_SOURCES;

  sourceItems.forEach((source, index) => {
    const card = document.createElement("article");
    card.className = "source-card";

    const title = source.title || source.source_name || `Source ${index + 1}`;
    const label = source.label || source.source_type || "Help Article";
    const section = source.section || source.chapter || "";
    const url = source.url || source.source_url || "";
    const snippet = source.snippet || source.full_text || "";

    card.innerHTML = `
      <div class="source-header">
        <div>
          <div class="source-title">${escapeHtml(title)}</div>
          <div class="source-meta">${escapeHtml(section)}</div>
        </div>
        <span class="source-badge">${escapeHtml(label)}</span>
      </div>
      <p class="source-snippet">${escapeHtml(snippet)}</p>
      ${url ? `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open source <span aria-hidden="true">↗</span></a>` : ""}
    `;

    sourcesList.appendChild(card);
  });
}

function renderLoadingState(query) {
  setAnswerState(
    '<div class="answer-loading"><span></span><span></span><span></span></div>',
    "Searching for the best answer..."
  );
  renderSources([]);
}

function renderDefaultState() {
  if (searchInput) searchInput.value = "";
  if (answerTitle) answerTitle.innerText = DEFAULT_QUERY;
  setAnswerState(renderAnswerHtml(DEFAULT_ANSWER_TEXT), "To reset your password on the MDR web platform, follow the steps below:");
  renderSources(DEFAULT_SOURCES);
}

function revealAllFaqs() {
  if (!faqList) return;
  faqList.querySelectorAll(".faq-item").forEach((item) => {
    item.classList.add("open");
    const button = item.querySelector(".faq-question");
    if (button) {
      button.setAttribute("aria-expanded", "true");
    }
  });

  faqList.scrollIntoView({ behavior: "smooth", block: "start" });
}

function addRatingStars() {
  const slot = document.getElementById("rating-slot");
  if (!slot) return;

  slot.innerHTML = "";

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

  slot.appendChild(ratingDiv);
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

async function probeApiHealth(baseUrl) {
  const normalized = normalizeApiBase(baseUrl);
  if (!normalized) return false;
  try {
    const response = await fetch(`${normalized}/health`, { method: "GET" });
    if (response.status === 404 && normalized === SAME_ORIGIN_BASE) {
      return false;
    }
    if (!response.ok) return false;
    const data = await response.json();
    return Boolean(data && data.status === "ok");
  } catch (error) {
    return false;
  }
}

async function sendRating(value) {
  try {
    await fetchJson("/rate", { rating: value }, 10000);
  } catch (error) {
    console.error("Rating failed:", error);
  }
}

async function runAiSearch(queryOverride = "") {
  if (!searchInput || !searchBtn) return;

  const query = String(queryOverride || searchInput.value || "").trim();
  if (!query) {
    if (isLandingPage) {
      return;
    }
    renderDefaultState();
    return;
  }

  if (isLandingPage) {
    navigateToResults(query);
    return;
  }

  if (searchInput) searchInput.value = query;
  if (answerTitle) answerTitle.innerText = query;
  searchBtn.disabled = true;
  searchBtn.innerText = "Thinking...";
  renderLoadingState(query);

  try {
    const retrieval = await fetchJson(`/api/search/general`, { query, k: 5 });
    const answerText = retrieval.answer || retrieval.response || retrieval.text || DEFAULT_ANSWER_TEXT;
    const sourceItems = retrieval.sources || retrieval.matches || DEFAULT_SOURCES;
    setAnswerState(renderAnswerHtml(answerText), retrieval.message || "To reset your password on the MDR web platform, follow the steps below:");
    renderSources(sourceItems);
    addRatingStars();
  } catch (error) {
    console.error("Search failed:", error);
    setAnswerState(
      renderAnswerHtml(DEFAULT_ANSWER_TEXT),
      "To reset your password on the MDR web platform, follow the steps below:"
    );
    renderSources(DEFAULT_SOURCES);
    addRatingStars();
  } finally {
    searchBtn.disabled = false;
    searchBtn.innerText = "Search";
  }
}

function initChatUI() {
  renderQuickGuides();
  renderFaqs();

  if (isResultsPage) {
    const initialQuery = getInitialQuery() || DEFAULT_QUERY;
    if (searchInput) searchInput.value = initialQuery;
    runAiSearch(initialQuery);
  }

  popularSearchButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const query = button.dataset.query || button.innerText;
      if (isLandingPage) {
        navigateToResults(query);
        return;
      }
      if (searchInput) {
        searchInput.value = query;
        searchInput.focus();
      }
      runAiSearch(query);
    });
  });

  feedbackButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const value = button.dataset.feedback === "helpful" ? 1 : 0;
      await sendRating(value);
    });
  });

  if (searchBtn) searchBtn.addEventListener("click", () => runAiSearch());
  if (searchInput) {
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runAiSearch();
      }
    });
  }

  if (faqViewBtn) faqViewBtn.addEventListener("click", revealAllFaqs);
}

function renderQuickGuides() {
  if (!quickGuidesContainer) return;
  quickGuidesContainer.innerHTML = "";

  quickGuides.forEach((guide) => {
    const card = document.createElement("article");
    card.className = "guide-card";
    card.innerHTML = `
      <div class="guide-icon" aria-hidden="true">${escapeHtml(guide.icon)}</div>
      <h4 class="guide-title">${escapeHtml(guide.title)}</h4>
      <p class="guide-text">${escapeHtml(guide.text)}</p>
      <div class="guide-footer"><span class="guide-arrow">→</span></div>
    `;
    quickGuidesContainer.appendChild(card);
  });
}

function renderFaqs() {
  if (!faqList) return;
  faqList.innerHTML = "";

  faqs.forEach((faq) => {
    const item = document.createElement("article");
    item.className = "faq-item";
    item.innerHTML = `
      <button type="button" class="faq-question" aria-expanded="false">
        <span>${escapeHtml(faq.question)}</span>
        <span aria-hidden="true">⌄</span>
      </button>
      <div class="faq-answer">${escapeHtml(faq.answer)}</div>
    `;

    const button = item.querySelector(".faq-question");
    button.addEventListener("click", () => {
      const isOpen = item.classList.contains("open");
      faqList.querySelectorAll(".faq-item").forEach((otherItem) => {
        otherItem.classList.remove("open");
        const otherButton = otherItem.querySelector(".faq-question");
        if (otherButton) {
          otherButton.setAttribute("aria-expanded", "false");
        }
      });
      if (!isOpen) {
        item.classList.add("open");
        button.setAttribute("aria-expanded", "true");
      }
    });

    faqList.appendChild(item);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChatUI);
} else {
  initChatUI();
}
