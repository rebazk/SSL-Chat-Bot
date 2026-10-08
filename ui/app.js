const body = document.body;
const launcher = document.getElementById("beacon-launcher");
const openPanelButton = document.getElementById("open-panel");
const closePanelButton = document.getElementById("close-panel");
const backdrop = document.getElementById("panel-backdrop");
const panel = document.getElementById("beacon-panel");
const form = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const questionCounter = document.getElementById("question-counter");
const resultsState = document.getElementById("results-state");
const topicPicker = document.getElementById("topic-picker");
const questionChips = document.getElementById("question-chips");
const QUESTION_LIMIT = Number(questionInput?.getAttribute("maxlength") || 400);
const ASK_FETCH_TIMEOUT_MS = 130_000;
const SESSION_STORAGE_KEY = "beacon_session_id_v1";
const MAX_GUIDED_MATCHES = 10;

const KEYWORD_ALIASES = {
  rep: ["report", "reports", "publication", "paper", "study", "studies"],
  dir: ["director", "lead", "leader", "staff", "people"],
  ssl: ["ssl", "sustainable", "solutions", "lab", "sustainable solutions lab"],
  mvp: ["mvp", "municipal", "vulnerability", "preparedness"],
  fin: ["finance", "financing", "funding", "budget", "grant", "grants"],
  res: ["resilience", "research", "researchers", "report"]
};

const GUIDED_TOPICS = [
  {
    id: "mission",
    label: "Mission",
    description: "SSL's purpose, framing, and core public-facing identity.",
    questions: [
      {
        label: "What does SSL focus on?",
        question: "What is the Sustainable Solutions Lab, and what does it focus on?"
      },
      {
        label: "Why SSL?",
        question: "This center seems to be all about climate justice. Why is it called Sustainable Solutions Lab?"
      },
      {
        label: "Who works here?",
        question: "Who does the research at SSL?"
      }
    ]
  },
  {
    id: "people",
    label: "People",
    description: "Staff, scholars, and who is involved in the lab.",
    questions: [
      {
        label: "Current director",
        question: "Who is the current director of the Sustainable Solutions Lab?"
      },
      {
        label: "Researchers",
        question: "Who does the research at SSL?"
      },
      {
        label: "Opportunities",
        question: "Does SSL offer any fellowships or post-doc opportunities?"
      }
    ]
  },
  {
    id: "reports",
    label: "Reports",
    description: "Direct questions about reports and public publications.",
    questions: [
      {
        label: "Who Counts?",
        question: "What does the report 'Who Counts in Climate Resilience?' identify as the two transient populations it focuses on?"
      },
      {
        label: "East Boston",
        question: "What concerns does the East Boston resilience work raise about climate adaptation, gentrification, and displacement?"
      },
      {
        label: "Summaries",
        question: "Summarize SSL's work in the last five years."
      }
    ]
  },
  {
    id: "policy",
    label: "Policy",
    description: "Financing, governance, and resilience planning questions.",
    questions: [
      {
        label: "Financing",
        question: "What kinds of funding mechanisms are discussed in SSL's climate resilience financing work?"
      },
      {
        label: "MVP program",
        question: "What does the SSL report say about the Massachusetts Municipal Vulnerability Preparedness (MVP) Program in the Greater Boston region?"
      },
      {
        label: "Waste / recycling",
        question: "Has SSL done anything on waste management or recycling?"
      }
    ]
  }
];

let selectedTopicId = GUIDED_TOPICS[0]?.id || "";
let lastAnsweredQuestionNormalized = "";
let elementBeforePanelOpen = null;
const sessionId = initSessionId();

function initSessionId() {
  try {
    const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing && /^[a-zA-Z0-9_-]{8,64}$/.test(existing)) {
      return existing;
    }
  } catch {
    // no-op if storage is unavailable
  }

  let generated = "";
  if (window.crypto?.randomUUID) {
    generated = window.crypto.randomUUID().replaceAll("-", "");
  } else {
    generated = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
  }

  generated = generated.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 64);
  try {
    window.localStorage.setItem(SESSION_STORAGE_KEY, generated);
  } catch {
    // no-op if storage is unavailable
  }
  return generated;
}

