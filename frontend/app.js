import { titleToUrl, categoryToUrl, makeScoreColorFn } from "./utils.js";
import { showToast, buildHowtoExample, showMidnightOverlay, buildWinOverlay, showWinOverlay } from "./overlays.js";
import TomSelect from "tom-select";
import "tom-select/dist/css/tom-select.css";

const API_URL = "/api";
const LANGUAGES = ["en", "fr"];
const scoreToColor = makeScoreColorFn("#0C57A8");

/**
 * Renders the target article card
 * @param {State} state - current application state
 * @param {Object} translations - translations for the current language
 * @returns {HTMLElement} the target article card
 */
function renderTargetCard(state, translations) {
  const targetFound = state.knowledgeTarget.title !== null;

  const card = document.createElement("div");
  card.classList.add("guess-card");
  card.classList.add("target-guess-card");

  if (targetFound) {
    card.classList.add("found-target-guess-card");
  }

  let titleHTML = `<div class="guess-card-title">?</div>`;
  if (targetFound) {
    titleHTML = `<div class="guess-card-title"><a href="${titleToUrl(state.knowledgeTarget.title, state.lang)}" target="_blank" rel="noopener noreferrer">${state.knowledgeTarget.title}</a></div>`;
  }

  const knowsHTML = state.knowsAllLinks ? `<div class="guess-card-knows">${translations.all_links_found}</div>` : "";

  const links = state.knowledgeTarget.links;
  const newLinks = state.knowledgeTarget.newLinks;

  const linksHTML =
    links.length > 0
      ? links
          .map((title) => {
            const isNew = newLinks && newLinks.has(title) && !targetFound;
            return `<a href="${titleToUrl(title, state.lang)}" target="_blank" rel="noopener noreferrer" ${isNew ? 'class="new-link"' : ""}>${title} </a>`;
          })
          .join(" ")
      : "";

  const categories = state.knowledgeTarget.categories;
  const newCategories = state.knowledgeTarget.newCategories;

  const placeholderHTML =
    links.length == 0 && categories.length == 0
      ? `<span class="target-placeholder">${translations.target_placeholder}</span>`
      : "";

  const categoriesHTML =
    categories.length > 0
      ? `
        <div class="guess-card-categories-separator">
          <span></span>
          <div class="guess-card-categories-label">${translations.categories}</div>
          <span></span>
        </div>
        <div class="guess-card-categories">
          ${categories
            .map((title) => {
              const isNew = newCategories && newCategories.has(title) && !targetFound;
              return `<a href="${categoryToUrl(title, state.lang)}" target="_blank" rel="noopener noreferrer" ${isNew ? 'class="new-category"' : ""}># ${title}</a>`;
            })
            .join(" ")}
        </div>
      `
      : "";

  card.innerHTML = `
      <div class="guess-card-header">
        ${titleHTML}
        ${knowsHTML}
      </div>
      <div class="guess-card-links">${linksHTML}</div>
      ${categoriesHTML}
      ${placeholderHTML}
    `;

  return card;
}

/**
 * Renders a guessed article card
 * @param {State} state - current application state
 * @param {Guess} guess - the guess to render
 * @param {Object} translations - translations for the current language
 * @returns {HTMLElement} the article card
 */
function renderGuessCard(state, guess, translations) {
  const card = document.createElement("div");

  card.classList.add("guess-card");

  const onTargetLabel = guess.isOnTarget
    ? ` <span class="guess-card-on-target-label">— ${translations.on_target_label}</span>`
    : "";

  const linksHTML =
    guess.commonLinks.length > 0
      ? `<div class="guess-card-links">${guess.commonLinks.map((title) => `<a href="${titleToUrl(title, state.lang)}" target="_blank" rel="noopener noreferrer">${title}</a>`).join(" ")}</div>`
      : "";

  const categoriesHTML =
    guess.commonCategories.length > 0
      ? `
        <div class="guess-card-categories-separator">
          <span></span>
          <div class="guess-card-categories-label">${translations.categories}</div>
          <span></span>
        </div>
        <div class="guess-card-categories">
          ${guess.commonCategories
            .map(
              (title) =>
                `<a href="${categoryToUrl(title, state.lang)}" target="_blank" rel="noopener noreferrer"># ${title}</a>`,
            )
            .join(" ")}
        </div>
      `
      : "";

  const noCommonHTML =
    guess.commonLinks.length == 0 && guess.commonCategories.length == 0
      ? `<div class="guess-card-noinfo">${translations.no_common_info}</div>`
      : "";

  card.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title"><a href="${titleToUrl(guess.title, state.lang)}" target="_blank" rel="noopener noreferrer">${guess.title}</a>${onTargetLabel}</div>
      <div class="guess-card-score">
        <span class="guess-card-score-links">${guess.commonLinks.length}</span>
      </div>
    </div>
    ${linksHTML}
    ${categoriesHTML}
    ${noCommonHTML}
  `;

  card.querySelector(".guess-card-score-links").style.color = scoreToColor(guess.score);

  // guess is a link on target -> change color
  if (guess.isOnTarget) {
    card.querySelector(".guess-card-title").classList.add("guess-card-title-on-target");
  }

  // guess is latest guess -> change style
  if (guess.id == state.lastGuess?.id) {
    card.classList.add("last-guess-card");
  }

  return card;
}

