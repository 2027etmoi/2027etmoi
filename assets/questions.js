// « Mes priorités », mode Questions clés : l'utilisateur répond à 24 questions,
// puis compare ses réponses aux positions sourcées des candidats (data/questions.json).
// Tout se passe dans le navigateur : rien n'est enregistré ni envoyé.

const Q_REPONSES = { "2": "Oui", "1": "Plutôt oui", "-1": "Plutôt non", "-2": "Non", "0": "Sans avis" };
const Q_POSITIONS = { pour: 2, plutot_pour: 1, nuance: 0, plutot_contre: -1, contre: -2 };
const Q_LIBELLES = { pour: "Pour", plutot_pour: "Plutôt pour", nuance: "Nuancé", plutot_contre: "Plutôt contre", contre: "Contre" };
const Q_MIN = 5; // nombre minimal de questions comparables pour afficher un pourcentage

const qs = { data: null, cands: {}, rep: {}, imp: {} };
const qapp = () => $("qapp");

function qLimites() {
  return `<details class="notes method">
    <summary><h2>À lire : comment ce mode fonctionne</h2></summary>
    <ul>
      <li><strong>Ce n'est pas une recommandation de vote.</strong> Le résultat compare vos réponses aux positions connues des candidats ; il ne dit pas pour qui voter.</li>
      <li><strong>Chaque position est sourcée</strong> : propos du candidat ou programme de campagne. Sans source, la position est « non connue » et la question n'est pas comptée pour ce candidat — elle n'est jamais déduite de son parti.</li>
      <li><strong>La proximité</strong> est calculée question par question (écart entre votre réponse et la position du candidat), sur les seules questions où vous avez un avis et où sa position est connue. Les questions marquées « importante » comptent double.</li>
      <li><strong>En dessous de ${Q_MIN} questions comparables</strong>, aucun pourcentage n'est affiché : ce serait trop peu pour être parlant.</li>
      <li><strong>Les 24 questions</strong> ont été choisies pour couvrir les 12 thèmes de façon équilibrée ; leur liste et les règles sont publiques (<a href="https://github.com/PhilippeBout/2027etmoi/blob/main/docs/questions-cles.md" target="_blank" rel="noopener">méthode</a>).</li>
    </ul>
  </details>`;
}

