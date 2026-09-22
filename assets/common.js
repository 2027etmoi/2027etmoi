// Constantes et utilitaires partagés par toutes les pages.

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

// Statuts pour lesquels on recense un programme
const EN_LICE = ["declare", "primaire", "pressenti"];

const LIENS = {
  campagne: "Site de campagne",
  parti: "Parti",
  programme: "Programme",
  x: "X",
  instagram: "Instagram",
  youtube: "YouTube",
  wikipedia: "Wikipédia",
};

// Doit rester aligné sur docs/methode-sources.md
const THEMES = {
  economie: "Économie, fiscalité et finances publiques",
  travail: "Travail, salaires et pouvoir d'achat",
  retraites: "Retraites et protection sociale",
  sante: "Santé",
  education: "Éducation, jeunesse et recherche",
  ecologie: "Écologie, climat et énergie",
  immigration: "Immigration et intégration",
  securite: "Sécurité et justice",
  international: "Europe, international et défense",
  institutions: "Institutions et démocratie",
  logement: "Logement",
  territoires: "Agriculture, ruralité et services publics locaux",
};

const NATURES = {
  programme: "Programme",
  declaration: "Déclaration",
  presse: "Presse",
};

const ETATS_PROGRAMME = {
  complet: "Programme complet publié",
  partiel: "Programme partiel",
  aucun: "Pas de programme publié",
};

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