/**
 * Renders all article cards (target, latest guess all other guesses)
 * @param {State} state - current application state
 * @param {Object} translations - translations for the current language
 */
function renderCards(state, translations) {
  const list = document.getElementById("guesses-list");
  list.innerHTML = "";

  // last guess card on top (if any)
  if (state.lastGuess != null) {
    const label = document.createElement("div");
    label.classList.add("section-label");
    label.textContent = translations.section_last_guess;
    list.appendChild(label);
    const lastGuessCard = renderGuessCard(state, state.lastGuess, translations);
    list.appendChild(lastGuessCard);
  }

  // target card right below
  const mysteryLabel = document.createElement("div");
  mysteryLabel.classList.add("section-label");
  mysteryLabel.textContent = translations.section_mystery;
  list.appendChild(mysteryLabel);
  const targetCard = renderTargetCard(state, translations);
  list.appendChild(targetCard);

  // all other guesses below
  if (state.guesses.length > 0) {
    const prevLabel = document.createElement("div");
    prevLabel.classList.add("section-label");
    prevLabel.textContent = translations.section_previous_guesses;
    list.appendChild(prevLabel);
    for (const guess of state.guesses) {
      const card = renderGuessCard(state, guess, translations);
      list.appendChild(card);
    }
  }
}

/**
 * Inserts a new guess in the guess list, sorted by decreasing score
 * @param {Guess} guess - guess to insert
 * @param {State} state - current application state
 */
function insertSorted(guess, state) {
  let low = 0;
  let high = state.guesses.length;
  while (low < high) {
    const m = Math.floor((low + high) / 2);
    if (guess.score < state.guesses.at(m).score) {
      low = m + 1;
    } else {
      high = m;
    }
  }
  state.guesses.splice(low, 0, guess);
}

/**
 * Updates known categories and links with new titles
 * @param {State} state - current application state
 * @param {str[]} links - array of article titles to add to the known links
 * @param {str[]} categories - array of categories to add to the known categories
 */

function updateKnownInfo(state, links, categories) {
  state.knowledgeTarget.newCategories.clear();
  state.knowledgeTarget.newLinks.clear();

  // Update links
  for (const link of links) {
    if (!state.knowledgeTarget.links.includes(link)) {
      state.knowledgeTarget.links.push(link);
      state.knowledgeTarget.newLinks.add(link);
    }
  }

  // Update categories
  for (const category of categories) {
    if (!state.knowledgeTarget.categories.includes(category)) {
      state.knowledgeTarget.categories.push(category);
      state.knowledgeTarget.newCategories.add(category);
    }
  }
}

/**
 * Handles the case when the target article changes mid-game
 */
