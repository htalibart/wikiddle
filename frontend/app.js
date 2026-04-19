const API_URL = "";

function scoreToColor(score, maxScore = 20) {
  const normalized = score / maxScore;
  const r = Math.round(normalized * 255);
  const b = Math.round((1 - normalized) * 255);
  return `rgb(${r}, 0, ${b})`;
}

function titleToUrl(title) {
  return `https://en.wikipedia.org/wiki/${title.replaceAll(" ", "_")}`;
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
        <div class="guess-card-title"><a href=${titleToUrl(guess.title)} target="_blank">${guess.title}</a></div>
        <div class="guess-card-score" style="color: ${scoreToColor(guess.score)}">${guess.score}</div>
      </div>
      <div class="guess-card-links">${guess.common.map(title => `<a href="${titleToUrl(title)}" target="_blank">${title}</a>`).join(" · ")}</div>
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

async function handleGuessInput(target, state, tomSelect) {
  const guessId = tomSelect.getValue();
  const guessTitle = tomSelect.getOption(guessId)?.textContent?.trim();
  if (!guessId) return;

  tomSelect.clear();
  tomSelect.clearOptions();
  
  fetch(`${API_URL}/common-neighbors?id1=${target.id}&id2=${guessId}`)
    .then(res => res.json())
    .then(data => {
      const guess = {
        id: guessId,
        title: guessTitle,
        common: data.common,
        score: data.common.length,
        visible: state.linksVisible,
        isTarget: (guessId == target.id),
      };
      insertSorted(guess, state);
      renderCards(state);
    });
  
    if (guessId == target.id) {
      confetti();
      document.getElementById("win-overlay").style.display = "flex";
    }
  }

async function main() {
  const target = await fetch(`${API_URL}/daily-article`)
    .then(res => res.json());
  
  console.log("target:", target);

  const state = {
    linksVisible: false,
    guesses: [],
  };

    const tomSelect = new TomSelect("#guess-input", {
      valueField: "id",
      labelField: "title",
      searchField: "title",
      preload: false,
      maxItems: 1,
      closeAfterSelect: true,
      load: function(query, callback) {
        fetch(`${API_URL}/articles?query=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(data => data.filter(article => !state.guesses.some(g => g.id == article.id)))
          .then(data => callback(data))
          .catch(() => callback());
      },
      onItemAdd: function() {
        handleGuessInput(target, state, tomSelect);
      }
    });

  document.getElementById("guess-btn").addEventListener("click", () => handleGuessInput(target, state, tomSelect));
  
  const toggleBtn = document.getElementById("toggle-links-btn");

  toggleBtn.addEventListener("click", () => {
    state.linksVisible = !state.linksVisible;
    state.guesses.forEach(g => g.visible = state.linksVisible);
    renderCards(state);
    document.getElementById("toggle-links-btn").textContent = state.linksVisible ? "Hide links" : "Show links";
    toggleBtn.blur();
  });

  toggleBtn.style.minWidth = toggleBtn.offsetWidth + "px";

  document.getElementById("win-overlay").addEventListener("click", () => {
    document.getElementById("win-overlay").style.display = "none";
  });
  document.getElementById("win-box").addEventListener("click", e => e.stopPropagation());
  document.getElementById("win-close-btn").addEventListener("click", () => {
  document.getElementById("win-overlay").style.display = "none";
});
}

main();