function normalizeQuestionKey(q) {
  return String(q ?? "").trim().replace(/\s+/g, " ");
}

function tokenizeAlnumWords(text) {
  return String(text ?? "")
    .toLowerCase()
    .match(/[a-z0-9]+/g) || [];
}

function syncTopicTabIndexes() {
  if (!topicPicker) {
    return;
  }

  const chips = topicPicker.querySelectorAll("button[data-topic-id]");
  chips.forEach((chip) => {
    chip.tabIndex = chip.classList.contains("selected") ? 0 : -1;
  });
}

function setPanelOpen(isOpen) {
  if (isOpen) {
    elementBeforePanelOpen = document.activeElement;
  }

  body.classList.toggle("panel-open", isOpen);
  panel.setAttribute("aria-hidden", String(!isOpen));
  backdrop.hidden = !isOpen;

  if (isOpen) {
    window.setTimeout(() => {
      questionInput?.focus();
    }, 50);
  } else {
    const ref = elementBeforePanelOpen;
    elementBeforePanelOpen = null;
    if (ref && typeof ref.focus === "function") {
      window.requestAnimationFrame(() => {
        ref.focus();
      });
    }
  }
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

function clickTargetElement(event) {
  const t = event?.target;
  if (!t) {
    return null;
  }

  if (t.nodeType === Node.ELEMENT_NODE) {
    return t;
  }

  if (t.nodeType === Node.TEXT_NODE) {
    return t.parentElement;
  }

  return t.parentElement;
}

function shortenText(text, maxLength = 220) {
  if (!text || text.length <= maxLength) {
    return text || "";
  }

  return `${text.slice(0, maxLength - 3).trimEnd()}...`;
}

function normalizeCitationKey(citation) {
  return (citation || "")
    .replace(/\s*\(p\.\s*\d+\)\s*$/i, "")
    .trim()
    .toLowerCase();
}

function formatCitationLabel(citation) {
  if (!citation) {
    return "Source";
  }

  if (citation.startsWith("http://") || citation.startsWith("https://")) {
    try {
      const url = new URL(citation);
      const path = url.pathname.replace(/\/$/, "");
      const compact = path ? `${url.hostname}${path}` : url.hostname;
      return shortenText(compact, 54);
    } catch {
      return shortenText(citation, 54);
    }
  }

  return shortenText(citation, 64);
}

function safeHttpUrlForLink(raw) {
  if (!raw || typeof raw !== "string") {
    return "";
  }

  const trimmed = raw.trim();
  if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
    return "";
  }

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return "";
    }

    if (!parsed.hostname) {
      return "";
    }

    return parsed.toString();
  } catch {
    return "";
  }
}

