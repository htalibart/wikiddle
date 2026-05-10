const API_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000/api"
  : "/api";

const LANGUAGES = ["en", "fr"];

/**
 * Returns a color between blue (cold) and red (hot) for a score
 * @param {number} score - score to color
 * @param {number} [maxScore=20] - score that maps to red
 * @returns {string} CSS color string, e.g. "rgb(255, 0, 0)"
 */
function scoreToColor(score, maxScore = 20) {
  const normalized = score / maxScore;
  const r = Math.round(normalized * 255);
  const b = Math.round((1 - normalized) * 255);
  return `rgb(${r}, 0, ${b})`;
}

/**
 * Returns the URL of a Wikipedia page given its title
 * @param {string} title - page title 
 * @param {string} lang - active language code
 * @returns {string} Wikipedia url
 */
function titleToUrl(title, lang) {
  return `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}

/**
 * Renders the target article card
 * @param {State} state - current application state
 * @returns {HTMLElement} the target article card
 */
function renderTargetCard(state) {

  const card = document.createElement("div");
  card.classList.add("guess-card");
  card.classList.add("target-guess-card");

  let titleHTML = `<div class="guess-card-title">?</div>`
  if (state.knowledgeTarget.title !== null) {
    titleHTML = `<div class="guess-card-title"><a href=${titleToUrl(state.knowledgeTarget.title, state.lang)} target="_blank">${state.knowledgeTarget.title}</a></div>`
  };

  const links = state.knowledgeTarget.links;

  card.innerHTML = `
      <div class="guess-card-header">
        ${titleHTML}
        <div class="guess-card-score""></div>
      </div>
      <div class="guess-card-links">${links.map(title => `<a href="${titleToUrl(title, state.lang)}" target="_blank">${title}</a>`).join(" · ")}</div>
    `;
    
  return card;

}


/**
 * Renders a guessed article card
 * @param {State} state - current application state
 * @param {Guess} guess - the guess to render
 * @returns {HTMLElement} the article card
 */
function renderGuessCard(state, guess) {
  const card = document.createElement("div");

  card.classList.add("guess-card");

  card.innerHTML = `
      <div class="guess-card-header">
        <div class="guess-card-title"><a href=${titleToUrl(guess.title, state.lang)} target="_blank">${guess.title}</a></div>
        <div class="guess-card-score" style="color: ${scoreToColor(guess.score)}">${guess.score}</div>
      </div>
      <div class="guess-card-links">${guess.common.map(title => `<a href="${titleToUrl(title, state.lang)}" target="_blank">${title}</a>`).join(" · ")}</div>
    `;

  
  // guess is a link on target -> change color
  if (guess.isOnTarget) {
    card.querySelector(".guess-card-title").classList.add("guess-card-title-on-target");
  }

  return card;
}


/**
 * Renders all article cards (target and guesses)
 * @param {State} state - current application state 
 */
function renderCards(state) {
  const list = document.getElementById("guesses-list");
  list.innerHTML = "";

  // target card on top
  const targetCard = renderTargetCard(state);
  list.appendChild(targetCard);

  // all other guesses below
  for (const guess of state.guesses) {
    const card = renderGuessCard(state, guess);
    list.appendChild(card);
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
 * Updates known links with new titles
 * @param {State} state - current application state
 * @param {str[]} links - array of article titles to add to the known links
 */
function updateKnownLinks(state, links) {
  for (const link of links) {
    if (! state.knowledgeTarget.links.includes(link)) {
      state.knowledgeTarget.links.push(link);
    }
  }
}

/**
 * Shows an overlay when the target article changes mid-game
 * 
 */
function showMidnightOverlay() {
  return new Promise(resolve => {
    document.getElementById("midnight-overlay").style.display = "flex";
    document.getElementById("midnight-btn").addEventListener("click", () => {
      resolve();
    });
  });
}

/**
 * Handles the case when the target article changes mid-game
 */
async function handleDateChange() {
  await showMidnightOverlay();
  window.location.reload();
}

/**
 * Saves the current state to localStorage
 * (stores one state per language)
 * @param {State} state - current application state
 */
function saveState(state) {
  localStorage.setItem(`game-state-${state.lang}`, JSON.stringify(state));
}

/**
 * Handles a guess proposed by the user.
 * Fetches common neighbors from the API, updates the state, re-renders the cards.
 * If the guess is the target, triggers the win popup.
 * @param {State} state - current application state 
 * @param {TomSelect} tomSelect - the TomSelect search input instance
 */
async function handleGuessInput(state, tomSelect) {
  const guessId = tomSelect.getValue();
  const guessTitle = tomSelect.getOption(guessId)?.textContent?.trim();
  if (!guessId) return;

  tomSelect.clear();
  tomSelect.clearOptions();
  
  fetch(`${API_URL}/${state.lang}/common-neighbors?id=${guessId}`)
    .then(res => res.json())
    .then(data => {

      // Check that the date is still the same as before the player started the game, otherwise reset the game
      if (state.gameDate == null) {
        state.gameDate = data.game_date;
      }
      else {
        if (data.game_date != state.gameDate) {
          handleDateChange();
          return;
        }
      }

      const guess = {
        id: guessId,
        title: guessTitle,
        common: data.common,
        score: data.common.length,
        isTarget: data.is_target,
        isOnTarget: data.is_on_target,
      };

      updateKnownLinks(state, guess.common);
      if (guess.isOnTarget) {
        updateKnownLinks(state, [guess.title]);
      }

      if (guess.isTarget) {
        state.knowledgeTarget.title = guess.title;
        confetti();
        document.getElementById("win-overlay").style.display = "flex";
      }
      else {
        insertSorted(guess, state);
      }

      renderCards(state);
      saveState(state);
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
 * Builds the example guess card shown in the "how to play" overlay
 * @param {Object} translations - translations for the current language
 * @param {string} lang - language code
 * @returns {HTMLElement} the example card
 */
function buildHowtoExample(translations, lang) {
  const card = document.createElement("div");
  card.classList.add("guess-card");
  card.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title">
        <a href="${titleToUrl(translations.howto_example_title, lang)}" target="_blank">${translations.howto_example_title}</a>
      </div>
      <div class="guess-card-score" style="color: ${scoreToColor(translations.howto_example_score)}">
        ${translations.howto_example_score}
      </div>
    </div>
    <div class="guess-card-links" style="display:block">
      ${translations.howto_example_links.map(title => `<a href="${titleToUrl(title, lang)}" target="_blank">${title}</a>`).join(" · ")}
    </div>
  `;
  return card;
}

