// « Mes priorités », parcours rapide : importance des thèmes + une question de fond par thème,
// puis proximité pondérée et mesures des programmes sur les thèmes prioritaires.
// Tout se passe dans le navigateur : rien n'est enregistré ni envoyé.

const R_IMP = { 0: "Secondaire", 1: "Important", 2: "Essentiel" };
const R_POIDS = { 0: 0.5, 1: 1, 2: 2 };
const R_REP = { "2": "Oui", "1": "Plutôt oui", "-1": "Plutôt non", "-2": "Non", "0": "Sans avis" };
const R_POS = { pour: 2, plutot_pour: 1, nuance: 0, plutot_contre: -1, contre: -2 };
const R_MIN = 4;     // questions comparables minimales pour afficher un pourcentage
const R_TOP = 6;     // candidats montrés dans « ce que prévoient les programmes »

const rs = { q: null, cands: {}, progs: {}, parTheme: {}, imp: {}, rep: {} };
const rapp = () => $("rapp");

// Question retenue pour chaque thème : celle qui départage le mieux les candidats
// (le plus de positions à la fois « pour » et « contre », puis le plus de positions connues).
function choisirQuestions() {
  const stats = (qid) => {
    let pour = 0, contre = 0, n = 0;
    for (const pos of Object.values(rs.q.positions)) {
      const p = pos[qid]?.position;
      if (!p) continue;
      n++;
      if (R_POS[p] > 0) pour++;
      if (R_POS[p] < 0) contre++;
    }
    return { clivage: Math.min(pour, contre), n };
  };
  for (const t of Object.keys(THEMES)) {
    const qs = rs.q.questions.filter((q) => q.theme === t).map((q) => ({ q, ...stats(q.id) }));
    qs.sort((a, b) => b.clivage - a.clivage || b.n - a.n);
    if (qs[0]) rs.parTheme[t] = qs[0].q;
  }
}

function rLimites() {
  return `<details class="notes method">
    <summary><h2>À lire : comment fonctionne le parcours rapide</h2></summary>
    <ul>
      <li><strong>Ce n'est pas une recommandation de vote.</strong> Le résultat compare vos réponses aux positions connues des candidats.</li>
      <li><strong>Une question par thème</strong>, choisie automatiquement : celle qui départage le mieux les candidats (le plus de positions sourcées à la fois « pour » et « contre »). Toutes les questions, dont celles de société, sont dans le parcours approfondi.</li>
      <li><strong>L'importance</strong> que vous donnez à un thème pondère sa question : essentiel ×2, important ×1, secondaire ×0,5.</li>
      <li><strong>Chaque position est sourcée</strong> ; sans source, elle est « non connue » et ne compte pas — jamais déduite du parti. En dessous de ${R_MIN} questions comparables, pas de pourcentage.</li>
      <li><strong>Rien n'est enregistré ni envoyé.</strong></li>
    </ul>
  </details>`;
}