async function handleDateChange() {
  await showMidnightOverlay();
  window.location.reload();
}

/**
 * Checks whether an API response belongs to the current game date.
 *
 * If no game date is stored yet, initializes state.gameDate with currentDate.
 * If currentDate differs from the stored game date, shows the midnight overlay,
 * schedules a page reload, and returns false
 *
 * @param {State} state - current application state
 * @param {string} currentDate - game date returned by the API
 * @returns {boolean} true if the caller may continue processing the response, false if processing should stop
 */
function checkGameDate(state, currentDate) {
  if (state.gameDate == null) {
    state.gameDate = currentDate;
    return true;
  } else {
    if (currentDate != state.gameDate) {
      handleDateChange();
      return false;
    }
  }

  return true;
}

/**
 * Shows yesterday's answer in a banner
 * @param {State} state - current state
 * @param {Object} translations - translations for the current language
 */
async function showYesterdaysAnswer(state, translations) {
  const banner = document.getElementById("yesterdays-banner");
  const dismissBtn = document.getElementById("yesterdays-banner-dismiss");
  dismissBtn.setAttribute("aria-label", translations.close);

  try {
    const res = await fetch(`${API_URL}/${state.lang}/yesterdays-article`);
    if (!res.ok) {
      banner.style.display = "none";
      return;
    }
    const { title } = await res.json();
    const titleLink = `<a href="${titleToUrl(title, state.lang)}" target="_blank" rel="noopener noreferrer">${title}</a>`;
    document.getElementById("yesterdays-banner-message").innerHTML = translations.yesterdays_answer.replace(
      "{title}",
      titleLink,
    );
  } catch {
    banner.style.display = "none";
    return;
  }

  dismissBtn.addEventListener("click", () => {
    banner.style.display = "none";
  });
}

/**
 * Handles a guess proposed by the user.
 * Fetches common links from the API, updates the state, re-renders the cards.
 * If the guess is the target, triggers the win popup.
 * @param {State} state - current application state
 * @param {TomSelect} tomSelect - the TomSelect search input instance
 * @param {Object} translations - translations for the current language
 */
async function handleGuessInput(state, tomSelect, translations) {
  const guessId = tomSelect.getValue();
  const guessTitle = tomSelect.getOption(guessId)?.textContent?.trim();
  if (!guessId) return;

  tomSelect.clear();
  tomSelect.clearOptions();

  fetch(`${API_URL}/${state.lang}/common-info?id=${guessId}`)
    .then((res) => {
      if (!res.ok) {
        showToast(translations.error_message, true);
        return;
      }
      return res.json();
    })
    .then((data) => {
      if (!data) return;

      // Check that the date is still the same as before the player started the game, otherwise reset the game
      if (!checkGameDate(state, data.game_date)) return;

      const guess = {
        id: guessId,
        title: guessTitle,
        commonLinks: data.common_links,
        commonCategories: data.common_categories,
        score: data.common_links.length,
        isTarget: data.is_target,
        isOnTarget: data.is_on_target,
      };

      const linksToAdd = [...guess.commonLinks];
      if (guess.isOnTarget) {
        linksToAdd.push(guess.title);
      }
      updateKnownInfo(state, linksToAdd, [...guess.commonCategories]);

      if (guess.isTarget) {
        state.knowledgeTarget.title = guess.title;
        if (state.lastGuess) {
          insertSorted(state.lastGuess, state);
        }
        state.lastGuess = null;
        showWinOverlay(state, translations);
      } else {
        // update last guess, sort the rest of the cards
        if (state.lastGuess != null) {
          insertSorted(state.lastGuess, state);
        }
        state.lastGuess = guess;
      }
      renderCards(state, translations);
      saveState(state);
    })
    .catch(() => {
      showToast(translations.error_message, true);
    });
}

/**
 * Returns the current active language based on the URL (falls back to "en" if not found).
 * @returns {string} active language code
 */