/**
 * Fetches a new hint from the API and adds it to the known links, then re-renders the cards.
 * Does nothing if the player already knows all the links.
 * @param {State} state - current application state
 */
async function addHint(state) {
  if (state.knowsAllLinks) {
    console.log("You already have all the links");
    document.getElementById("hint-btn").classList.toggle("disabled-btn", state.knowsAllLinks);
    return;
  }

  await fetch(`/${API_URL}/${state.lang}/new-target-neighbor`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(state.knowledgeTarget.links)
  })
  .then(res => res.json())
  .then(
    data => {
      if (data.title === null) {
        state.knowsAllLinks = true;
        return;
      }
      updateKnownLinks(state, [data.title]);
    }
  )

  renderCards(state);
  saveState(state);
}


/**
 * @typedef {Object} Guess
 * @property {string} id - article id
 * @property {string} title - article title
 * @property {string[]} common - common neighbors with the target
 * @property {number} score - number of common neighbors with the target
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
 * @property {boolean} knowsAllLinks - true if the player already has all the links, false otherwise
 * @property {string} gameDate - date associated with the ongoing game
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
      links: []
    },
    knowsAllLinks: false,
    gameDate: null,
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
  
  return state;
}


async function main() {
  
  const state = await loadOrCreateState();

  // Translations
  const translations = await loadTranslations(state.lang);
  document.querySelector(`#lang-switcher a[href="/${state.lang}"]`).classList.add("active");
  document.getElementById("guess-btn").textContent = translations.guess;
  document.getElementById("guess-input").placeholder = translations.input_placeholder;
  document.getElementById("win-message").textContent = translations.win_message;
  document.getElementById("howto-btn").textContent = translations.howto_btn;
  document.getElementById("hint-btn").textContent = translations.hint;
  document.getElementById("midnight-message").textContent = translations.midnight_message;
  document.getElementById("midnight-btn").textContent = translations.midnight_btn;


  // How to play
  document.getElementById("howto-title").textContent = translations.howto_btn;
  document.getElementById("howto-text-before").innerHTML = translations.howto_text_before;
  document.getElementById("howto-text-after").innerHTML = translations.howto_text_after;
  document.getElementById("howto-example").appendChild(buildHowtoExample(translations, state.lang));

  const howtoBtn = document.getElementById("howto-btn");
  const howtoOverlay = document.getElementById("howto-overlay");
  howtoBtn.addEventListener("click", () => howtoOverlay.style.display = "flex");
  howtoOverlay.addEventListener("click", () => howtoOverlay.style.display = "none");
  document.getElementById("howto-box").addEventListener("click", e => e.stopPropagation());
  document.getElementById("howto-close-btn").addEventListener("click", () => howtoOverlay.style.display = "none");
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") howtoOverlay.style.display = "none";
  });


  // Search
  const tomSelect = new TomSelect("#guess-input", {
      valueField: "id",
      labelField: "title",
      searchField: "title",
      preload: false,
      maxItems: 1,
      closeAfterSelect: true,
      load: function(query, callback) {
        fetch(`${API_URL}/${state.lang}/articles?query=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(data => data.filter(article => !state.guesses.some(g => g.id == article.id)))
          .then(data => callback(data))
          .catch(() => callback());
      },
      onItemAdd: function() {
        handleGuessInput(state, tomSelect);
      }
    });

  document.getElementById("guess-btn").addEventListener("click", () => handleGuessInput(state, tomSelect));

  // Hint button
  const hintBtn = document.getElementById("hint-btn");
  hintBtn.addEventListener("click", () => {
    addHint(state);
      hintBtn.blur();
  });
  hintBtn.classList.toggle("disabled-btn", state.knowsAllLinks);
  

  // Win overlay
  document.getElementById("win-overlay").addEventListener("click", () => {
    document.getElementById("win-overlay").style.display = "none";
  });
  document.getElementById("win-box").addEventListener("click", e => e.stopPropagation());
  document.getElementById("win-close-btn").addEventListener("click", () => {
  document.getElementById("win-overlay").style.display = "none";
});
  document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    document.getElementById("win-overlay").style.display = "none";
  }

  
});

renderCards(state);
}

main();
