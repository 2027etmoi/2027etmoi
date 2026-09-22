// Affiche data/candidats.json sous forme de tableau filtrable et triable.

const BLOCS = {
  gauche: "Gauche",
  ecolo: "Écologistes",
  centre: "Centre",
  droite: "Droite",
  extdroite: "Droite nationaliste",
  autre: "Autres",
};

const STATUTS = {
  declare: "Déclaré",
  primaire: "En primaire",
  pressenti: "Pressenti",
  empeche: "Empêché",
  renonce: "Pas candidat",
};

const LIENS = {
  campagne: "Site de campagne",
  parti: "Parti",
  programme: "Programme",
  x: "X",
  instagram: "Instagram",
  youtube: "YouTube",
  wikipedia: "Wikipédia",
};

const state = { q: "", blocs: new Set(), statuts: new Set(), sort: "statut", dir: "asc" };
let candidats = [];

const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function safeUrl(u) {
  return /^https?:\/\//i.test(u || "") ? esc(u) : null;
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  // "2026-09" : date connue au mois près seulement
  const opts = /^\d{4}-\d{2}$/.test(iso) ? { month: "long", year: "numeric" } : { day: "numeric", month: "long", year: "numeric" };
  return d.toLocaleDateString("fr-FR", opts);
}

function buildChips(container, dict, set) {
  const present = new Set(candidats.map((c) => (dict === BLOCS ? c.bloc : c.statut)));
  for (const [key, label] of Object.entries(dict)) {
    if (!present.has(key)) continue;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.setAttribute("aria-pressed", "false");
    b.innerHTML = (dict === BLOCS ? `<span class="dot ${key}"></span>` : "") + esc(label);
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
  const hay = [c.nom, c.parti, c.statut_detail, ...(c.propositions || [])]
    .join(" ").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  return hay.includes(state.q);
}

function compare(a, b) {
  const order = (dict, k) => Object.keys(dict).indexOf(k);
  let r;
  if (state.sort === "bloc") r = order(BLOCS, a.bloc) - order(BLOCS, b.bloc);
  else if (state.sort === "statut") r = order(STATUTS, a.statut) - order(STATUTS, b.statut);
  else r = 0;
  if (r === 0) r = a.nom.localeCompare(b.nom, "fr");
  return state.dir === "asc" ? r : -r;
}

function row(c) {
  const src = c.source?.url && safeUrl(c.source.url)
    ? `<span class="source">Source : <a href="${safeUrl(c.source.url)}" target="_blank" rel="noopener">${esc(c.source.titre || "lien")}</a>${c.source.date ? `, ${esc(formatDate(c.source.date))}` : ""}</span>`
    : "";
  const props = (c.propositions || []).length
    ? `<ul class="props">${c.propositions.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`
    : `<span class="props-empty">Pas encore de programme publié</span>`;
  const links = Object.entries(LIENS)
    .filter(([k]) => safeUrl(c.liens?.[k]))
    .map(([k, label]) => `<a href="${safeUrl(c.liens[k])}" target="_blank" rel="noopener">${label}</a>`)
    .join("");

  return `<tr class="${c.statut === "renonce" ? "retire" : ""}">
    <td data-label="Candidat"><div class="name">${esc(c.nom)}</div><div class="party">${esc(c.parti)}</div></td>
    <td data-label="Famille"><span class="bloc"><span class="dot ${esc(c.bloc)}"></span>${esc(BLOCS[c.bloc] || c.bloc)}</span></td>
    <td data-label="Statut"><span class="badge ${esc(c.statut)}">${esc(STATUTS[c.statut] || c.statut)}</span>
      ${c.statut_detail ? `<div class="status-note">${esc(c.statut_detail)}</div>` : ""}${src}</td>
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
    const res = await fetch("data/candidats.json", { cache: "no-cache" });
    const data = await res.json();
    candidats = data.candidats || [];
    if (data.mise_a_jour) $("meta").textContent = `Données mises à jour le ${formatDate(data.mise_a_jour)}.`;
  } catch (e) {
    $("count").textContent = "Impossible de charger les données.";
    return;
  }

  buildChips($("f-bloc"), BLOCS, state.blocs);
  buildChips($("f-statut"), STATUTS, state.statuts);

  $("q").addEventListener("input", (e) => {
    state.q = e.target.value.trim().toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
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
