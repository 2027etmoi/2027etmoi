// Page Actualité : filtres par candidat et par thème sur la liste statique (lisible sans JavaScript).

(function () {
  const feed = document.getElementById("feed");
  const bar = document.getElementById("filtres");
  if (!feed || !bar) return;
  bar.classList.remove("needs-js");

  const items = Array.from(feed.querySelectorAll("li[data-cand]"));
  const select = bar.querySelector("select");
  const chips = Array.from(bar.querySelectorAll(".chip[data-theme]"));
  const count = document.getElementById("feed-count");
  const state = { cand: "", theme: "" };

  function apply(majAdresse = true) {
    let n = 0;
    for (const li of items) {
      const ok = (!state.cand || li.dataset.cand === state.cand)
        && (!state.theme || li.dataset.themes.split(" ").includes(state.theme));
      li.hidden = !ok;
      if (ok) n++;
    }
    // Un mois sans prise de parole visible disparaît avec son titre
    for (const ul of feed.querySelectorAll("ul.feed")) {
      const vide = !ul.querySelector("li:not([hidden])");
      ul.hidden = vide;
      const h = ul.previousElementSibling;
      if (h && h.classList.contains("feed-month")) h.hidden = vide;
    }
    for (const ch of chips) ch.setAttribute("aria-pressed", String(ch.dataset.theme === state.theme));
    if (count) count.textContent = `${n} prise${n > 1 ? "s" : ""} de parole affichée${n > 1 ? "s" : ""} sur ${items.length}`;
    const h = state.cand ? `#${state.cand}` : "";
    if (majAdresse && location.hash !== h) history.replaceState(null, "", location.pathname + h);
  }

  select.addEventListener("change", () => { state.cand = select.value; apply(); });
  bar.addEventListener("click", (e) => {
    const ch = e.target.closest(".chip[data-theme]");
    if (!ch) return;
    state.theme = state.theme === ch.dataset.theme ? "" : ch.dataset.theme;
    apply();
  });

  // /actualite.html#le-pen : présélection du candidat
  const cible = decodeURIComponent(location.hash.slice(1));
  if (cible && Array.from(select.options).some((o) => o.value === cible)) {
    select.value = cible;
    state.cand = cible;
  }
  // Au chargement, l'ancre d'une prise de parole (lien du flux RSS) est conservée
  apply(false);
})();
