const API_URL = "/api";
const LANGUAGES = ["en", "fr"];



/**
 * Returns a scoring color function that interpolates from light gray to a target color
 * @param {string} targetHex - target color in hex format, e.g. "#3d5a80"
 * @param {number} [maxScore=20] - score that maps to the target color
 * @returns {function(number): string} a function that takes a score and returns a CSS color string
 */
function makeScoreColorFn(targetHex, maxScore = 20) {
  const r2 = parseInt(targetHex.slice(1,3), 16);
  const g2 = parseInt(targetHex.slice(3,5), 16);
  const b2 = parseInt(targetHex.slice(5,7), 16);
  /**
   * @param {number} score - score to color
   * @returns {string} CSS color string, e.g. "rgb(61, 90, 128)"
   */
  return function(score) {
    if (score <= 3) return "#888780";
    const n = (score - 3) / (maxScore - 3);
    const r = Math.round((1-n) * 200 + n * r2);
    const g = Math.round((1-n) * 200 + n * g2);
    const b = Math.round((1-n) * 200 + n * b2);
    return `rgb(${r}, ${g}, ${b})`;
  }
}

const scoreToColor = makeScoreColorFn("#0C57A8");

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
function renderTargetCard(state, translations) {

  const card = document.createElement("div");
  card.classList.add("guess-card");
  card.classList.add("target-guess-card");

  let titleHTML = `<div class="guess-card-title">?</div>`
  if (state.knowledgeTarget.title !== null) {
    titleHTML = `<div class="guess-card-title"><a href=${titleToUrl(state.knowledgeTarget.title, state.lang)} target="_blank">${state.knowledgeTarget.title}</a></div>`
  };

  const links = state.knowledgeTarget.links;
  const newLinks = state.knowledgeTarget.newLinks;

  const linksHTML = links.length > 0
    ? links.map(title => {
        const isNew = newLinks && newLinks.has(title);
        return `<a href="${titleToUrl(title, state.lang)}" target="_blank" ${isNew ? 'class="new-link"' : ''}>${title} </a>`
      }).join(" ")
    : `<span class="target-placeholder">${translations.target_placeholder}</span>`;

  card.innerHTML = `
      <div class="guess-card-header">
        ${titleHTML}
      </div>
      <div class="guess-card-links">${linksHTML}</div>
    `;
    
  return card;

}


/**
 * Renders a guessed article card
 * @param {State} state - current application state
 * @param {Guess} guess - the guess to render
 * @returns {HTMLElement} the article card
 */