function qRenderQuestions() {
  const qsList = qs.data.questions;
  const faites = Object.keys(qs.rep).length;
  let theme = "";
  qapp().innerHTML = `${qLimites()}
    <section class="section">
      <div class="progress" aria-label="Progression"><span style="width:${(faites / qsList.length) * 100}%"></span></div>
      <p class="notice">Répondez aux questions qui vous parlent ; vous pouvez en passer. Cochez « importante » pour les sujets qui comptent le plus pour vous.</p>
      ${qsList.map((q, i) => {
        const titre = q.theme !== theme ? `<h2 class="quiz-theme th-${q.theme}">${esc(THEMES[q.theme])}</h2>` : "";
        theme = q.theme;
        return `${titre}<div class="card quiz-item" data-q="${q.id}">
          <p><span class="quiz-letter">Question ${i + 1}</span>${esc(q.texte)}</p>${q.contexte ? `<p class="notice">${esc(q.contexte.texte)}${sourceHtml(q.contexte.source, " ")}</p>` : ""}
          <div class="quiz-answers">${Object.entries(Q_REPONSES).map(([k, l]) =>
            `<button type="button" class="chip" data-answer="${k}" aria-pressed="${qs.rep[q.id] === k}">${l}</button>`).join("")}
            <label class="imp-toggle"><input type="checkbox" data-imp ${qs.imp[q.id] ? "checked" : ""}> Importante</label></div>
        </div>`;
      }).join("")}
      <p class="quiz-nav"><span class="notice" id="qcount"></span><button type="button" class="cta" id="qgo">Voir les résultats</button></p>
    </section>`;
  const maj = () => {
    const n = Object.values(qs.rep).filter((v) => v !== "0").length;
    $("qcount").textContent = `${n} réponse${n > 1 ? "s" : ""} avec un avis`;
    qapp().querySelector(".progress span").style.width = `${(Object.keys(qs.rep).length / qsList.length) * 100}%`;
  };
  qapp().querySelectorAll(".quiz-item").forEach((card) => {
    const id = card.dataset.q;
    card.querySelectorAll("[data-answer]").forEach((b) => b.addEventListener("click", () => {
      qs.rep[id] = b.dataset.answer;
      card.querySelectorAll("[data-answer]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      maj();
    }));
    card.querySelector("[data-imp]").addEventListener("change", (e) => { qs.imp[id] = e.target.checked; });
  });
  maj();
  $("qgo").addEventListener("click", () => { qRenderResultats(); window.scrollTo({ top: $("qapp").offsetTop - 80 }); });
}

function qProximite(id) {
  const pos = qs.data.positions[id] || {};
  let somme = 0, poids = 0, n = 0;
  for (const q of qs.data.questions) {
    const u = qs.rep[q.id];
    const p = pos[q.id];
    if (u === undefined || u === "0" || !p || !(p.position in Q_POSITIONS)) continue;
    const w = qs.imp[q.id] ? 2 : 1;
    somme += (1 - Math.abs(+u - Q_POSITIONS[p.position]) / 4) * w;
    poids += w; n++;
  }
  return { pct: poids ? (somme / poids) * 100 : null, n, connues: Object.keys(pos).length };
}

function qRenderResultats() {
  const ids = Object.keys(qs.cands);
  const lignes = ids.map((id) => ({ id, ...qProximite(id) }))
    .sort((a, b) => ((b.n >= Q_MIN ? b.pct : -1) - (a.n >= Q_MIN ? a.pct : -1)) || b.n - a.n || a.id.localeCompare(b.id, "fr"));
  const avis = Object.values(qs.rep).filter((v) => v !== "0").length;

  qapp().innerHTML = `<section class="section">
      <h2>Vos résultats</h2>
      <p class="notice">Proximité entre vos ${avis} réponses et les positions sourcées de chaque candidat, sur les questions où les deux sont connues. 100 % = mêmes réponses partout ; 0 % = réponses opposées partout. <strong>Ce n'est pas une recommandation de vote</strong> ; vérifiez les positions et leurs sources ci-dessous.</p>
      <div class="table-wrap"><table class="poll-table">
        <thead><tr><th>Candidat</th><th class="num">Proximité</th><th class="num">Questions comparées</th><th class="bar-cell"><span class="visually-hidden">Graphique</span></th></tr></thead>
        <tbody>${lignes.map((l) => `<tr>
          <td><span class="bloc"><span class="dot ${esc(qs.cands[l.id].bloc)}"></span><a class="name" href="${candidatUrl(l.id)}">${esc(qs.cands[l.id].nom)}</a></span></td>
          <td class="num">${l.n >= Q_MIN ? `<strong>${Math.round(l.pct)} %</strong>` : `<span class="props-empty">Trop peu de positions connues</span>`}</td>
          <td class="num">${l.n} <span class="poll-n">(${l.connues} positions connues sur 24)</span></td>
          <td class="bar-cell">${l.n >= Q_MIN ? `<div class="bar" style="width:${l.pct}%"></div>` : ""}</td>
        </tr>`).join("")}</tbody>
      </table></div>
    </section>

    <section class="section">
      <h2>Question par question</h2>
      <div class="fold-tools"><button type="button" class="chip" data-toggle="open">Tout déplier</button><button type="button" class="chip" data-toggle="close">Tout replier</button></div>
      ${qs.data.questions.map((q, i) => {
        const positions = ids.map((id) => ({ id, p: qs.data.positions[id]?.[q.id] })).filter((x) => x.p);
        const groupe = (keys) => positions.filter((x) => keys.includes(x.p.position));
        const u = qs.rep[q.id];
        const bloc = (label, list) => list.length ? `<div class="qpos"><strong>${label}</strong><ul class="measures">${list.map((x) =>
          `<li><strong>${esc(qs.cands[x.id]?.nom || x.id)}</strong> <span class="answer-tag ${Q_POSITIONS[x.p.position] > 0 ? "oui" : Q_POSITIONS[x.p.position] < 0 ? "non" : "none"}">${esc(Q_LIBELLES[x.p.position])}</span> ${esc(x.p.resume)}${sourceHtml(x.p.source)}</li>`).join("")}</ul></div>` : "";
        return `<details class="card theme-block th-${q.theme}" id="q-${q.id}">
          <summary><h3>${i + 1}. ${esc(q.texte)}</h3><span class="fold-count">${positions.length}</span></summary>
          <p class="notice">Votre réponse : <strong>${u === undefined ? "pas de réponse" : Q_REPONSES[u]}</strong>${qs.imp[q.id] ? " · importante" : ""}</p>
          ${bloc("Pour", groupe(["pour", "plutot_pour"]))}${bloc("Nuancé", groupe(["nuance"]))}${bloc("Contre", groupe(["contre", "plutot_contre"]))}
          ${positions.length ? "" : `<p class="props-empty">Aucune position sourcée pour l'instant.</p>`}
          <p class="notice">Position non connue : ${ids.filter((id) => !qs.data.positions[id]?.[q.id]).length} candidat(s).</p>
        </details>`;
      }).join("")}
    </section>
    <p class="quiz-nav"><button type="button" class="chip" id="qback">Modifier mes réponses</button></p>
    ${qLimites()}`;
  qapp().querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", () =>
    qapp().querySelectorAll("details.theme-block").forEach((d) => { d.open = b.dataset.toggle === "open"; })));
  $("qback").addEventListener("click", () => { qRenderQuestions(); window.scrollTo({ top: $("qapp").offsetTop - 80 }); });
}

(async () => {
  const [d, cands] = await Promise.all([loadOptional("/data/questions.json"), loadCandidats()]);
  qs.data = d;
  qs.cands = Object.fromEntries((cands.candidats || []).filter((c) => EN_LICE.includes(c.statut)).map((c) => [c.id, c]));
  const nbPos = Object.values(d?.positions || {}).reduce((n, p) => n + Object.keys(p).length, 0);
  if (!d || !nbPos) {
    qapp().innerHTML = `<p class="notice">Les positions des candidats sur les questions clés sont en cours de recherche. En attendant, essayez le mode « Propositions des programmes ».</p>`;
    return;
  }
  qRenderQuestions();
})();

// Onglets entre les deux modes
document.querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("[data-mode]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  $("qapp").hidden = b.dataset.mode !== "questions";
  $("app").hidden = b.dataset.mode !== "propositions";
}));