function rRenderQuestions() {
  rapp().innerHTML = `${rLimites()}
    <section class="section">
      <p class="notice">Pour chaque grand thème : dites s'il compte pour vous, puis répondez à la question (vous pouvez la passer).</p>
      ${Object.entries(THEMES).map(([t, label]) => {
        const q = rs.parTheme[t];
        return `<div class="card rq th-${t}" data-theme="${t}">
          <div class="rq-head"><h3 class="quiz-theme">${esc(label)}</h3>
            <span class="imp-choices">${Object.entries(R_IMP).map(([v, l]) =>
              `<button type="button" class="chip" data-imp="${v}" aria-pressed="${(rs.imp[t] ?? 1) === +v}">${l}</button>`).join("")}</span></div>
          ${q ? `<p>${esc(q.texte)}</p>${q.contexte ? `<p class="notice">${esc(q.contexte.texte)}</p>` : ""}
          <div class="quiz-answers">${Object.entries(R_REP).map(([k, l]) =>
            `<button type="button" class="chip" data-answer="${k}" aria-pressed="${rs.rep[q.id] === k}">${l}</button>`).join("")}</div>` : ""}
        </div>`;
      }).join("")}
      <p class="quiz-nav"><span class="notice" id="rcount"></span><button type="button" class="cta" id="rgo">Voir les résultats</button></p>
    </section>`;
  const maj = () => {
    const n = Object.values(rs.rep).filter((v) => v !== "0").length;
    $("rcount").textContent = `${n} réponse${n > 1 ? "s" : ""} sur ${Object.keys(rs.parTheme).length}`;
  };
  rapp().querySelectorAll(".rq").forEach((card) => {
    const t = card.dataset.theme;
    const q = rs.parTheme[t];
    card.querySelectorAll("[data-imp]").forEach((b) => b.addEventListener("click", () => {
      rs.imp[t] = +b.dataset.imp;
      card.querySelectorAll("[data-imp]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    }));
    card.querySelectorAll("[data-answer]").forEach((b) => b.addEventListener("click", () => {
      rs.rep[q.id] = b.dataset.answer;
      card.querySelectorAll("[data-answer]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      maj();
    }));
  });
  maj();
  $("rgo").addEventListener("click", () => { rRenderResultats(); window.scrollTo({ top: $("rapp").offsetTop - 80 }); });
}

function rProximite(id) {
  const pos = rs.q.positions[id] || {};
  let somme = 0, poids = 0, n = 0;
  for (const [t, q] of Object.entries(rs.parTheme)) {
    const u = rs.rep[q.id];
    const p = pos[q.id]?.position;
    if (u === undefined || u === "0" || !(p in R_POS)) continue;
    const w = R_POIDS[rs.imp[t] ?? 1];
    somme += (1 - Math.abs(+u - R_POS[p]) / 4) * w;
    poids += w; n++;
  }
  return { pct: poids ? (somme / poids) * 100 : null, n };
}

function rRenderResultats() {
  const ids = Object.keys(rs.cands);
  const lignes = ids.map((id) => ({ id, ...rProximite(id) }))
    .sort((a, b) => ((b.n >= R_MIN ? b.pct : -1) - (a.n >= R_MIN ? a.pct : -1)) || b.n - a.n || a.id.localeCompare(b.id, "fr"));
  const proches = lignes.filter((l) => l.n >= R_MIN).slice(0, R_TOP).map((l) => l.id);
  const themes = Object.keys(THEMES).filter((t) => (rs.imp[t] ?? 1) >= 1).sort((a, b) => (rs.imp[b] ?? 1) - (rs.imp[a] ?? 1));

  const mesures = (id, t) => {
    const ms = (rs.progs[id]?.mesures || []).filter((m) => m.theme === t);
    return [...ms.filter((m) => m.nature === "programme"), ...ms.filter((m) => m.nature !== "programme")].slice(0, 2);
  };

  rapp().innerHTML = `<section class="section">
      <h2>Vos résultats</h2>
      <p class="notice">Proximité entre vos réponses et les positions sourcées des candidats, pondérée par l'importance de chaque thème. <strong>Ce n'est pas une recommandation de vote.</strong></p>
      <div class="table-wrap"><table class="poll-table">
        <thead><tr><th>Candidat</th><th class="num">Proximité</th><th class="num">Questions comparées</th><th class="bar-cell"><span class="visually-hidden">Graphique</span></th></tr></thead>
        <tbody>${lignes.map((l) => `<tr>
          <td><span class="bloc"><span class="dot ${esc(rs.cands[l.id].bloc)}"></span><a class="name" href="${candidatUrl(l.id)}">${esc(rs.cands[l.id].nom)}</a></span></td>
          <td class="num">${l.n >= R_MIN ? `<strong>${Math.round(l.pct)} %</strong>` : `<span class="props-empty">Trop peu de positions connues</span>`}</td>
          <td class="num">${l.n}</td>
          <td class="bar-cell">${l.n >= R_MIN ? `<div class="bar" style="width:${l.pct}%"></div>` : ""}</td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>

    <section class="section">
      <h2>Ce que prévoient les programmes sur vos thèmes prioritaires</h2>
      <p class="notice">Pour les ${proches.length} candidats les plus proches de vos réponses : jusqu'à deux mesures sourcées par thème, issues en priorité de leur programme officiel. Le comparateur permet de voir tous les candidats.</p>
      ${themes.length ? themes.map((t) => `<details class="card theme-block th-${t}"${(rs.imp[t] ?? 1) === 2 ? " open" : ""}>
          <summary><h3>${esc(THEMES[t])}</h3><span class="fold-count">${esc(R_IMP[rs.imp[t] ?? 1])}</span></summary>
          ${proches.map((id) => {
            const ms = mesures(id, t);
            return `<div class="qpos"><strong><span class="dot ${esc(rs.cands[id].bloc)}"></span> <a href="${candidatUrl(id)}">${esc(rs.cands[id].nom)}</a></strong>
              ${ms.length ? `<ul class="measures">${ms.map((m) => `<li>${esc(m.texte)} <span class="tag ${esc(m.nature)}">${esc(NATURES[m.nature] || m.nature)}</span>${sourceHtml(m.source)}</li>`).join("")}</ul>`
                : `<p class="props-empty">Pas de mesure sourcée sur ce thème pour l'instant.</p>`}</div>`;
          }).join("")}
          <p><a href="/comparateur.html?c=${encodeURIComponent(proches.slice(0, 4).join(","))}&t=${t}">Comparer en détail sur ce thème →</a></p>
        </details>`).join("") : `<p class="notice">Vous n'avez marqué aucun thème comme important.</p>`}
    </section>

    <p class="quiz-nav">
      <button type="button" class="chip" id="rback">Modifier mes réponses</button>
      <button type="button" class="cta" id="rplus">Aller plus loin : parcours approfondi</button>
    </p>
    ${rLimites()}`;
  $("rback").addEventListener("click", () => { rRenderQuestions(); window.scrollTo({ top: $("rapp").offsetTop - 80 }); });
  $("rplus").addEventListener("click", () => {
    // Reporte les réponses et l'importance dans le parcours approfondi
    if (typeof qs !== "undefined") {
      Object.assign(qs.rep, rs.rep);
      for (const [t, q] of Object.entries(rs.parTheme)) if ((rs.imp[t] ?? 1) === 2) qs.imp[q.id] = true;
      if (qs.data) qRenderQuestions();
    }
    document.querySelector('[data-mode="approfondi"]').click();
    window.scrollTo({ top: 0 });
  });
}

(async () => {
  const [q, cands] = await Promise.all([loadOptional("/data/questions.json"), loadCandidats()]);
  if (!q || !Object.keys(q.positions || {}).length) {
    rapp().innerHTML = `<p class="notice">Les positions des candidats sont en cours de recherche.</p>`;
    return;
  }
  rs.q = q;
  const actifs = (cands.candidats || []).filter((c) => EN_LICE.includes(c.statut));
  rs.cands = Object.fromEntries(actifs.map((c) => [c.id, c]));
  const fiches = await Promise.all(actifs.map((c) => loadProgramme(c.id)));
  actifs.forEach((c, i) => { if (fiches[i]) rs.progs[c.id] = fiches[i]; });
  choisirQuestions();
  rRenderQuestions();
})();