function normalize(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

function extLink(url, label) {
  const u = safeUrl(url);
  return u ? `<a href="${u}" target="_blank" rel="noopener">${esc(label)}</a>` : esc(label);
}

function sourceHtml(src, prefix = "Source : ") {
  if (!src || !safeUrl(src.url)) return "";
  return `<span class="source">${prefix}${extLink(src.url, src.titre || "lien")}${src.date ? `, ${esc(formatDate(src.date))}` : ""}</span>`;
}

function badge(statut) {
  return `<span class="badge ${esc(statut)}">${esc(STATUTS[statut] || statut)}</span>`;
}

function blocHtml(bloc) {
  return `<span class="bloc"><span class="dot ${esc(bloc)}"></span>${esc(BLOCS[bloc] || bloc)}</span>`;
}

function linksHtml(liens) {
  return Object.entries(LIENS)
    .filter(([k]) => safeUrl(liens?.[k]))
    .map(([k, label]) => `<a href="${safeUrl(liens[k])}" target="_blank" rel="noopener">${label}</a>`)
    .join("");
}

async function loadCandidats() {
  const res = await fetch("/data/candidats.json", { cache: "no-cache" });
  if (!res.ok) throw new Error("candidats.json introuvable");
  return res.json();
}

// Renvoie null si le fichier n'existe pas (encore)
async function loadOptional(path) {
  try {
    const res = await fetch(path, { cache: "no-cache" });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

const loadProgramme = (id) => loadOptional(`/data/programmes/${encodeURIComponent(id)}.json`);
const loadBiographie = (id) => loadOptional(`/data/biographies/${encodeURIComponent(id)}.json`);

const ETATS_AFFAIRE = {
  enquete: "Enquête en cours",
  mise_en_examen: "Mise en examen",
  renvoi_proces: "Renvoi devant le tribunal",
  condamnation_non_definitive: "Condamnation non définitive",
  condamnation_definitive: "Condamnation définitive",
  relaxe: "Relaxe",
  instruction_close: "Instruction close",
  non_lieu: "Non-lieu",
  classement: "Classement sans suite",
};

const loadSondages = () => loadOptional("/data/sondages.json");

// Moyenne des intentions de vote par personnalité.
// Un sondage compte pour une voix : on fait d'abord la moyenne des hypothèses
// d'un même sondage, puis la moyenne entre sondages. Voir sondages.html.
function computeMoyennes(data) {
  const perPoll = {}; // id -> [moyenne dans chaque sondage]
  for (const s of data?.sondages || []) {
    const acc = {};
    for (const h of s.hypotheses || []) {
      for (const [id, v] of Object.entries(h.scores || {})) {
        if (typeof v !== "number") continue;
        (acc[id] ||= []).push(v);
      }
    }
    for (const [id, vals] of Object.entries(acc)) {
      (perPoll[id] ||= []).push(vals.reduce((a, b) => a + b, 0) / vals.length);
    }
  }
  const out = {};
  for (const [id, vals] of Object.entries(perPoll)) {
    out[id] = {
      moyenne: vals.reduce((a, b) => a + b, 0) / vals.length,
      n: vals.length,
      min: Math.min(...vals),
      max: Math.max(...vals),
    };
  }
  return out;
}

function formatPct(v) {
  return `${v.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
}

function candidatUrl(id) {
  return `/candidats/${encodeURIComponent(id)}.html`;
}

const loadTempsParole = () => loadOptional("/data/temps-parole.json");

// Durée en minutes → « 2 h 05 » ou « 45 min »
function formatDuree(min) {
  if (typeof min !== "number") return "";
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min`;
}

function formatMois(ym) {
  return formatDate(ym); // « AAAA-MM » → « septembre 2026 »
}

// Dernier mois publié pour un candidat : { mois, tv, radio, total } ou null
function dernierTempsParole(tp, id) {
  const pm = tp?.candidats?.[id]?.par_mois;
  if (!pm) return null;
  const mois = (tp.mois || Object.keys(pm)).filter((m) => pm[m]).sort().pop();
  return mois ? { mois, ...pm[mois] } : null;
}

// Infobulles d'en-tête : <th data-tip-quoi="…" data-tip-calcul="…" data-tip-source="…">
// ajoute une icône « ? » accessible (survol et clavier) avec l'explication.
function initHeaderTips() {
  document.querySelectorAll("th[data-tip-quoi]").forEach((th, i) => {
    const id = `tip-${i}`;
    const part = (label, text) => (text ? `<span class="tip-row"><strong>${label}</strong> ${esc(text)}</span>` : "");
    th.insertAdjacentHTML("beforeend", `<span class="info" tabindex="0" role="button" aria-label="Explication de la colonne" aria-describedby="${id}">?</span>
      <span class="tip" role="tooltip" id="${id}">${part("De quoi s'agit-il ?", th.dataset.tipQuoi)}${part("Calcul :", th.dataset.tipCalcul)}${part("Source :", th.dataset.tipSource)}</span>`);
  });
  const place = (icon) => {
    const tip = icon.nextElementSibling;
    tip.classList.add("open");
    const r = icon.getBoundingClientRect();
    const w = tip.offsetWidth;
    tip.style.left = `${Math.max(12, Math.min(r.left - 12, window.innerWidth - w - 12))}px`;
    tip.style.top = `${r.bottom + 8}px`;
  };
  const hide = (icon) => icon.nextElementSibling.classList.remove("open");
  document.querySelectorAll(".info").forEach((icon) => {
    icon.addEventListener("mouseenter", () => place(icon));
    icon.addEventListener("mouseleave", () => hide(icon));
    icon.addEventListener("focus", () => place(icon));
    icon.addEventListener("blur", () => hide(icon));
    icon.addEventListener("click", (e) => { e.stopPropagation(); place(icon); });
  });
  window.addEventListener("scroll", () => document.querySelectorAll(".tip.open").forEach((t) => t.classList.remove("open")), { passive: true });
}
initHeaderTips();

// Date de dernière mise à jour, affichée dans le pied de page de toutes les pages
(async () => {
  const meta = await loadOptional("/data/meta.json");
  const foot = document.querySelector(".site-footer .footer-grid > div");
  if (!meta || !foot) return;
  const d = meta.donnees && meta.donnees > meta.publication ? meta.donnees : meta.publication;
  foot.insertAdjacentHTML("beforeend", `<p class="maj">Dernière mise à jour : <strong>${esc(formatDate(d))}</strong> · <a href="https://github.com/PhilippeBout/2027etmoi/commits/main" target="_blank" rel="noopener">historique des modifications</a></p>`);
})();

// Menu mobile et lien d'évitement (accessibilité), communs à toutes les pages
(() => {
  const main = document.querySelector("main");
  if (main && !main.id) main.id = "contenu";
  if (main) document.body.insertAdjacentHTML("afterbegin", `<a class="skip" href="#${main.id}">Aller au contenu</a>`);
  const nav = document.querySelector(".site-nav .wrap");
  if (!nav) return;
  nav.insertAdjacentHTML("beforeend", `<button type="button" class="menu-btn" aria-expanded="false" aria-controls="menu">Menu</button>`);
  const links = [...nav.querySelectorAll("a:not(.brand)")];
  const menu = document.createElement("div");
  menu.className = "menu-links"; menu.id = "menu";
  links.forEach((a) => menu.appendChild(a));
  nav.insertBefore(menu, nav.querySelector(".menu-btn"));
  nav.querySelector(".menu-btn").addEventListener("click", (e) => {
    const open = nav.classList.toggle("open");
    e.currentTarget.setAttribute("aria-expanded", String(open));
  });
})();