function getLang() {
  const pathLang = window.location.pathname.split("/")[1];
  if (LANGUAGES.includes(pathLang)) {
    return pathLang;
  }
  const browserLang = navigator.language.split("-")[0];
  return LANGUAGES.includes(browserLang) ? browserLang : "en";
}

/**
 * Loads the translations from the i18n/ folder
 * @param {string} lang - acttive language code
 * @returns {Promise<Object>} translations for the given language
 */
async function loadTranslations(lang) {
  const res = await fetch(`/i18n/${lang}.json`);
  return res.json();
}

/**
 * Fetches a new hint from the API (category or link) and adds it to the known links, then re-renders the cards.
 * Does nothing if the player already knows all the categories or links.
 * @param {State} state - current application state
 * @param {Object} translations - translations for the current language
 */
async function addHint(state, translations) {
  const hintBtn = document.getElementById("hint-btn");
  let hintType = null;

  if (state.knowsAllLinks && !state.knowsAllCategories) {
    hintType = "category";
  } else if (state.knowsAllCategories && !state.knowsAllLinks) {
    hintType = "link";
  } else if (!state.knowsAllCategories && !state.knowsAllLinks) {
    hintType = Math.random() < 0.75 ? "link" : "category";
  } else {
    showToast(translations.all_hints_found_error, false);
    hintBtn.classList.add("disabled-btn");
    hintBtn.disabled = true;
    return;
  }

  const known = hintType == "link" ? state.knowledgeTarget.links : state.knowledgeTarget.categories;

  await fetch(`${API_URL}/${state.lang}/new-target-${hintType}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(known),
  })
    .then((res) => {
      if (!res.ok) {
        showToast(translations.error_message, true);
        return null;
      }
      return res.json();
    })
    .then((data) => {
      if (data === null) return;

      if (!checkGameDate(state, data.game_date)) return;

      if (data.title === null) {
        if (hintType == "link") state.knowsAllLinks = true;
        else state.knowsAllCategories = true;
        if (state.knowsAllLinks && state.knowsAllCategories) {
          hintBtn.classList.add("disabled-btn");
          hintBtn.disabled = true;
        }
      } else {
        if (hintType == "link") updateKnownInfo(state, [data.title], []);
        else updateKnownInfo(state, [], [data.title]);
        state.nbHints += 1;
      }

      renderCards(state, translations);
      saveState(state);
    })
    .catch(() => {
      showToast(translations.error_message, true);
    });
}

/**
 * @typedef {Object} Guess
 * @property {string} id - article id
 * @property {string} title - article title
 * @property {string[]} commonLinks - common links with the target
 * @property {number} score - number of common links with the target
 * @property {boolean} isTarget - whether this guess is the target article
 * @property {boolean} isOnTarget - whether this guess is a link on the target article
 */

/**
 * @typedef {Object} State
 * @property {string} lang - current active language
 * @property {Guess[]} guesses - guesses made so far, sorted by decreasing score
 * @property {Object} knowledgeTarget - known information about the target article
 * @property {string|null} knowledgeTarget.title - target page once found, set to null before that
 * @property {string[]} knowledgeTarget.links - links on the target page, revealed by guesses or hints
 * @property {Set<string>} knowledgeTarget.newLinks - new links on the target paged (colored differently)
 * @property {boolean} knowsAllLinks - true if the player already has all the links, false otherwise
 * @property {string} gameDate - date associated with the ongoing game
 * @property {Guess} lastGuess - last guess proposed by the player
 * @property {int} nbHints - number of hints asked by the player
 */

/**
 * Creates an empty state for a new game
 * @returns {State} a new state object
 */
function createState() {
  return {
    lang: getLang(),
    guesses: [],
    knowledgeTarget: {
      title: null,
      links: [],
      newLinks: new Set(),
      categories: [],
      newCategories: new Set(),
    },
    knowsAllLinks: false,
    knowsAllCategories: false,
    gameDate: null,
    lastGuess: null,
    nbHints: 0,
  };
}

/**
 * Loads the saved state from localStorage if it exists and is still valid for today's game,
 * otherwise creates an empty state.
 * @returns {Promise<State>} the restored or newly created state
 */
async function loadOrCreateState() {
  const lang = getLang();

  const savedState = localStorage.getItem(`game-state-${lang}`);

  if (savedState == null) {
    return createState();
  }

  const state = JSON.parse(savedState);

  const res = await fetch(`${API_URL}/${state.lang}/game-date`);
  const { date } = await res.json();
  if (state.gameDate != date) {
    return createState();
  }

  // temporary fix to handle current game states without categories
  if (!("categories" in state.knowledgeTarget)) {
    state.knowledgeTarget.categories = [];
    state.knowsAllCategories = false;
  }

  state.knowledgeTarget.newLinks = new Set();
  state.knowledgeTarget.newCategories = new Set();

  return state;
}

/**
 * Saves the current state to localStorage, except for the new links
 * (stores one state per language)
 * @param {State} state - current application state
 */
function saveState(state) {
  const { _newLinks, ...knowledgeTarget } = state.knowledgeTarget;
  localStorage.setItem(`game-state-${state.lang}`, JSON.stringify({ ...state, knowledgeTarget }));
}

async function main() {
  const state = await loadOrCreateState();

  document.documentElement.lang = state.lang;

  // Set aria-current attribute to current language (for screen readers)
  document.querySelectorAll("#lang-switcher a").forEach((link) => {
    link.removeAttribute("aria-current");
  });
  document.querySelector(`#lang-switcher a[href="/${state.lang}"]`)?.setAttribute("aria-current", "page");

  // Translations
  const translations = await loadTranslations(state.lang);
  document.title = translations.title;
  document.querySelector('meta[name="description"]').setAttribute("content", translations.description);
  document.querySelector(`#lang-switcher a[href="/${state.lang}"]`).classList.add("active");
  document.getElementById("guess-btn").textContent = translations.guess;
  document.getElementById("guess-input").placeholder = translations.input_placeholder;
  document.getElementById("guess-input-label").textContent = translations.input_placeholder;
  document.getElementById("howto-btn").textContent = translations.howto_btn;
  document.getElementById("hint-btn").textContent = translations.hint;
  document.getElementById("midnight-message").textContent = translations.midnight_message;
  document.getElementById("midnight-btn").textContent = translations.midnight_btn;

  buildHowtoExample(translations, state.lang, scoreToColor);

  const howtoBtn = document.getElementById("howto-btn");
  const howtoOverlay = document.getElementById("howto-overlay");
  howtoBtn.addEventListener("click", () => {
    howtoOverlay.showModal();
    document.getElementById("howto-close-btn").focus();
  });

  showYesterdaysAnswer(state, translations);

  // Search
  const tomSelect = new TomSelect("#guess-input", {
    valueField: "id",
    labelField: "title",
    searchField: "title",
    preload: false,
    maxItems: 1,
    closeAfterSelect: true,
    load: function (query, callback) {
      fetch(`${API_URL}/${state.lang}/articles?query=${encodeURIComponent(query)}`)
        .then((res) => res.json())
        .then((data) =>
          data.filter((article) => !state.guesses.some((g) => g.id == article.id) && article.id != state.lastGuess?.id),
        )
        .then((data) => callback(data))
        .catch(() => callback());
    },
    onItemAdd: function () {
      handleGuessInput(state, tomSelect, translations);
    },
  });

  document
    .getElementById("guess-btn")
    .addEventListener("click", () => handleGuessInput(state, tomSelect, translations));

  // Hint button
  const hintBtn = document.getElementById("hint-btn");
  hintBtn.addEventListener("click", () => {
    addHint(state, translations);
    hintBtn.blur();
  });
  hintBtn.classList.toggle("disabled-btn", state.knowsAllLinks && state.knowsAllCategories);
  hintBtn.disabled = state.knowsAllLinks && state.knowsAllCategories;

  buildWinOverlay(translations);

  renderCards(state, translations);
}

main();
