// Page « Candidatures en données » : faits vérifiables, sans note ni classement.

const DESIGNATIONS = {
  auto: "Auto-déclaration",
  vote_militants: "Vote des adhérents",
  instance_parti: "Instance du parti",
  primaire_fermee: "Primaire fermée",
  primaire_ouverte: "Primaire ouverte",
  autre: "Autre",
};

const state = { blocs: new Set(), sort: "nom", dir: "asc" };
let rows = [];

const nonConnu = `<span class="props-empty">Non connu</span>`;

function themesCovered(p) {
  if (!p) return null;
  const set = new Set((p.mesures || []).filter((m) => m.nature === "programme").map((m) => m.theme));
  return Object.keys(THEMES).filter((t) => set.has(t));
}

function themeDots(covered) {
  if (covered === null) return nonConnu;
  const dots = Object.entries(THEMES).map(([t, label]) =>
    `<span class="tdot${covered.includes(t) ? " on" : ""}" title="${esc(label)}${covered.includes(t) ? "" : " (non couvert)"}"></span>`).join("");
  return `<div class="tdots" aria-label="${covered.length} thèmes sur 12">${dots}</div><span class="poll-n">${covered.length} / 12</span>`;
}

function cellDeclaration(k) {
  const d = k?.declaration;
  return d?.date ? `${esc(formatDate(d.date))}${sourceHtml(d.source)}` : nonConnu;
}

function cellDesignation(k) {
  const d = k?.designation;
  if (!d?.mode) return nonConnu;
  return `<strong>${esc(DESIGNATIONS[d.mode] || d.mode)}</strong>${d.detail ? `<div class="status-note">${esc(d.detail)}</div>` : ""}${sourceHtml(d.source)}`;
}

function cellPrecedentes(k) {
  const list = k?.precedentes;
  if (!Array.isArray(list)) return nonConnu;
  if (!list.length) return `<span class="props-empty">Aucune</span>`;
  return `<ul class="props">${list.map((x) => `<li><strong>${esc(x.annee)}</strong> : ${esc(x.resultat)}${sourceHtml(x.source)}</li>`).join("")}</ul>`;
}

function cellProgramme(p) {
  if (!p) return `<span class="props-empty">Fiche en préparation</span>`;
  const e = p.programme || {};
  return `${esc(ETATS_PROGRAMME[e.etat] || "Non connu")}${e.url ? `<span class="source">${extLink(e.url, e.titre || "Consulter")}</span>` : ""}`;
}

function cellChiffrage(k) {
  const c = k?.chiffrage;
  if (!c || c.publie === null || c.publie === undefined) return nonConnu;
  return `<strong>${c.publie ? "Publié" : "Non publié"}</strong>${c.detail ? `<div class="status-note">${esc(c.detail)}</div>` : ""}${c.url ? `<span class="source">${extLink(c.url, "Voir le chiffrage")}</span>` : ""}${sourceHtml(c.source)}`;
}

function cellSondage(m, id) {
  return m ? `<a class="poll" href="/sondages.html#${encodeURIComponent(id)}">${formatPct(m.moyenne)}</a><span class="poll-n">${m.n} sondage${m.n > 1 ? "s" : ""}</span>` : `<span class="props-empty">Non testé</span>`;
}

function cellParole(tp, id) {
  const d = dernierTempsParole(tp, id);
  if (!tp) return nonConnu;
  if (!d) return `<span class="props-empty" title="Absent des relevés Arcom de ${esc(formatMois(tp.mois?.[0]))} à ${esc(formatMois(tp.mois?.at(-1)))}, ou moins d'une minute par mois">Non relevé</span>`;
  return `<strong>${esc(formatDuree(d.total))}</strong><span class="poll-n">${esc(formatMois(d.mois))}</span>`
    + `<span class="poll-n">TV ${d.tv == null ? "—" : esc(formatDuree(d.tv))} · radio ${d.radio == null ? "—" : esc(formatDuree(d.radio))}</span>`;
}

function cellEvaluations(evals, instById, id) {
  const mine = evals.filter((e) => (e.candidats || []).includes(id));
  if (!mine.length) return `<span class="props-empty">Aucune recensée</span>`;
  return `<ul class="props">${mine.map((e) => {
    const url = e.liens_par_candidat?.[id] || e.url;
    return `<li>${extLink(url, instById[e.institution]?.nom || e.institution)}${e.date ? ` <span class="source">${esc(formatDate(e.date))}</span>` : ""}</li>`;
  }).join("")}</ul>`;
}

function sortKey(r) {
  switch (state.sort) {
    case "declaration": return r.k?.declaration?.date || "9999";
    case "designation": return DESIGNATIONS[r.k?.designation?.mode] || "~";
    case "programme": return ["complet", "partiel", "aucun"].indexOf(r.p?.programme?.etat) + 1 || 9;
    case "themes": return -(r.themes?.length ?? -1);
    case "chiffrage": return r.k?.chiffrage?.publie === true ? 0 : r.k?.chiffrage?.publie === false ? 1 : 2;
    case "sondage": return -(r.m?.moyenne ?? -1);
    case "parole": return -(r.tp?.total ?? -1);
    default: return r.c.id; // l’id est le nom de famille : tri alphabétique par nom
  }
}