function renderGuessCard(state, guess, translations) {
  const card = document.createElement("div");

  card.classList.add("guess-card");
  
  const onTargetLabel = guess.isOnTarget
    ? ` <span class="guess-card-on-target-label">— ${translations.on_target_label}</span>`
    : "";

  card.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title"><a href=${titleToUrl(guess.title, state.lang)} target="_blank">${guess.title}</a>${onTargetLabel}</div>
      <div class="guess-card-score">${guess.score}</div>
    </div>
    <div class="guess-card-links">${guess.common.map(title => `<a href="${titleToUrl(title, state.lang)}" target="_blank">${title}</a>`).join(" ")}</div>
  `;
  card.querySelector(".guess-card-score").style.color = scoreToColor(guess.score);

  
  // guess is a link on target -> change color
  if (guess.isOnTarget) {
    card.querySelector(".guess-card-title").classList.add("guess-card-title-on-target");
  }

  // guess is latest guess -> change style
  if (guess.id == state.lastGuess?.id) {
    card.classList.add("last-guess-card")
  }

  return card;
}


/**
 * Renders all article cards (target, latest guess all other guesses)
 * @param {State} state - current application state 
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
  if (state.guesses.length > 0)
  {
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
 * Updates known links with new titles
 * @param {State} state - current application state
 * @param {str[]} links - array of article titles to add to the known links
 */
function updateKnownLinks(state, links) {
  state.knowledgeTarget.newLinks.clear();
  for (const link of links) {
    if (! state.knowledgeTarget.links.includes(link)) {
      state.knowledgeTarget.links.push(link);
      state.knowledgeTarget.newLinks.add(link);
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
 * Saves the current state to localStorage, except for the new links
 * (stores one state per language)
 * @param {State} state - current application state
 */
function saveState(state) {
  const { newLinks, ...knowledgeTarget } = state.knowledgeTarget;
  localStorage.setItem(`game-state-${state.lang}`, JSON.stringify({...state, knowledgeTarget}));
}

/**
 * Checks that the date is still the same as before the player started the game, otherwise resets the game
 * @param {State} state 
 */
function checkGameDate(state, currentDate) {
  if (state.gameDate == null) {
    state.gameDate = currentDate;
  }
  else {
    if (currentDate != state.gameDate) {
      handleDateChange();
      return;
    }
  }
}

/**
 * Handles a guess proposed by the user.
 * Fetches common neighbors from the API, updates the state, re-renders the cards.
 * If the guess is the target, triggers the win popup.
 * @param {State} state - current application state 
 * @param {TomSelect} tomSelect - the TomSelect search input instance
 */
async function handleGuessInput(state, tomSelect, translations) {
  const guessId = tomSelect.getValue();
  const guessTitle = tomSelect.getOption(guessId)?.textContent?.trim();
  if (!guessId) return;

  tomSelect.clear();
  tomSelect.clearOptions();
  
  fetch(`${API_URL}/${state.lang}/common-neighbors?id=${guessId}`)
    .then(res => {
      if (!res.ok) {
        showToast(translations.error_message);
        return;
      }
      return res.json();
      })
    .then(data => {
      if (!data) return;

      // Check that the date is still the same as before the player started the game, otherwise reset the game
      checkGameDate(state, data.game_date);

      const guess = {
        id: guessId,
        title: guessTitle,
        common: data.common,
        score: data.common.length,
        isTarget: data.is_target,
        isOnTarget: data.is_on_target,
      };

      const linksToAdd = [...guess.common];
      if (guess.isOnTarget) {
        linksToAdd.push(guess.title);
      }
      updateKnownLinks(state, linksToAdd);

      if (guess.isTarget) {
        state.knowledgeTarget.title = guess.title;
        confetti();
        document.getElementById("win-overlay").style.display = "flex";
      }
      else { // update last guess, sort the rest of the cards
        if (state.lastGuess != null) {
          insertSorted(state.lastGuess, state);
        }
        state.lastGuess = guess;
      }

      renderCards(state, translations);
      saveState(state);
    })
    .catch(() => {
      showToast(translations.error_message);
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
 * Builds the "how to play" overlay
 * @param {Object} translations - translations for the current language
 * @param {string} lang - language code
 * @returns {HTMLElement} the how-to-play overlay
 */
function buildHowtoExample(translations, lang) {
  const box = document.getElementById("howto-box");
  box.innerHTML = "";

  const closeBtn = document.createElement("span");
  closeBtn.id = "howto-close-btn";
  closeBtn.classList.add("overlay-close-btn");
  closeBtn.textContent = "×";
  box.appendChild(closeBtn);
  closeBtn.addEventListener("click", () => document.getElementById("howto-overlay").style.display = "none");

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

  function makeGuessCard(title, score, links, isOnTarget, isLastGuess) {
    const card = document.createElement("div");
    card.classList.add("guess-card");
    if (isLastGuess) card.classList.add("last-guess-card");
    card.innerHTML = `
      <div class="guess-card-header">
        <div class="guess-card-title${isOnTarget ? " guess-card-title-on-target" : ""}">
          <a href="${titleToUrl(title, lang)}" target="_blank">${title}</a>${isOnTarget ? ` <span class="guess-card-on-target-label">— ${translations.on_target_label}</span>` : ""}
        </div>
        <div class="guess-card-score">${score}</div>
      </div>
      <div class="guess-card-links">
        ${links.map(t => `<a href="${titleToUrl(t, lang)}" target="_blank">${t}</a>`).join(" ")}
      </div>
    `;
    card.querySelector(".guess-card-score").style.color = scoreToColor(score);
    return card;
  }

  box.appendChild(makeLabel(translations.section_last_guess));
  box.appendChild(makeGuessCard(
    translations.howto_example_encyclopedia_title,
    translations.howto_example_encyclopedia_score,
    translations.howto_example_encyclopedia_links,
    true, true
  ));
  box.appendChild(makeAnnotation(translations.howto_annotation_last_guess));

  box.appendChild(makeLabel(translations.section_mystery));
  const targetCard = document.createElement("div");
  targetCard.classList.add("guess-card", "target-guess-card");
  const mysteryLinks = [
    ...translations.howto_example_internet_links,
    ...translations.howto_example_encyclopedia_links,
    ...translations.howto_example_europe_links,
  ];
  targetCard.innerHTML = `
    <div class="guess-card-header">
      <div class="guess-card-title">?</div>
    </div>
    <div class="guess-card-links">
      ${mysteryLinks.map(t => `<a href="${titleToUrl(t, lang)}" target="_blank">${t}</a>`).join(" ")}
    </div>
  `;
  box.appendChild(targetCard);
  box.appendChild(makeAnnotation(translations.howto_annotation_mystery));

  box.appendChild(makeLabel(translations.section_previous_guesses));
  box.appendChild(makeGuessCard(
    translations.howto_example_internet_title,
    translations.howto_example_internet_score,
    translations.howto_example_internet_links,
    true, false
  ));
  box.appendChild(makeGuessCard(
    translations.howto_example_europe_title,
    translations.howto_example_europe_score,
    translations.howto_example_europe_links,
    false, false
  ));
  box.appendChild(makeAnnotation(translations.howto_annotation_previous_guesses));

  const textAfter = document.createElement("p");
  textAfter.innerHTML = translations.howto_text_after;
  box.appendChild(textAfter);
}

/**
 * Fetches a new hint from the API and adds it to the known links, then re-renders the cards.
 * Does nothing if the player already knows all the links.
 * @param {State} state - current application state
 */
async function addHint(state, translations) {
  if (state.knowsAllLinks) {
    console.log("You already have all the links");
    document.getElementById("hint-btn").classList.toggle("disabled-btn", state.knowsAllLinks);
    return;
  }

  await fetch(`${API_URL}/${state.lang}/new-target-neighbor`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(state.knowledgeTarget.links)
  })
  .then(res => {
    if (!res.ok) {
      showToast(translations.error_message);
      return;
    }
    return res.json();
    })
  .then(
    data => {
      if (!data) return;
      checkGameDate(state, data.game_date);

      if (data.title === null) {
        state.knowsAllLinks = true;
        return;
      }
      updateKnownLinks(state, [data.title]);
    }
  )
  .catch(() => {
    showToast(translations.error_message);
  });
  renderCards(state, translations);
  saveState(state);
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 3000);
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
 * @property {Set<string>} knowledgeTarget.newLinks - new links on the target paged (colored differently)
 * @property {boolean} knowsAllLinks - true if the player already has all the links, false otherwise
 * @property {string} gameDate - date associated with the ongoing game
 * @property {Guess} lastGuess - last guess proposed by the player
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
      newLinks: new Set()
    },
    knowsAllLinks: false,
    gameDate: null,
    lastGuess: null,
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

  state.knowledgeTarget.newLinks = new Set();
  
  return state;
}


async function main() {
  
  const state = await loadOrCreateState();

  // Translations
  const translations = await loadTranslations(state.lang);
  document.title = translations.title;
  document.querySelector('meta[name="description"]').setAttribute('content', translations.description);
  document.querySelector(`#lang-switcher a[href="/${state.lang}"]`).classList.add("active");
  document.getElementById("guess-btn").textContent = translations.guess;
  document.getElementById("guess-input").placeholder = translations.input_placeholder;
  document.getElementById("guess-input-label").textContent = translations.input_placeholder;
  document.getElementById("win-message").textContent = translations.win_message;
  document.getElementById("howto-btn").textContent = translations.howto_btn;
  document.getElementById("hint-btn").textContent = translations.hint;
  document.getElementById("midnight-message").textContent = translations.midnight_message;
  document.getElementById("midnight-btn").textContent = translations.midnight_btn;


  buildHowtoExample(translations, state.lang);

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
        handleGuessInput(state, tomSelect, translations);
      }
    });

  document.getElementById("guess-btn").addEventListener("click", () => handleGuessInput(state, tomSelect, translations));

  // Hint button
  const hintBtn = document.getElementById("hint-btn");
  hintBtn.addEventListener("click", () => {
    addHint(state, translations);
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

renderCards(state, translations);
}

main();
