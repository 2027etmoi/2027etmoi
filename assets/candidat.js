// Page candidat : programme et propositions d'abord, puis biographie, en blocs repliables.

function measureItem(m) {
  return `<li>${esc(m.texte)} <span class="tag ${esc(m.nature)}">${esc(NATURES[m.nature] || m.nature)}</span>${sourceHtml(m.source)}</li>`;
}

// Bloc repliable de premier niveau
function fold(title, content, { open = false, count = null, id = "" } = {}) {
  return `<details class="section fold"${id ? ` id="${id}"` : ""}${open ? " open" : ""}>
    <summary><h2>${esc(title)}</h2>${count !== null ? `<span class="fold-count">${count}</span>` : ""}</summary>
    <div class="fold-body">${content}</div>
  </details>`;
}

function programmeSections(c, p) {
  if (!p) {
    const why = EN_LICE.includes(c.statut)
      ? "La fiche programme de cette personnalité est en cours de préparation."
      : "Cette personnalité n'est pas candidate : aucun programme n'est recensé.";
    return `<section class="section"><p class="notice">${why}</p></section>`;
  }

  const prog = p.programme || {};
  const progCard = `<div class="card">
      <strong>${esc(ETATS_PROGRAMME[prog.etat] || "État du programme non renseigné")}</strong>
      ${prog.titre ? `<div>${prog.url ? extLink(prog.url, prog.titre) : esc(prog.titre)}</div>` : ""}
      ${prog.note ? `<p class="notice">${esc(prog.note)}</p>` : ""}
    </div>`;

  const byTheme = {};
  for (const m of p.mesures || []) (byTheme[m.theme] ||= []).push(m);
  const themes = Object.keys(THEMES).filter((t) => byTheme[t]);
  const total = (p.mesures || []).length;

  const mesures = themes.length
    ? `<div class="fold-tools">
        <button type="button" class="chip" data-toggle-all="open">Tout déplier</button>
        <button type="button" class="chip" data-toggle-all="close">Tout replier</button>
      </div>
      ${themes.map((t) => `<details class="card theme-block" id="t-${t}">
          <summary><h3>${esc(THEMES[t])}</h3><span class="fold-count">${byTheme[t].length}</span></summary>
          <ul class="measures">${byTheme[t].map(measureItem).join("")}</ul>
        </details>`).join("")}
      <p class="notice">Les thèmes absents n'ont pas de proposition sourcée à ce jour. <span class="tag programme">Programme</span> document officiel de campagne · <span class="tag declaration">Déclaration</span> propos du candidat rapportés · <span class="tag presse">Presse</span> mesure décrite par un média.</p>`
    : `<p class="notice">Aucune proposition sourcée n'a été recensée à ce jour.</p>`;

  return fold("Programme", progCard, { open: true })
    + fold("Propositions par thème", mesures, { count: total, id: "propositions" });
}

function photoHtml(b, nom) {
  const ph = b?.photo;
  if (!ph || !safeUrl(ph.url)) return "";
  const credit = [ph.auteur, ph.licence].filter(Boolean).map(esc).join(" · ");
  return `<figure class="portrait">
    <img src="${safeUrl(ph.url)}" alt="Portrait de ${esc(nom)}">
    <figcaption>${ph.legende ? esc(ph.legende) + "<br>" : ""}${ph.page ? extLink(ph.page, credit || "Wikimedia Commons") : credit}</figcaption>
  </figure>`;
}

// Présentation courte affichée sous le nom, dans l'en-tête
function presentationHtml(b) {
  if (!b?.presentation?.texte) return "";
  const naiss = b.naissance?.date
    ? ` Né(e) le ${esc(formatDate(b.naissance.date))}${b.naissance.lieu ? ` à ${esc(b.naissance.lieu)}` : ""}.`
    : "";
  return `<div class="presentation">
    <p class="lede">${esc(b.presentation.texte)}${naiss}</p>
    ${(b.presentation.sources || []).map((s) => sourceHtml(s)).join("")}
  </div>`;
}

function timeline(items) {
  return `<ul class="timeline">${items.map((e) => `<li><span class="period">${esc(e.periode || "")}</span><div>${esc(e.texte)}${sourceHtml(e.source)}</div></li>`).join("")}</ul>`;
}