function sanitizeSnippet(text) {
  let cleaned = String(text || "");

  cleaned = cleaned.replace(/\r\n/g, "\n");
  cleaned = cleaned.replace(/^\s*#+\s.*?snapshot.*?(?:\n+|$)/i, "");
  cleaned = cleaned.replace(/\bSource URL:\s*\S+/gi, "");
  cleaned = cleaned.replace(/\bCaptured:\s*[^\n]+/gi, "");
  cleaned = cleaned.replace(/\bTitle:\s*[^\n]+/gi, "");
  cleaned = cleaned.replace(/\bSnapshot Source URL:\s*\S+/gi, "");
  cleaned = cleaned.replace(/\n{2,}/g, "\n");
  cleaned = cleaned.replace(/\s+/g, " ");

  return cleaned.trim();
}

function formatEvidenceSnippet(text, maxLength) {
  const cleaned = sanitizeSnippet(text);
  if (!cleaned) {
    return "No preview text available for this evidence card.";
  }

  return shortenText(cleaned, maxLength);
}

function buildCitationEntries(payload) {
  const exactUrlMap = new Map();
  const normalizedUrlMap = new Map();

  (payload.top_results || []).forEach((result) => {
    const citation = result?.citation || "";
    const href = safeHttpUrlForLink(
      result?.source_url || ((citation.startsWith("http://") || citation.startsWith("https://")) ? citation : "")
    );

    if (!citation || !href) {
      return;
    }

    if (!exactUrlMap.has(citation)) {
      exactUrlMap.set(citation, href);
    }

    const normalized = normalizeCitationKey(citation);
    if (normalized && !normalizedUrlMap.has(normalized)) {
      normalizedUrlMap.set(normalized, href);
    }
  });

  return (payload.citations || []).map((citation) => {
    const href = safeHttpUrlForLink(
      (citation.startsWith("http://") || citation.startsWith("https://"))
        ? citation
        : exactUrlMap.get(citation) || normalizedUrlMap.get(normalizeCitationKey(citation)) || ""
    );

    return {
      citation,
      href,
      label: formatCitationLabel(citation)
    };
  });
}

function renderResultsEmptyHint(options = {}) {
  const stale = Boolean(options.stale);
  resultsState.setAttribute("aria-busy", "false");
  resultsState.classList.add("empty");
  resultsState.innerHTML = `
    <div class="empty-state">
      <h4>Evidence-first responses</h4>
      <p>
        Uses the current local SSL corpus and returns an answer, source links, and the strongest
        retrieved evidence together.
      </p>
      <p>
        For the cleanest review experience, begin with one of the suggested questions and then
        branch into your own follow-ups.
      </p>
      ${
        stale
          ? `<p class="empty-stale-hint">That answer was for a different question. Press <strong>Ask</strong> when you are ready to search again.</p>`
          : ""
      }
    </div>
  `;
}

function refreshResultsForDraft() {
  if (!questionInput) {
    return;
  }

  const draft = normalizeQuestionKey(questionInput.value);
  if (draft === lastAnsweredQuestionNormalized) {
    return;
  }

  const hadAnswer = lastAnsweredQuestionNormalized !== "";
  lastAnsweredQuestionNormalized = "";
  renderResultsEmptyHint({ stale: hadAnswer });
}

function renderLoading(question) {
  resultsState.classList.remove("empty");
  resultsState.setAttribute("aria-busy", "true");
  resultsState.innerHTML = `
    <div class="loading" role="status">
      <div class="loading-title">Searching SSL evidence</div>
      <p class="loading-question">${escapeHtml(question)}</p>
    </div>
  `;
}

function renderError(message) {
  lastAnsweredQuestionNormalized = "";
  resultsState.setAttribute("aria-busy", "false");
  resultsState.classList.remove("empty");
  resultsState.innerHTML = `
    <div class="error-box" role="alert">
      <span class="error-title">Could not complete this request.</span>
      ${escapeHtml(message)}
    </div>
  `;
}

function syncQuestionCounter() {
  if (!questionCounter || !questionInput) {
    return;
  }

  const currentLength = questionInput.value.length;
  questionCounter.textContent = `${currentLength} / ${QUESTION_LIMIT}`;
  questionCounter.classList.toggle("limit-near", currentLength >= QUESTION_LIMIT - 40);
}

function renderTopicPicker() {
  if (!topicPicker) {
    return;
  }

  topicPicker.innerHTML = GUIDED_TOPICS.map((topic) => {
    const isSelected = topic.id === selectedTopicId;
    return `
      <button
        type="button"
        role="radio"
        class="topic-chip ${isSelected ? "selected" : ""}"
        aria-checked="${String(isSelected)}"
        data-topic-id="${escapeHtml(topic.id)}"
        title="${escapeHtml(topic.description)}"
      >
        ${escapeHtml(topic.label)}
      </button>
    `;
  }).join("");

  syncTopicTabIndexes();
}

function buildQuestionChipPool() {
  const rows = [];
  GUIDED_TOPICS.forEach((topic) => {
    topic.questions.forEach((item, index) => {
      rows.push({
        topicId: topic.id,
        topicLabel: topic.label,
        label: item.label,
        question: item.question,
        index
      });
    });
  });
  return rows;
}

function getGuidedMatches(query) {
  const q = String(query ?? "").trim().toLowerCase();
  const pool = buildQuestionChipPool();
  if (!q || q.length < 2) {
    return [];
  }

  const rawTokens = tokenizeAlnumWords(q);
  const qTokens = [...new Set(
    rawTokens.flatMap((token) => [token, ...(KEYWORD_ALIASES[token] || [])])
  )];

  const byQuestion = new Map();
  for (const row of pool) {
    const key = normalizeQuestionKey(row.question).toLowerCase();
    if (!byQuestion.has(key)) {
      byQuestion.set(key, row);
    }
  }
  const dedupedPool = [...byQuestion.values()];

  return dedupedPool
    .map((row) => {
      const haystack = `${row.topicLabel} ${row.label} ${row.question}`.toLowerCase();
      const tokenHits = qTokens.filter((t) => t.length >= 2 && haystack.includes(t)).length;
      const startsWith = haystack.includes(` ${q}`) || haystack.startsWith(q);
      const direct = haystack.includes(q);
      const score = (direct ? 4 : 0) + (startsWith ? 2 : 0) + tokenHits;
      return { row, score };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || a.row.label.localeCompare(b.row.label))
    .slice(0, MAX_GUIDED_MATCHES)
    .map((x) => x.row);
}

function renderQuestionChips() {
  if (!questionChips) {
    return;
  }

  const inputQuery = String(questionInput?.value || "");
  const filtered = getGuidedMatches(inputQuery);
  const topic = GUIDED_TOPICS.find((entry) => entry.id === selectedTopicId) || GUIDED_TOPICS[0];
  if (!topic && filtered.length === 0) {
    questionChips.innerHTML = "";
    return;
  }

  const chipsToRender = filtered.length > 0
    ? filtered
    : topic.questions.map((item, index) => ({
        topicId: topic.id,
        topicLabel: topic.label,
        label: item.label,
        question: item.question,
        index
      }));

  questionChips.innerHTML = chipsToRender
    .map(
      (item) => `
    <button type="button" class="sample-chip compact" data-topic-id="${escapeHtml(item.topicId)}" data-q-index="${item.index}" title="${escapeHtml(item.topicLabel)}">
      ${escapeHtml(item.label)}
    </button>
  `
    )
    .join("");
}

function applyQuestionFromChipIndex(index, topicId = selectedTopicId) {
  const topic = GUIDED_TOPICS.find((entry) => entry.id === topicId) || GUIDED_TOPICS[0];
  const item = topic?.questions?.[index];
  if (!item || !questionInput) {
    return;
  }

  questionInput.value = item.question;
  syncQuestionCounter();
  refreshResultsForDraft();
  questionInput.focus();
  void askBeacon(item.question.trim());
}

function setSelectedTopic(topicId) {
  if (!GUIDED_TOPICS.some((topic) => topic.id === topicId)) {
    return;
  }

  selectedTopicId = topicId;
  renderTopicPicker();
  renderQuestionChips();

  const topic = GUIDED_TOPICS.find((t) => t.id === topicId);
  if (topic?.questions?.length && questionInput) {
    questionInput.value = topic.questions[0].question;
    syncQuestionCounter();
    if (body.classList.contains("panel-open")) {
      questionInput.focus();
    }
  }

  refreshResultsForDraft();
}

function renderResults(payload) {
  const citationEntries = buildCitationEntries(payload);
  const citationCount = citationEntries.length;
  const rawEvidenceResults = (payload.top_results || []).slice(0, 10);
  const citedKeys = new Set(
    (payload.citations || []).map((c) => normalizeCitationKey(String(c || ""))).filter(Boolean)
  );

  const evidenceResults = (() => {
    const questionText = String(payload.question || questionInput?.value || "");
    const questionTokens = new Set(tokenizeAlnumWords(questionText).filter((t) => t.length >= 4));
    const scoreByOverlap = (snippet) => {
      const tokens = tokenizeAlnumWords(snippet).filter((t) => t.length >= 4);
      let hits = 0;
      for (const t of tokens) {
        if (questionTokens.has(t)) {
          hits += 1;
        }
      }
      return hits;
    };

    const preferred = [];
    const fallback = [];
    const seen = new Set();

    for (const result of rawEvidenceResults) {
      const key = normalizeCitationKey(String(result?.citation || ""));
      const id = `${key}::${String(result?.snippet || "").slice(0, 120)}`;
      if (seen.has(id)) {
        continue;
      }
      seen.add(id);

      if (payload.supported && citedKeys.size > 0 && key && citedKeys.has(key)) {
        preferred.push(result);
      } else {
        fallback.push(result);
      }
    }

    // If we have a single "best source", keep the evidence drawer tightly scoped to that source.
    // This avoids dumping unrelated passages from the same long webpage or other high-scoring docs.
    const singleSourceMode = payload.supported && citedKeys.size === 1;

    const orderWithin = (items) => {
      const withScores = items.map((r) => ({
        r,
        overlap: scoreByOverlap(String(r?.snippet || "")),
        hasPreview: Boolean(String(r?.snippet || "").trim())
      }));

      withScores.sort((a, b) => {
        if (a.hasPreview !== b.hasPreview) return a.hasPreview ? -1 : 1;
        if (a.overlap !== b.overlap) return b.overlap - a.overlap;
        return String(a.r?.citation || "").localeCompare(String(b.r?.citation || ""));
      });

      const ranked = withScores.map((x) => x.r);
      // Prefer cards with actual preview text; allow no-preview only if we have too few.
      const withPreview = ranked.filter((r) => String(r?.snippet || "").trim());
      const noPreview = ranked.filter((r) => !String(r?.snippet || "").trim());
      return withPreview.concat(noPreview);
    };

    const preferredRanked = orderWithin(preferred);
    if (singleSourceMode) {
      return preferredRanked.slice(0, 4);
    }

    const fallbackRanked = orderWithin(fallback);
    const merged = preferredRanked.concat(fallbackRanked);
    return merged.slice(0, 5);
  })();
  const evidenceCount = evidenceResults.length;
  const evidenceHeading = payload.supported ? "Supporting evidence" : "Closest retrieved passages";
  const citationSummary = citationCount === 1 ? "1 source" : `${citationCount} sources`;
  const sourceButtonLabel = citationCount > 0 ? `All sources (${citationCount})` : "All sources";
  const evidenceButtonLabel = payload.supported
    ? `Why this answer (${evidenceCount})`
    : `Closest matches (${evidenceCount})`;
  const primarySource = citationEntries[0] || null;
  const statusClass = payload.supported ? "supported" : "unsupported";
  const statusLabel = payload.supported ? "Grounded" : "Not enough support";
  const note = payload.supported
    ? (citationCount > 1
        ? `Retrieval lines up across ${citationSummary}.`
        : "Direct match in the public SSL corpus.")
    : "Could not verify a confident direct answer in the current corpus.";
  const answerDirection = payload.supported
    ? (citationCount > 1 ? "Based on multiple SSL sources" : "Based on one strongest SSL source")
    : "Closest source shown below for redirection";
  const memoryNote = payload.memory_applied
    ? "Used short session memory to resolve this follow-up."
    : "";
  const supportLine = payload.supported && citationCount > 1
    ? `Also supported by ${citationCount - 1} additional ${citationCount - 1 === 1 ? "source" : "sources"}.`
    : "";
  const askedQuestion = String(payload.question || "").trim();

  const citationsMarkup = citationEntries.map((entry) => {
    const safeCitation = escapeHtml(entry.citation);
    const safeLabel = escapeHtml(entry.label);
    const safeHref = escapeHtml(entry.href);

    if (entry.href) {
      return `
        <a class="source-link-card" href="${safeHref}" target="_blank" rel="noreferrer" title="${safeCitation}">
          <span class="source-link-title">${safeLabel}</span>
          <span class="source-link-meta">Open source</span>
        </a>
      `;
    }

    return `
      <div class="source-link-card static" title="${safeCitation}">
        <span class="source-link-title">${safeLabel}</span>
        <span class="source-link-meta">Label only</span>
      </div>
    `;
  }).join("");

  const evidenceMarkup = evidenceResults.map((result) => {
    const citation = escapeHtml(result.citation || "Source");
    const title = escapeHtml(formatCitationLabel(result.citation || "Source"));
    const snippet = escapeHtml(formatEvidenceSnippet(result.snippet || "", 240));
    const safeUrl = safeHttpUrlForLink(result.source_url || "");
    const href = safeUrl ? escapeHtml(safeUrl) : "";
    const body = `
      <div class="evidence-meta">
        <strong title="${citation}">${title}</strong>
        ${href ? '<span class="evidence-link-hint">Open source</span>' : ""}
      </div>
      <p>${snippet}</p>
    `;

    if (href) {
      return `
        <a class="evidence-card evidence-card-link" href="${href}" target="_blank" rel="noreferrer">
          ${body}
        </a>
      `;
    }

    return `
      <article class="evidence-card">
        ${body}
      </article>
    `;
  }).join("");

  const primarySourceMarkup = primarySource
    ? (primarySource.href
        ? `
        <a class="primary-source-link" href="${escapeHtml(primarySource.href)}" target="_blank" rel="noreferrer" title="${escapeHtml(primarySource.citation)}">
          <span class="primary-source-kicker">${payload.supported ? "Best source" : "Closest source"}</span>
          <span class="primary-source-label">${escapeHtml(primarySource.label)}</span>
        </a>
      `
      : `
        <div class="primary-source-link static" title="${escapeHtml(primarySource.citation)}">
          <span class="primary-source-kicker">${payload.supported ? "Best source" : "Closest source"}</span>
          <span class="primary-source-label">${escapeHtml(primarySource.label)}</span>
        </div>
      `)
    : "";

  resultsState.setAttribute("aria-busy", "false");
  resultsState.classList.remove("empty");
  resultsState.innerHTML = `
    <div class="result-block">
      <section class="result-summary-card result-answer-card">
        ${askedQuestion ? `
        <section class="result-question" aria-label="Question asked">
          <span class="result-question-label">You asked</span>
          <p class="result-question-text">${escapeHtml(askedQuestion)}</p>
        </section>
        ` : ""}

        <div class="status-stack">
          <div class="status-row">
            <span class="status-chip ${statusClass}">${statusLabel}</span>
            <span class="result-meta-pill">${escapeHtml(citationSummary)}</span>
          </div>
          <p class="status-note">${escapeHtml(note)}</p>
        </div>

        <section class="result-answer">
          <div class="result-section-header simple">
            <h4>Answer</h4>
            <span class="section-helper">${escapeHtml(answerDirection)}</span>
          </div>
          <p class="result-answer-text">${escapeHtml(payload.answer || "No answer returned.")}</p>
        </section>

        ${primarySourceMarkup}
        ${memoryNote ? `<p class="answer-support-line">${escapeHtml(memoryNote)}</p>` : ""}
        ${supportLine ? `<p class="answer-support-line">${escapeHtml(supportLine)}</p>` : ""}

        <div class="result-action-row">
          <button class="drawer-toggle" type="button" aria-expanded="false" data-drawer="sources">
            <span>More sources</span>
            <span class="drawer-toggle-meta">${escapeHtml(sourceButtonLabel)}</span>
          </button>
          <button class="drawer-toggle" type="button" aria-expanded="false" data-drawer="evidence">
            <span>${payload.supported ? "Why this answer" : "Why we're holding back"}</span>
            <span class="drawer-toggle-meta">${escapeHtml(evidenceButtonLabel)}</span>
          </button>
        </div>
      </section>

      <section class="result-summary-card result-drawer-shell">
        <div class="drawer-panel drawer-sources" hidden>
          <div class="result-section-header">
            <h4>Sources</h4>
            <span class="section-helper">Open the original page or report</span>
          </div>
          <div class="source-link-list">${citationsMarkup || '<span class="citation-chip">No citations returned</span>'}</div>
        </div>

        <div class="drawer-panel drawer-evidence" hidden>
          <div class="result-section-header">
            <h4>${escapeHtml(evidenceHeading)}</h4>
            <span class="section-helper">Open a result to inspect the source</span>
          </div>
          <div class="result-evidence-list">${evidenceMarkup || '<p>No evidence cards returned.</p>'}</div>
        </div>
      </section>
    </div>
  `;

  lastAnsweredQuestionNormalized = normalizeQuestionKey(
    payload.question || questionInput?.value || ""
  );
}

async function askBeacon(question) {
  const trimmed = question.trim();
  if (!trimmed) {
    return;
  }

  if (trimmed.length > QUESTION_LIMIT) {
    renderError(`Questions must be ${QUESTION_LIMIT} characters or fewer.`);
    setPanelOpen(true);
    return;
  }

  setPanelOpen(true);
  renderLoading(trimmed);

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), ASK_FETCH_TIMEOUT_MS);
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question: trimmed, top: 5, session_id: sessionId }),
      signal: controller.signal
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.error || `Request failed with status ${response.status}.`);
    }

    const payload = await response.json();
    renderResults(payload);
    questionInput.value = "";
    syncQuestionCounter();
  } catch (error) {
    if (error && error.name === "AbortError") {
      renderError("That request timed out. The local worker may be busy or stuck.");
    } else {
      renderError(error.message || "Could not reach the local SSL backend.");
    }
  } finally {
    window.clearTimeout(timeoutId);
    resultsState.setAttribute("aria-busy", "false");
  }
}

