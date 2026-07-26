/**
 * AskMyNotes — app.js
 * Pure front-end interaction logic. No network calls, no third-party libs.
 */

document.addEventListener("DOMContentLoaded", () => {

  // ─────────────────────────────────────────────
  // ELEMENT REFERENCES
  // ─────────────────────────────────────────────

  const fileInput     = document.querySelector("#pdf-input");
  const uploadStatus  = document.querySelector("#upload-status");
  const questionEl    = document.querySelector("#question");
  const askBtn        = document.querySelector("#ask-btn");
  const statusEl      = document.querySelector("#status");
  const answerEl      = document.querySelector("#answer");
  const answerTextEl  = document.querySelector("#answer-text");
  const qtypePill     = document.querySelector("#qtype-pill");
  const toolPill      = document.querySelector("#tool-pill");
  const sourcesEl     = document.querySelector("#sources");
  const sourcesListEl = document.querySelector("#sources-list");

  // ─────────────────────────────────────────────
  // CONSTANTS
  // ─────────────────────────────────────────────

  /** Maps question-type keys → Tailwind pill colour classes. */
  const QTYPE_COLORS = {
    definition : "pill pill-indigo",
    example    : "pill pill-purple",
    comparison : "pill pill-emerald",
  };

  /**
   * Three distinct placeholder source excerpts shown for non-calculator questions.
   * Text is set via textContent — never innerHTML — per spec.
   */
  const PLACEHOLDER_SOURCES = [
    "Sample source chunk 1 — example excerpt from the uploaded notes.",
    "Sample source chunk 2 — another excerpt.",
    "Sample source chunk 3 — final excerpt.",
  ];

  // ─────────────────────────────────────────────
  // HELPERS
  // ─────────────────────────────────────────────

  /**
   * Resets every piece of answer-related UI back to its hidden/empty state.
   * Must be called before each new submission attempt.
   */
  function resetAnswerUI() {
    answerEl.hidden        = true;
    qtypePill.hidden       = true;
    toolPill.hidden        = true;
    sourcesEl.hidden       = true;
    answerTextEl.textContent = "";
    statusEl.textContent     = "";
    // Empty the list without innerHTML on the items themselves
    while (sourcesListEl.firstChild) {
      sourcesListEl.removeChild(sourcesListEl.firstChild);
    }
  }

  /**
   * Derives the placeholder question-type from the raw question string.
   * @param {string} q  Trimmed, lower-cased question.
   * @returns {"definition"|"example"|"comparison"} placeholderType
   */
  function inferQuestionType(q) {
    if (q.startsWith("what is"))                                              return "definition";
    if (q.startsWith("give") || q.includes("example"))                       return "example";
    if (q.includes("vs") || q.includes("versus") ||
        q.includes("compare") || q.includes("difference"))                   return "comparison";
    return "definition";
  }

  /**
   * Derives the placeholder tool from the raw question string.
   * Uses "calculator" only when the input is purely arithmetic.
   * @param {string} q  Original (non-lowercased) trimmed question.
   * @returns {"calculator"|"search_notes"} placeholderTool
   */
  function inferTool(q) {
    return /^[0-9\s+\-*/().]+$/.test(q) ? "calculator" : "search_notes";
  }

  // ─────────────────────────────────────────────
  // FILE INPUT — display selected filename
  // ─────────────────────────────────────────────

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];

    if (!file) {
      uploadStatus.textContent = "";
      uploadStatus.className   = "";
      return;
    }

    uploadStatus.textContent = `Selected "${file.name}" (ready to upload)`;
    uploadStatus.className   = "text-sm text-green-600 mt-2 min-h-[1.25rem]";
  });

  // ─────────────────────────────────────────────
  // SUBMIT FLOW
  // ─────────────────────────────────────────────

  askBtn.addEventListener("click", () => {

    // ── Step 1 · Validate input ────────────────
    const question = questionEl.value.trim();

    if (!question) {
      statusEl.textContent = "Please type a question first.";
      statusEl.className   = "text-sm text-red-500 mt-2 min-h-[1.25rem]";
      resetAnswerUI();
      return;
    }

    // ── Step 2 · Show loading state ────────────
    resetAnswerUI();
    statusEl.textContent = "Thinking...";
    statusEl.className   = "text-sm text-gray-500 mt-2 min-h-[1.25rem]";

    // ── Step 3 · Simulate backend delay (exactly one setTimeout) ──
    setTimeout(() => {

      // ── Step 4 · Determine question type ────
      const placeholderType = inferQuestionType(question.toLowerCase());

      // ── Step 5 · Determine tool ─────────────
      const placeholderTool = inferTool(question);

      // ── Step 6 · Build placeholder answer ───
      const placeholderAnswer =
        `Placeholder answer for: "${question}". Real answers will appear here once the backend is connected.`;

      // ── Step 7 · Populate UI ────────────────

      // Answer text
      answerTextEl.textContent = placeholderAnswer;

      // Question-type pill
      qtypePill.textContent = `type: ${placeholderType}`;
      qtypePill.className   = QTYPE_COLORS[placeholderType];
      qtypePill.hidden      = false;

      // Tool pill
      toolPill.textContent = `tool: ${placeholderTool}`;
      toolPill.hidden      = false;

      // Sources — only for non-calculator questions
      if (placeholderTool !== "calculator") {
        PLACEHOLDER_SOURCES.forEach((excerpt) => {
          const li = document.createElement("li");
          li.textContent = excerpt;          // textContent only — no innerHTML
          sourcesListEl.appendChild(li);
        });
        sourcesEl.hidden = false;
      }

      // Reveal answer panel and clear the loading message
      answerEl.hidden      = false;
      statusEl.textContent = "";

    }, 600); // single 600 ms UX delay
  });

});