function render() {
  const list = rows
    .filter((r) => !state.blocs.size || state.blocs.has(r.c.bloc))
    .sort((a, b) => {
      const ka = sortKey(a), kb = sortKey(b);
      let d = typeof ka === "number" ? ka - kb : String(ka).localeCompare(String(kb), "fr");
      if (d === 0) d = a.c.id.localeCompare(b.c.id, "fr");
      return state.dir === "asc" ? d : -d;
    });
  $("rows").innerHTML = list.map((r) => r.html).join("");
  $("count").textContent = `${list.length} candidature${list.length > 1 ? "s" : ""}`;
  document.querySelectorAll("thead button").forEach((b) => { b.dataset.dir = b.dataset.sort === state.sort ? state.dir : ""; });
}

async function init() {
  const [cands, sondages, cand, evals, tparole] = await Promise.all([
    loadCandidats(), loadSondages(), loadOptional("/data/candidatures.json"), loadOptional("/data/evaluations.json"), loadTempsParole(),
  ]);
  const moy = computeMoyennes(sondages);
  const instById = Object.fromEntries((evals?.institutions || []).map((i) => [i.id, i]));
  const evalList = evals?.evaluations || [];
  const actifs = (cands.candidats || []).filter((c) => EN_LICE.includes(c.statut));
  const progs = await Promise.all(actifs.map((c) => loadProgramme(c.id)));

  rows = actifs.map((c, i) => {
    const p = progs[i];
    const k = cand?.candidatures?.[c.id];
    const m = moy[c.id];
    const themes = themesCovered(p);
    return {
      c, p, k, m, themes, tp: dernierTempsParole(tparole, c.id),
      html: `<tr>
        <td data-label="Candidat"><a class="name" href="${candidatUrl(c.id)}">${esc(c.nom)}</a><div class="party">${esc(c.parti)}</div>${blocHtml(c.bloc)} ${badge(c.statut)}</td>
        <td data-label="Déclaration">${cellDeclaration(k)}</td>
        <td data-label="Désignation">${cellDesignation(k)}</td>
        <td data-label="Présidentielles passées">${cellPrecedentes(k)}</td>
        <td data-label="Programme">${cellProgramme(p)}</td>
        <td data-label="Thèmes couverts (document officiel)">${themeDots(themes)}</td>
        <td data-label="Chiffrage">${cellChiffrage(k)}</td>
        <td data-label="Sondages (moyenne)">${cellSondage(m, c.id)}</td>
        <td data-label="Temps de parole TV et radio">${cellParole(tparole, c.id)}</td>
        <td data-label="Évaluations externes">${cellEvaluations(evalList, instById, c.id)}</td>
      </tr>`,
    };
  });

  // Filtre par famille politique
  const present = new Set(actifs.map((c) => c.bloc));
  for (const [key, label] of Object.entries(BLOCS)) {
    if (!present.has(key)) continue;
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.setAttribute("aria-pressed", "false");
    b.innerHTML = `<span class="dot ${key}"></span>${esc(label)}`;
    b.addEventListener("click", () => {
      state.blocs.has(key) ? state.blocs.delete(key) : state.blocs.add(key);
      b.setAttribute("aria-pressed", String(state.blocs.has(key)));
      render();
    });
    $("f-bloc").appendChild(b);
  }
  document.querySelectorAll("thead button").forEach((b) => b.addEventListener("click", () => {
    if (state.sort === b.dataset.sort) state.dir = state.dir === "asc" ? "desc" : "asc";
    else { state.sort = b.dataset.sort; state.dir = "asc"; }
    render();
  }));

  if (evals?.institutions?.length) {
    $("institutions").innerHTML = evals.institutions.map((inst) => {
      const ev = evalList.filter((e) => e.institution === inst.id);
      return `<div class="card inst">
        <h3>${extLink(inst.url, inst.nom)}</h3>
        ${inst.presentation ? `<p>${esc(inst.presentation)}</p>` : ""}
        ${inst.orientation?.texte ? `<p class="notice"><strong>Orientation ou statut :</strong> ${esc(inst.orientation.texte)}</p>${sourceHtml(inst.orientation.source)}` : ""}
        ${ev.length ? `<ul class="plain">${ev.map((e) => `<li>${extLink(e.url, e.titre)}${e.date ? ` <span class="source">${esc(formatDate(e.date))}</span>` : ""}${e.methode ? `<div class="notice">${esc(e.methode)}</div>` : ""}<div class="notice">Candidats couverts : ${(e.candidats || []).length}</div></li>`).join("")}</ul>` : ""}
      </div>`;
    }).join("") + `<p class="notice">${evals.institutions.length === 1 ? "Une seule institution recensée" : `${evals.institutions.length} institutions recensées`}${evals.mise_a_jour ? ` au ${esc(formatDate(evals.mise_a_jour))}` : ""}. Cela reflète l'état des publications à cette date, pas un choix éditorial : toute évaluation multi-candidats publiée par une institution sera ajoutée, quelle que soit son orientation.</p>`;
  }

  render();
}

init();
