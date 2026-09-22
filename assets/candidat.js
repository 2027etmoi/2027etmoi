// Page candidat : statut, programme, propositions par thème, ressources.

function measureItem(m) {
  return `<li>${esc(m.texte)} <span class="tag ${esc(m.nature)}">${esc(NATURES[m.nature] || m.nature)}</span>${sourceHtml(m.source)}</li>`;
}

function programmeSection(c, p) {
  if (!p) {
    const why = EN_LICE.includes(c.statut)
      ? "La fiche programme de cette personnalité est en cours de préparation."
      : "Cette personnalité n'est pas candidate : aucun programme n'est recensé.";
    return `<section class="section"><p class="notice">${why}</p></section>`;
  }

  const prog = p.programme || {};
  const progCard = `<section class="section">
    <h2>Programme</h2>
    <div class="card">
      <strong>${esc(ETATS_PROGRAMME[prog.etat] || "État du programme non renseigné")}</strong>
      ${prog.titre ? `<div>${prog.url ? extLink(prog.url, prog.titre) : esc(prog.titre)}</div>` : ""}
      ${prog.note ? `<p class="notice">${esc(prog.note)}</p>` : ""}
    </div>
  </section>`;

  const reperes = (p.reperes || []).length
    ? `<section class="section"><h2>Repères</h2><div class="card"><ul class="plain">${p.reperes.map((r) => `<li>${esc(r.texte)}${sourceHtml(r.source)}</li>`).join("")}</ul></div></section>`
    : "";

  const byTheme = {};
  for (const m of p.mesures || []) (byTheme[m.theme] ||= []).push(m);
  const themes = Object.keys(THEMES).filter((t) => byTheme[t]);
  const mesures = themes.length
    ? `<section class="section">
        <h2>Propositions par thème</h2>
        <nav class="toc" aria-label="Thèmes">${themes.map((t) => `<a href="#t-${t}">${esc(THEMES[t])} (${byTheme[t].length})</a>`).join("")}</nav>
        ${themes.map((t) => `<div class="card theme-block" id="t-${t}"><h3>${esc(THEMES[t])}</h3><ul class="measures">${byTheme[t].map(measureItem).join("")}</ul></div>`).join("")}
        <p class="notice">Les thèmes absents n'ont pas de proposition sourcée à ce jour. <span class="tag programme">Programme</span> document officiel de campagne · <span class="tag declaration">Déclaration</span> propos du candidat rapportés · <span class="tag presse">Presse</span> mesure décrite par un média.</p>
      </section>`
    : `<section class="section"><h2>Propositions</h2><p class="notice">Aucune proposition sourcée n'a été recensée à ce jour.</p></section>`;

  const ressources = (p.ressources || []).length
    ? `<section class="section"><h2>Pour aller plus loin</h2><div class="card"><ul class="plain">${p.ressources.map((r) => `<li>${extLink(r.url, r.titre)}${r.date ? ` <span class="source">${esc(formatDate(r.date))}</span>` : ""}</li>`).join("")}</ul></div></section>`
    : "";

  const maj = p.mise_a_jour ? `<p class="meta">Fiche mise à jour le ${esc(formatDate(p.mise_a_jour))}.</p>` : "";
  return progCard + reperes + mesures + ressources + maj;
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

function timeline(items) {
  return `<ul class="timeline">${items.map((e) => `<li><span class="period">${esc(e.periode || "")}</span><div>${esc(e.texte)}${sourceHtml(e.source)}</div></li>`).join("")}</ul>`;
}

function bioSections(b) {
  if (!b) return "";
  let html = "";
  if (b.presentation?.texte) {
    const naiss = b.naissance?.date
      ? `<p class="notice">Né(e) le ${esc(formatDate(b.naissance.date))}${b.naissance.lieu ? ` à ${esc(b.naissance.lieu)}` : ""}.</p>`
      : "";
    html += `<section class="section"><h2>Présentation</h2><div class="card">
      <p style="margin-top:0">${esc(b.presentation.texte)}</p>${naiss}
      ${(b.presentation.sources || []).map((s) => sourceHtml(s)).join("")}
    </div></section>`;
  }
  if ((b.parcours_politique || []).length) {
    html += `<section class="section"><h2>Parcours politique</h2><div class="card">${timeline(b.parcours_politique)}</div></section>`;
  }
  if ((b.parcours_professionnel || []).length) {
    html += `<section class="section"><h2>Formation et parcours professionnel</h2><div class="card">${timeline(b.parcours_professionnel)}</div></section>`;
  }
  if (Array.isArray(b.affaires)) {
    const body = b.affaires.length
      ? b.affaires.map((a) => `<div class="card affaire">
          <h3>${esc(a.titre)}</h3>
          <span class="badge ${/condamnation/.test(a.etat) ? "empeche" : /relaxe|non_lieu|classement|instruction_close/.test(a.etat) ? "renonce" : "pressenti"}">${esc(ETATS_AFFAIRE[a.etat] || a.etat)}</span>
          <p>${esc(a.texte)}</p>
          ${a.etat_detail ? `<p class="notice">${esc(a.etat_detail)}${a.date_etat ? ` (état au ${esc(formatDate(a.date_etat))})` : ""}</p>` : ""}
          ${(a.sources || []).map((s) => sourceHtml(s)).join("")}
        </div>`).join("")
      : `<p class="notice">Aucune procédure judiciaire n'est mentionnée à ce jour pour cette personnalité.</p>`;
    html += `<section class="section"><h2>Affaires judiciaires</h2>${body}
      <p class="notice">Toute personne non définitivement condamnée est présumée innocente. Ne sont publiées que les procédures visant personnellement la personnalité, rapportées par des médias reconnus et dont l'état a pu être vérifié, avec la date de cet état. Cette rubrique peut donc être incomplète.</p></section>`;
  }
  return html;
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
      ${c.statut_detail ? `<p class="lede">${esc(c.statut_detail)}</p>` : ""}
      ${sourceHtml(c.source)}
      <div class="cand-head"><div class="links">${linksHtml(c.liens)}</div></div>
      ${EN_LICE.includes(c.statut) ? `<a class="cta" href="comparateur.html?c=${encodeURIComponent(c.id)}">Comparer avec d'autres candidats</a>` : ""}
      </div>
    </header>`;

  $("loading").remove();
  main.insertAdjacentHTML("beforeend", head + bioSections(b) + programmeSection(c, p));
}

init();
