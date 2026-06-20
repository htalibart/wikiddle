import { titleToUrl, categoryToUrl } from "./utils.js";
import confetti from "canvas-confetti";

/**
 * Shows a toast notification message
 * @param {string} message - message to show
 */
export function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 3000);
}

/**
 * Builds the category separator HTML
 * @param {Object} translations - translations for the current language
 * @returns {string} category separator HTML
 */
function buildCategoriesSeparator(translations) {
  return `
    <div class="guess-card-categories-separator">
      <span></span>
      <div class="guess-card-categories-label">${translations.categories}</div>
      <span></span>
    </div>
  `;
}

/**
 * Builds the "how to play" overlay
 * @param {Object} translations - translations for the current language
 * @param {string} lang - language code
 * @param {function} scoreToColor - function that maps a score to a CSS color string
 */
export function buildHowtoExample(translations, lang, scoreToColor) {
  const box = document.getElementById("howto-box");
  const overlay = document.getElementById("howto-overlay");
  box.innerHTML = "";

  const closeBtn = document.createElement("span");
  closeBtn.id = "howto-close-btn";
  closeBtn.classList.add("overlay-close-btn");
  closeBtn.textContent = "×";
  box.appendChild(closeBtn);

  const title = document.createElement("h2");
  title.textContent = translations.howto_btn;
  box.appendChild(title);

  const textBefore = document.createElement("p");
  textBefore.innerHTML = translations.howto_text_before;
  box.appendChild(textBefore);

  function makeLabel(text) {
    const label = document.createElement("div");
    label.classList.add("section-label");
    label.textContent = text;
    return label;
  }

  function makeAnnotation(text) {
    const anno = document.createElement("p");
    anno.classList.add("howto-annotation");
    anno.innerHTML = text;
    return anno;
  }

  function makeGuessCard(title, score, links, categories, isOnTarget, isLastGuess) {
    const card = document.createElement("div");
    card.classList.add("guess-card");
    if (isLastGuess) card.classList.add("last-guess-card");

    const categoriesHTML =
      categories.length > 0
        ? `
          ${buildCategoriesSeparator(translations)}
          <div class="guess-card-categories">
            ${categories.map((t) => `<a href="${categoryToUrl(t, lang)}" target="_blank"># ${t}</a>`).join(" ")}
          </div>
        `
        : "";

    card.innerHTML = `
      <div class="guess-card-header">
        <div class="guess-card-title${isOnTarget ? " guess-card-title-on-target" : ""}">
          <a href="${titleToUrl(title, lang)}" target="_blank">${title}</a>${isOnTarget ? ` <span class="guess-card-on-target-label">— ${translations.on_target_label}</span>` : ""}
        </div>
        <div class="guess-card-score">
          <span class="guess-card-score-links">${score}</span>
        </div>
      </div>
      <div class="guess-card-links">
        ${links.map((t) => `<a href="${titleToUrl(t, lang)}" target="_blank">${t}</a>`).join(" ")}
      </div>
      ${categoriesHTML}
    `;
    card.querySelector(".guess-card-score-links").style.color = scoreToColor(score);
    return card;
  }

  box.appendChild(makeLabel(translations.section_last_guess));
  box.appendChild(
    makeGuessCard(
      translations.howto_example_encyclopedia_title,
      translations.howto_example_encyclopedia_score,
      translations.howto_example_encyclopedia_links,
      translations.howto_example_encyclopedia_categories,
      true,
      true,
    ),
  );
  box.appendChild(makeAnnotation(translations.howto_annotation_last_guess));

  box.appendChild(makeLabel(translations.section_mystery));
  const targetCard = document.createElement("div");
  targetCard.classList.add("guess-card", "target-guess-card");
  const mysteryLinks = [
    ...translations.howto_example_internet_links,
    ...translations.howto_example_encyclopedia_links,
    ...translations.howto_example_europe_links,
  ];
  const mysteryCategories = [
    ...translations.howto_example_encyclopedia_categories,
    ...translations.howto_example_internet_categories,
    ...translations.howto_example_europe_categories,
  ];
  targetCard.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title">?</div>
    </div>
    <div class="guess-card-links">
      ${mysteryLinks.map((t) => `<a href="${titleToUrl(t, lang)}" target="_blank">${t}</a>`).join(" ")}
    </div>
    ${buildCategoriesSeparator(translations)}
    <div class="guess-card-categories">
      ${mysteryCategories.map((t) => `<a href="${categoryToUrl(t, lang)}" target="_blank"># ${t}</a>`).join(" ")}
    </div>
  `;
  box.appendChild(targetCard);
  box.appendChild(makeAnnotation(translations.howto_annotation_mystery));

  box.appendChild(makeLabel(translations.section_previous_guesses));
  box.appendChild(
    makeGuessCard(
      translations.howto_example_internet_title,
      translations.howto_example_internet_score,
      translations.howto_example_internet_links,
      translations.howto_example_internet_categories,
      true,
      false,
    ),
  );
  box.appendChild(
    makeGuessCard(
      translations.howto_example_europe_title,
      translations.howto_example_europe_score,
      translations.howto_example_europe_links,
      translations.howto_example_europe_categories,
      false,
      false,
    ),
  );
  box.appendChild(makeAnnotation(translations.howto_annotation_previous_guesses));

  const textAfter = document.createElement("p");
  textAfter.innerHTML = translations.howto_text_after;
  box.appendChild(textAfter);

  // Event listeners
  closeBtn.addEventListener("click", () => (overlay.style.display = "none"));
  overlay.addEventListener("click", () => (overlay.style.display = "none"));
  box.addEventListener("click", (e) => e.stopPropagation());
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") overlay.style.display = "none";
  });
}

/**
 * Shows an overlay when the target article changes mid-game
 *
 */
export function showMidnightOverlay() {
  return new Promise((resolve) => {
    document.getElementById("midnight-overlay").style.display = "flex";
    document.getElementById("midnight-btn").addEventListener("click", () => {
      resolve();
    });
  });
}

/**
 * Builds the win overlay
 * @param {Object} translations - translations for the current language
 */
export function buildWinOverlay(translations) {
  document.getElementById("win-message").textContent = translations.win_message;
  document.getElementById("win-share-btn").textContent = translations.win_share;
  document.getElementById("win-share-label").textContent = translations.win_share_label;

  document.getElementById("win-overlay").addEventListener("click", () => {
    document.getElementById("win-overlay").style.display = "none";
  });
  document.getElementById("win-box").addEventListener("click", (e) => e.stopPropagation());
  document.getElementById("win-close-btn").addEventListener("click", () => {
    document.getElementById("win-overlay").style.display = "none";
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.getElementById("win-overlay").style.display = "none";
    }
  });
}

/**
 * Shows the win overlay
 * @param {State} state - current application state
 * @param {Object} translations - translations for the current language
 */
export function showWinOverlay(state, translations) {
  confetti();

  const nbGuesses = 1 + state.guesses.length + (state.lastGuess ? 1 : 0);
  const mysteryTitle = state.knowledgeTarget.title;
  const nbHints = state.nbHints;

  document.getElementById("win-article").innerHTML = translations.win_article.replace(
    "{title}",
    `<a href="${titleToUrl(mysteryTitle, state.lang)}" target="_blank">${mysteryTitle}</a>`,
  );
  document.getElementById("win-game-stats").textContent = translations.win_game_stats
    .replace("{nbGuesses}", nbGuesses)
    .replace("{nbHints}", nbHints);

  const shareText = translations.win_share_text.replace("{nbGuesses}", nbGuesses).replace("{nbHints}", nbHints);
  document.getElementById("win-share-preview").value = shareText;

  document.getElementById("win-share-btn").addEventListener("click", () => {
    if (navigator.share) {
      navigator.share({ text: shareText });
    } else {
      navigator.clipboard.writeText(shareText).then(() => showToast(translations.copied_to_clipboard));
    }
  });

  document.getElementById("win-overlay").style.display = "flex";
}