launcher.addEventListener("click", () => setPanelOpen(true));
openPanelButton.addEventListener("click", () => setPanelOpen(true));
closePanelButton.addEventListener("click", () => setPanelOpen(false));
backdrop.addEventListener("click", () => setPanelOpen(false));

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && body.classList.contains("panel-open")) {
    setPanelOpen(false);
  }
});

questionInput.addEventListener("input", () => {
  syncQuestionCounter();
  renderQuestionChips();
  refreshResultsForDraft();
});

questionInput.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter" || event.shiftKey) {
    return;
  }

  event.preventDefault();
  await askBeacon(questionInput.value);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await askBeacon(questionInput.value);
});

topicPicker?.addEventListener("click", (event) => {
  const targetEl = clickTargetElement(event);
  const button = targetEl?.closest?.("[data-topic-id]");
  if (!button || !topicPicker.contains(button)) {
    return;
  }

  const topicId = button.getAttribute("data-topic-id") || "";
  setSelectedTopic(topicId);
  setPanelOpen(true);
});

topicPicker?.addEventListener("keydown", (event) => {
  if (!topicPicker) {
    return;
  }

  const chips = [...topicPicker.querySelectorAll("button[data-topic-id]")];
  if (chips.length === 0) {
    return;
  }

  const moveFocus = (nextIndex) => {
    const len = chips.length;
    const clamped = ((nextIndex % len) + len) % len;
    chips.forEach((c) => {
      c.tabIndex = -1;
    });
    const next = chips[clamped];
    next.tabIndex = 0;
    next.focus();
    event.preventDefault();
  };

  const currentIndex = chips.indexOf(document.activeElement);

  if (event.key === "ArrowRight") {
    moveFocus(currentIndex === -1 ? 0 : currentIndex + 1);
  } else if (event.key === "ArrowLeft") {
    moveFocus(currentIndex === -1 ? chips.length - 1 : currentIndex - 1);
  } else if (event.key === "Home") {
    moveFocus(0);
  } else if (event.key === "End") {
    moveFocus(chips.length - 1);
  }
});

