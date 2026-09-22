// Page d'accueil : tableau filtrable et triable des candidats.

const state = { q: "", blocs: new Set(), statuts: new Set(), sort: "statut", dir: "asc" };
let candidats = [];
let moyennes = {};

function buildChips(container, dict, set, field) {
  const present = new Set(candidats.map((c) => c[field]));
  for (const [key, label] of Object.entries(dict)) {
    if (!present.has(key)) continue;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.setAttribute("aria-pressed", "false");
    b.innerHTML = (field === "bloc" ? `<span class="dot ${key}"></span>` : "") + esc(label);
    b.addEventListener("click", () => {
      set.has(key) ? set.delete(key) : set.add(key);
      b.setAttribute("aria-pressed", String(set.has(key)));
      render();
    });
    container.appendChild(b);
  }
}

function matches(c) {
  if (state.blocs.size && !state.blocs.has(c.bloc)) return false;
  if (state.statuts.size && !state.statuts.has(c.statut)) return false;
  if (!state.q) return true;
  return normalize([c.nom, c.parti, c.statut_detail, ...(c.propositions || [])].join(" ")).includes(state.q);
}

function compare(a, b) {
  const order = (dict, k) => Object.keys(dict).indexOf(k);
  let r = 0;
  if (state.sort === "bloc") r = order(BLOCS, a.bloc) - order(BLOCS, b.bloc);
  else if (state.sort === "statut") r = order(STATUTS, a.statut) - order(STATUTS, b.statut);
  // Plus haut score en premier ; les personnalités non testées à la fin
  else if (state.sort === "sondage") r = (moyennes[b.id]?.moyenne ?? -1) - (moyennes[a.id]?.moyenne ?? -1);
  if (r === 0) r = a.nom.localeCompare(b.nom, "fr");
  return state.dir === "asc" ? r : -r;
}

function row(c) {
  const props = (c.propositions || []).length
    ? `<ul class="props">${c.propositions.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`
    : `<span class="props-empty">Pas encore de programme publié</span>`;
  const links = linksHtml(c.liens);
  const m = moyennes[c.id];
  const poll = m
    ? `<a class="poll" href="sondages.html#${encodeURIComponent(c.id)}" title="Moyenne sur ${m.n} sondage${m.n > 1 ? "s" : ""}, de ${formatPct(m.min)} à ${formatPct(m.max)}">${formatPct(m.moyenne)}</a>
       <span class="poll-n">${m.n} sondage${m.n > 1 ? "s" : ""}</span>`
    : `<span class="props-empty">Non testé</span>`;

  return `<tr class="${c.statut === "renonce" ? "retire" : ""}">
    <td data-label="Candidat"><a class="name" href="${candidatUrl(c.id)}">${esc(c.nom)}</a><div class="party">${esc(c.parti)}</div></td>
    <td data-label="Famille">${blocHtml(c.bloc)}</td>
    <td data-label="Statut">${badge(c.statut)}
      ${c.statut_detail ? `<div class="status-note">${esc(c.statut_detail)}</div>` : ""}${sourceHtml(c.source)}</td>
    <td data-label="Sondages (moyenne)">${poll}</td>
    <td data-label="Propositions phares">${props}</td>
    <td data-label="Liens"><div class="links">${links || '<span class="props-empty">—</span>'}</div></td>
  </tr>`;
}

function render() {
  const list = candidats.filter(matches).sort(compare);
  $("rows").innerHTML = list.map(row).join("");
  $("empty").hidden = list.length > 0;
  $("count").textContent = `${list.length} personnalité${list.length > 1 ? "s" : ""} sur ${candidats.length}`;
  document.querySelectorAll("thead button").forEach((b) => {
    b.dataset.dir = b.dataset.sort === state.sort ? state.dir : "";
  });
}

async function init() {
  try {
    const data = await loadCandidats();
    candidats = data.candidats || [];
    if (data.mise_a_jour) $("meta").textContent = `Données mises à jour le ${formatDate(data.mise_a_jour)}.`;
    moyennes = computeMoyennes(await loadSondages());
  } catch {
    $("count").textContent = "Impossible de charger les données.";
    return;
  }

  buildChips($("f-bloc"), BLOCS, state.blocs, "bloc");
  buildChips($("f-statut"), STATUTS, state.statuts, "statut");

  $("q").addEventListener("input", (e) => {
    state.q = normalize(e.target.value.trim());
    render();
  });
  document.querySelectorAll("thead button").forEach((b) => {
    b.addEventListener("click", () => {
      if (state.sort === b.dataset.sort) state.dir = state.dir === "asc" ? "desc" : "asc";
      else { state.sort = b.dataset.sort; state.dir = "asc"; }
      render();
    });
  });

  render();
}

init();
