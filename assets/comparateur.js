// Comparateur : propositions de 1 à 4 candidats, thème par thème.

const MAX = 4;
const sel = { cands: [], themes: new Set() };
const programmes = {}; // id -> fiche (ou null si absente)
let byId = {};

function readUrl() {
  const q = new URLSearchParams(location.search);
  sel.cands = (q.get("c") || "").split(",").filter((id) => byId[id]).slice(0, MAX);
  (q.get("t") || "").split(",").filter((t) => THEMES[t]).forEach((t) => sel.themes.add(t));
}

function writeUrl() {
  const q = new URLSearchParams();
  if (sel.cands.length) q.set("c", sel.cands.join(","));
  if (sel.themes.size) q.set("t", [...sel.themes].join(","));
  history.replaceState(null, "", q.toString() ? `?${q}` : location.pathname);
}

function chip(label, pressed, onClick, dot) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.setAttribute("aria-pressed", String(pressed));
  b.innerHTML = (dot ? `<span class="dot ${dot}"></span>` : "") + esc(label);
  b.addEventListener("click", onClick);
  return b;
}

function buildPickers(candidats) {
  const pc = $("pick-cand");
  const order = Object.keys(BLOCS);
  candidats
    .filter((c) => EN_LICE.includes(c.statut))
    .sort((a, b) => order.indexOf(a.bloc) - order.indexOf(b.bloc) || a.id.localeCompare(b.id, "fr"))
    .forEach((c) => {
      const b = chip(c.nom, sel.cands.includes(c.id), async () => {
        const i = sel.cands.indexOf(c.id);
        if (i >= 0) sel.cands.splice(i, 1);
        else if (sel.cands.length < MAX) sel.cands.push(c.id);
        else return;
        b.setAttribute("aria-pressed", String(sel.cands.includes(c.id)));
        await render();
      }, c.bloc);
      pc.appendChild(b);
    });

  const pt = $("pick-theme");
  const all = chip("Tous", sel.themes.size === 0, () => {
    sel.themes.clear();
    pt.querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", String(x === all)));
    render();
  });
  pt.appendChild(all);
  for (const [t, label] of Object.entries(THEMES)) {
    const b = chip(label, sel.themes.has(t), () => {
      sel.themes.has(t) ? sel.themes.delete(t) : sel.themes.add(t);
      b.setAttribute("aria-pressed", String(sel.themes.has(t)));
      all.setAttribute("aria-pressed", String(sel.themes.size === 0));
      render();
    });
    pt.appendChild(b);
  }
}

function cell(id, theme) {
  const c = byId[id];
  const p = programmes[id];
  const ms = (p?.mesures || []).filter((m) => m.theme === theme);
  const body = !p
    ? `<p class="props-empty">Fiche programme en préparation.</p>`
    : ms.length
      ? `<ul class="measures">${ms.map((m) => `<li>${esc(m.texte)} <span class="tag ${esc(m.nature)}">${esc(NATURES[m.nature] || m.nature)}</span>${sourceHtml(m.source)}</li>`).join("")}</ul>`
      : `<p class="props-empty">Pas de proposition sourcée sur ce thème.</p>`;
  return `<div class="card compare-col">
    <h4><span class="dot ${esc(c.bloc)}"></span><a href="${candidatUrl(id)}">${esc(c.nom)}</a></h4>${body}</div>`;
}

async function render() {
  $("nsel").textContent = sel.cands.length;
  writeUrl();
  await Promise.all(sel.cands.filter((id) => !(id in programmes)).map(async (id) => {
    programmes[id] = await loadProgramme(id);
  }));

  if (!sel.cands.length) {
    $("result").innerHTML = `<p class="hint">Sélectionnez au moins un candidat ci-dessus.</p>`;
    return;
  }
  const themes = sel.themes.size ? Object.keys(THEMES).filter((t) => sel.themes.has(t)) : Object.keys(THEMES);
  $("result").innerHTML = themes.map((t) => `<section class="compare-theme">
      <h3 class="th-${t}">${esc(THEMES[t])}</h3>
      <div class="compare-grid" style="--cols:${sel.cands.length}">${sel.cands.map((id) => cell(id, t)).join("")}</div>
    </section>`).join("");
}

async function init() {
  let data;
  try {
    data = await loadCandidats();
  } catch {
    $("result").textContent = "Impossible de charger les données.";
    return;
  }
  byId = Object.fromEntries((data.candidats || []).map((c) => [c.id, c]));
  readUrl();
  buildPickers(data.candidats || []);
  await render();
}

init();