questionChips?.addEventListener("click", (event) => {
  const targetEl = clickTargetElement(event);
  const chip = targetEl?.closest?.("button[data-q-index]");
  if (!chip || !questionChips.contains(chip)) {
    return;
  }

  event.preventDefault();
  const raw = chip.getAttribute("data-q-index");
  const index = Number.parseInt(raw ?? "", 10);
  if (Number.isNaN(index) || index < 0) {
    return;
  }

  const topicId = chip.getAttribute("data-topic-id") || selectedTopicId;
  applyQuestionFromChipIndex(index, topicId);
});

syncQuestionCounter();
renderTopicPicker();
renderQuestionChips();

resultsState.addEventListener("click", (event) => {
  const toggle = event.target.closest(".drawer-toggle");
  if (!toggle) {
    return;
  }

  const shell = toggle.closest(".result-answer-card")?.nextElementSibling;
  if (!shell) {
    return;
  }

  const drawerType = toggle.dataset.drawer || "";
  const targetPanel = shell.querySelector(`.drawer-${drawerType}`);
  if (!targetPanel) {
    return;
  }

  const isExpanded = toggle.getAttribute("aria-expanded") === "true";
  shell.querySelectorAll(".drawer-panel").forEach((panel) => {
    if (panel !== targetPanel) {
      panel.hidden = true;
    }
  });
  shell.previousElementSibling?.querySelectorAll(".drawer-toggle").forEach((button) => {
    if (button !== toggle) {
      button.setAttribute("aria-expanded", "false");
    }
  });
  toggle.setAttribute("aria-expanded", String(!isExpanded));
  targetPanel.hidden = isExpanded;
});
