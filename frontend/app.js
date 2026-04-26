const API_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000/api"
  : "/api";

const LANGUAGES = ["en", "fr"];

function scoreToColor(score, maxScore = 20) {
  const normalized = score / maxScore;
  const r = Math.round(normalized * 255);
  const b = Math.round((1 - normalized) * 255);
  return `rgb(${r}, 0, ${b})`;
}

function titleToUrl(title, lang) {
  return `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}

function renderCards(state) {
  const list = document.getElementById("guesses-list");
  list.innerHTML = "";
  for (const guess of state.guesses) {
    const card = document.createElement("div");
    card.classList.add("guess-card");
    if (guess.isTarget) {
      card.classList.add("target-guess-card");
    }
    card.innerHTML = `
      <div class="guess-card-header">
        <div class="guess-card-title"><a href=${titleToUrl(guess.title, state.lang)} target="_blank">${guess.title}</a></div>
        <div class="guess-card-score" style="color: ${scoreToColor(guess.score)}">${guess.score}</div>
      </div>
      <div class="guess-card-links">${guess.common.map(title => `<a href="${titleToUrl(title, state.lang)}" target="_blank">${title}</a>`).join(" · ")}</div>
    `;
    card.querySelector(".guess-card-links").style.display = guess.visible ? "block" : "none";
    card.querySelector(".guess-card-links").addEventListener("click", e => e.stopPropagation()); // prevents click on Wikipedia page to propagate to visibility
    card.querySelector(".guess-card-title").addEventListener("click", e => e.stopPropagation()); // prevents click on Wikipedia page to propagate to visibility
    card.addEventListener("click", () => {
      guess.visible = !guess.visible;
      card.querySelector(".guess-card-links").style.display = guess.visible ? "block" : "none";
    });
    list.appendChild(card);
  }
  
}

function insertSorted(guess, state) {
  let low = 0;

  if (!guess.isTarget) {
    let high = state.guesses.length;
    while (low < high) {
      const m = Math.floor((low + high) / 2);
      if (guess.score < state.guesses.at(m).score) {
        low = m + 1;
      } else {
        high = m;
      }
    }
  }
  state.guesses.splice(low, 0, guess);
}

async function handleGuessInput(state, tomSelect) {
  const guessId = tomSelect.getValue();
  const guessTitle = tomSelect.getOption(guessId)?.textContent?.trim();
  if (!guessId) return;

  tomSelect.clear();
  tomSelect.clearOptions();
  
  fetch(`${API_URL}/${state.lang}/common-neighbors?id=${guessId}`)
    .then(res => res.json())
    .then(data => {
      const guess = {
        id: guessId,
        title: guessTitle,
        common: data.common,
        score: data.common.length,
        visible: state.linksVisible,
        isTarget: data.is_target,
      };
      insertSorted(guess, state);
      renderCards(state);

      if (guess.isTarget) {
        confetti();
        document.getElementById("win-overlay").style.display = "flex";
      }
    });
  }


function getLang() {
  const lang = window.location.pathname.split("/")[1];
  return LANGUAGES.includes(lang) ? lang : "en";
}

async function loadTranslations(lang) {
  const res = await fetch(`/i18n/${lang}.json`);
  return res.json();
}

async function main() {
  
  const state = {
    lang: getLang(),
    linksVisible: true,
    guesses: [],
  };


  // Translations
  const translations = await loadTranslations(state.lang);
  document.getElementById("guess-btn").textContent = translations.guess;
  document.getElementById("guess-input").placeholder = translations.input_placeholder;
  document.getElementById("win-message").textContent = translations.win_message;
  document.querySelector(`#lang-switcher a[href="/${state.lang}"]`).classList.add("active");

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
  
  const toggleBtn = document.getElementById("toggle-links-btn");

  toggleBtn.addEventListener("click", () => {
    state.linksVisible = !state.linksVisible;
    state.guesses.forEach(g => g.visible = state.linksVisible);
    renderCards(state);
    document.getElementById("toggle-links-btn").textContent = state.linksVisible ? translations.toggle_hide : translations.toggle_show;
    toggleBtn.blur();
  });

  [translations.toggle_hide, translations.toggle_show].forEach(text => {
    toggleBtn.textContent = text;
    toggleBtn.style.minWidth = Math.max(toggleBtn.offsetWidth, parseInt(toggleBtn.style.minWidth) || 0) + "px";
    });
  toggleBtn.textContent = translations.toggle_hide;

  document.getElementById("win-overlay").addEventListener("click", () => {
    document.getElementById("win-overlay").style.display = "none";
  });
  document.getElementById("win-box").addEventListener("click", e => e.stopPropagation());
  document.getElementById("win-close-btn").addEventListener("click", () => {
  document.getElementById("win-overlay").style.display = "none";
});
}

main();