function bioSections(b, p) {
  let html = "";
  if ((p?.reperes || []).length) {
    html += fold("Repères", `<div class="card"><ul class="plain">${p.reperes.map((r) => `<li>${esc(r.texte)}${sourceHtml(r.source)}</li>`).join("")}</ul></div>`,
      { count: p.reperes.length });
  }
  if ((b?.parcours_politique || []).length) {
    html += fold("Parcours politique", `<div class="card">${timeline(b.parcours_politique)}</div>`, { count: b.parcours_politique.length });
  }
  if ((b?.parcours_professionnel || []).length) {
    html += fold("Formation et parcours professionnel", `<div class="card">${timeline(b.parcours_professionnel)}</div>`, { count: b.parcours_professionnel.length });
  }
  if (Array.isArray(b?.affaires)) {
    const body = b.affaires.length
      ? b.affaires.map((a) => `<div class="card affaire">
          <h3>${esc(a.titre)}</h3>
          <span class="badge ${/condamnation/.test(a.etat) ? "empeche" : /relaxe|non_lieu|classement|instruction_close/.test(a.etat) ? "renonce" : "pressenti"}">${esc(ETATS_AFFAIRE[a.etat] || a.etat)}</span>
          <p>${esc(a.texte)}</p>
          ${a.etat_detail ? `<p class="notice">${esc(a.etat_detail)}${a.date_etat ? ` (état au ${esc(formatDate(a.date_etat))})` : ""}</p>` : ""}
          ${(a.sources || []).map((s) => sourceHtml(s)).join("")}
        </div>`).join("")
      : `<p class="notice">Aucune procédure judiciaire n'est mentionnée à ce jour pour cette personnalité.</p>`;
    html += fold("Affaires judiciaires", `${body}
      <p class="notice">Toute personne non définitivement condamnée est présumée innocente. Ne sont publiées que les procédures visant personnellement la personnalité, rapportées par des médias reconnus et dont l'état a pu être vérifié, avec la date de cet état. Cette rubrique peut donc être incomplète.</p>`,
      { count: b.affaires.length });
  }
  if ((p?.ressources || []).length) {
    html += fold("Pour aller plus loin", `<div class="card"><ul class="plain">${p.ressources.map((r) => `<li>${extLink(r.url, r.titre)}${r.date ? ` <span class="source">${esc(formatDate(r.date))}</span>` : ""}</li>`).join("")}</ul></div>`,
      { count: p.ressources.length });
  }
  return html;
}

// Ouvre le bloc visé par une ancre (#t-retraites…) et ses parents
function openTarget(hash) {
  const el = hash && document.getElementById(decodeURIComponent(hash.slice(1)));
  if (!el) return;
  for (let d = el.closest("details"); d; d = d.parentElement?.closest("details")) d.open = true;
  el.scrollIntoView();
}

async function init() {
  const id = new URLSearchParams(location.search).get("id");
  const main = $("main");
  let data;
  try {
    data = await loadCandidats();
  } catch {
    $("loading").textContent = "Impossible de charger les données.";
    return;
  }
  const c = (data.candidats || []).find((x) => x.id === id);
  if (!c) {
    $("loading").textContent = "Candidat introuvable.";
    return;
  }

  document.title = `${c.nom} — 2027 et moi`;
  const [p, b, sondages] = await Promise.all([loadProgramme(c.id), loadBiographie(c.id), loadSondages()]);
  const m = computeMoyennes(sondages)[c.id];

  const head = `<header class="site-header cand-header" style="padding-top:16px">
      ${photoHtml(b, c.nom)}
      <div>
      <p class="kicker">${esc(c.parti)}</p>
      <h1>${esc(c.nom)}</h1>
      <div class="cand-head">${blocHtml(c.bloc)} ${badge(c.statut)}
        ${m ? `<a class="poll" href="sondages.html#${encodeURIComponent(c.id)}">${formatPct(m.moyenne)}</a><span class="notice">moyenne de ${m.n} sondage${m.n > 1 ? "s" : ""}</span>` : ""}
      </div>
      ${presentationHtml(b)}
      ${c.statut_detail ? `<p class="status-line"><strong>Candidature :</strong> ${esc(c.statut_detail)}</p>` : ""}
      ${sourceHtml(c.source)}
      <div class="cand-head"><div class="links">${linksHtml(c.liens)}</div></div>
      ${EN_LICE.includes(c.statut) ? `<a class="cta" href="comparateur.html?c=${encodeURIComponent(c.id)}">Comparer avec d'autres candidats</a>` : ""}
      </div>
    </header>`;

  $("loading").remove();
  main.insertAdjacentHTML("beforeend", head + programmeSections(c, p) + bioSections(b, p));

  main.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-toggle-all]");
    if (!btn) return;
    const open = btn.dataset.toggleAll === "open";
    btn.closest(".fold-body").querySelectorAll("details.theme-block").forEach((d) => { d.open = open; });
  });
  window.addEventListener("hashchange", () => openTarget(location.hash));
  openTarget(location.hash);
}

init();
