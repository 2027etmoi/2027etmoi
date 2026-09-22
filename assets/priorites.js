// « Mes priorités » : importance des thèmes, propositions anonymes
// avec réponses nuancées, puis résultats détaillés et partageables.
// Tout se passe dans le navigateur : rien n'est enregistré ni envoyé.

const REPONSES = {
  "2": "Tout à fait d'accord",
  "1": "Plutôt d'accord",
  "-1": "Plutôt pas d'accord",
  "-2": "Pas du tout d'accord",
  "0": "Sans avis",
};
const IMPORTANCE = { 0: "Pas prioritaire", 1: "Important", 2: "Essentiel" };
const POIDS = { 1: 1, 2: 2 }; // poids d'un thème selon son importance
const DUREES = {
  rapide: { label: "Rapide", detail: "une proposition par candidat, thèmes essentiels seulement", essentiel: 1, important: 0 },
  approfondi: { label: "Approfondi", detail: "deux propositions par candidat sur les thèmes essentiels, une sur les thèmes importants", essentiel: 2, important: 1 },
};

let candidats = {};   // id -> candidat
let programmes = {};  // id -> fiche programme (avec au moins une mesure)
const st = { importance: {}, duree: "rapide", tirage: [], reponses: {}, etape: 0 };

// --- utilitaires

function melange(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const mesure = (ref) => { const [id, i] = ref.split(":"); return { id, m: programmes[id]?.mesures?.[+i] }; };
const themesChoisis = () => Object.keys(THEMES).filter((t) => st.importance[t] > 0)
  .sort((a, b) => st.importance[b] - st.importance[a]);

// Tirage équilibré : n mesures au plus par candidat et par thème, documents officiels d'abord.
function tirer() {
  const d = DUREES[st.duree];
  const out = [];
  for (const t of themesChoisis()) {
    const n = st.importance[t] === 2 ? d.essentiel : d.important;
    if (!n) continue;
    const pool = [];
    for (const [id, p] of Object.entries(programmes)) {
      const refs = (p.mesures || []).map((m, i) => ({ m, ref: `${id}:${i}` })).filter((x) => x.m.theme === t);
      const officiel = melange(refs.filter((x) => x.m.nature === "programme"));
      const autres = melange(refs.filter((x) => x.m.nature !== "programme"));
      [...officiel, ...autres].slice(0, n).forEach((x) => pool.push(x.ref));
    }
    out.push({ theme: t, refs: melange(pool) });
  }
  return out.filter((b) => b.refs.length);
}

// Partage : l'état tient dans l'adresse (#…), aucun serveur.
function encoder() {
  const imp = Object.keys(THEMES).map((t) => st.importance[t] || 0).join("");
  const blocs = st.tirage.map((b) => `${b.theme}~${b.refs.map((r) => `${r}~${st.reponses[r] ?? ""}`).join("~")}`).join("|");
  return `#r=${encodeURIComponent(`${imp}|${blocs}`)}`;
}

function decoder(hash) {
  const m = /#r=(.+)/.exec(hash);
  if (!m) return false;
  const [imp, ...blocs] = decodeURIComponent(m[1]).split("|");
  Object.keys(THEMES).forEach((t, i) => { st.importance[t] = +imp[i] || 0; });
  st.tirage = []; st.reponses = {};
  for (const b of blocs) {
    const [theme, ...rest] = b.split("~");
    const refs = [];
    for (let i = 0; i < rest.length; i += 2) {
      if (!mesure(rest[i]).m) continue; // fiche modifiée depuis le partage
      refs.push(rest[i]);
      if (rest[i + 1] !== "") st.reponses[rest[i]] = rest[i + 1];
    }
    if (THEMES[theme] && refs.length) st.tirage.push({ theme, refs });
  }
  return st.tirage.length > 0;
}

const app = () => $("app");
const haut = () => window.scrollTo({ top: 0 });

function limitesHtml(open = false) {
  return `<details class="notes method"${open ? " open" : ""}>
    <summary><h2>À lire : ce que cet outil fait, et ne fait pas</h2></summary>
    <ul>
      <li><strong>Ce n'est pas une recommandation de vote.</strong> Les résultats comptent vos réponses ; ils ne disent pas pour qui voter.</li>
      <li><strong>Les propositions sont anonymes et mélangées</strong>, pour juger le fond plutôt que l'étiquette. Les auteurs apparaissent à la fin.</li>
      <li><strong>Le même nombre de propositions par candidat</strong> et par thème, tirées au hasard parmi les mesures vérifiées du site, en privilégiant les documents officiels. Deux essais présentent donc des mesures différentes.</li>
      <li><strong>Tous les programmes ne sont pas aussi détaillés.</strong> Un candidat sans mesure sourcée sur un thème n'y apparaît pas : cela ne veut pas dire qu'il n'a pas d'avis.</li>
      <li><strong>Rien n'est enregistré ni envoyé.</strong> Le lien de partage contient vos réponses dans l'adresse elle-même.</li>
    </ul>
  </details>`;
}

// --- étape 1 : importance des thèmes et durée

function renderPreparation() {
  const nb = Object.fromEntries(Object.keys(THEMES).map((t) => [t, new Set()]));
  for (const [id, p] of Object.entries(programmes)) for (const m of p.mesures || []) nb[m.theme]?.add(id);
  const choisis = themesChoisis();

  app().innerHTML = `${limitesHtml()}
    <section class="section card quiz">
      <h2>1. Quelle importance donnez-vous à chaque thème ?</h2>
      <p class="notice">Les thèmes « essentiels » comptent double dans les résultats.</p>
      <div class="imp-list">${Object.entries(THEMES).map(([t, label]) => `<div class="imp-row th-${t}">
          <span class="imp-label">${esc(label)}<span class="poll-n">${nb[t].size} candidats avec des propositions sourcées</span></span>
          <span class="imp-choices">${Object.entries(IMPORTANCE).map(([v, l]) =>
            `<button type="button" class="chip" data-theme="${t}" data-imp="${v}" aria-pressed="${(st.importance[t] || 0) === +v}">${l}</button>`).join("")}</span>
        </div>`).join("")}</div>
    </section>

    <section class="section card quiz">
      <h2>2. Durée</h2>
      <div class="chips">${Object.entries(DUREES).map(([k, d]) =>
        `<button type="button" class="chip" data-duree="${k}" aria-pressed="${st.duree === k}"><strong>${d.label}</strong>&nbsp;: ${esc(d.detail)}</button>`).join("")}</div>
      <p class="quiz-nav"><span class="notice">${choisis.length ? `${choisis.length} thème${choisis.length > 1 ? "s" : ""} retenu${choisis.length > 1 ? "s" : ""}.` : "Choisissez au moins un thème « important » ou « essentiel »."}</span>
        <button type="button" class="cta" id="go" ${tirer().length ? "" : "disabled"}>Commencer</button></p>
    </section>`;

  app().querySelectorAll("[data-imp]").forEach((b) => b.addEventListener("click", () => {
    st.importance[b.dataset.theme] = +b.dataset.imp;
    renderPreparation();
  }));
  app().querySelectorAll("[data-duree]").forEach((b) => b.addEventListener("click", () => { st.duree = b.dataset.duree; renderPreparation(); }));
  $("go").addEventListener("click", () => {
    st.tirage = tirer(); st.reponses = {}; st.etape = 0;
    renderQuestions(); haut();
  });
}

// --- étape 2 : propositions anonymes

function renderQuestions() {
  const bloc = st.tirage[st.etape];
  const total = st.tirage.reduce((n, b) => n + b.refs.length, 0);
  const faites = Object.keys(st.reponses).length;
  app().innerHTML = `<section class="section">
      <div class="progress" aria-label="Progression"><span style="width:${(faites / total) * 100}%"></span></div>
      <p class="kicker">Thème ${st.etape + 1} sur ${st.tirage.length} · ${esc(IMPORTANCE[st.importance[bloc.theme]])}</p>
      <h2 class="th-${bloc.theme} quiz-theme">${esc(THEMES[bloc.theme])}</h2>
      <p class="notice">Donnez votre avis sur chaque proposition. Les auteurs seront révélés à la fin.</p>
      ${bloc.refs.map((ref, i) => `<div class="card quiz-item" data-ref="${ref}">
          <p><span class="quiz-letter">Proposition ${i + 1}</span>${esc(mesure(ref).m.texte)}</p>
          <div class="quiz-answers">${Object.entries(REPONSES).map(([k, label]) =>
            `<button type="button" class="chip" data-answer="${k}" aria-pressed="${st.reponses[ref] === k}">${label}</button>`).join("")}</div>
        </div>`).join("")}
      <p class="quiz-nav">
        <button type="button" class="chip" id="prev">${st.etape === 0 ? "Modifier mes choix" : "Thème précédent"}</button>
        <button type="button" class="cta" id="next">${st.etape === st.tirage.length - 1 ? "Voir les résultats" : "Thème suivant"}</button>
      </p>
    </section>`;
  app().querySelectorAll(".quiz-item").forEach((card) => card.querySelectorAll("[data-answer]").forEach((b) =>
    b.addEventListener("click", () => {
      st.reponses[card.dataset.ref] = b.dataset.answer;
      card.querySelectorAll("[data-answer]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      const n = Object.keys(st.reponses).length;
      app().querySelector(".progress span").style.width = `${(n / total) * 100}%`;
    })));
  $("prev").addEventListener("click", () => { if (st.etape === 0) renderPreparation(); else { st.etape--; renderQuestions(); } haut(); });
  $("next").addEventListener("click", () => {
    if (st.etape < st.tirage.length - 1) { st.etape++; renderQuestions(); } else { history.replaceState(null, "", encoder()); renderResultats(); }
    haut();
  });
}

// --- étape 3 : résultats

// Accord d'un ensemble de réponses : moyenne des réponses (-2 à +2) ramenée de 0 à 100 %.
// Les « sans avis » et les propositions sans réponse ne comptent pas.
function accord(refs) {
  const v = refs.map((r) => st.reponses[r]).filter((x) => x !== undefined && x !== "0").map(Number);
  return v.length ? { pct: ((v.reduce((a, b) => a + b, 0) / v.length + 2) / 4) * 100, n: v.length } : null;
}

function renderResultats() {
  const ids = [...new Set(st.tirage.flatMap((b) => b.refs.map((r) => mesure(r).id)))];
  const ligne = (id) => {
    let somme = 0, poids = 0;
    const parTheme = {};
    for (const b of st.tirage) {
      const a = accord(b.refs.filter((r) => mesure(r).id === id));
      parTheme[b.theme] = a;
      if (a) { const w = POIDS[st.importance[b.theme]] || 1; somme += a.pct * w; poids += w; }
    }
    return { id, global: poids ? somme / poids : null, parTheme };
  };
  const lignes = ids.map(ligne).sort((a, b) => (b.global ?? -1) - (a.global ?? -1) || a.id.localeCompare(b.id, "fr"));
  const cell = (a) => a ? `<span class="acc" style="--p:${a.pct}%">${Math.round(a.pct)} %</span>` : `<span class="props-empty">—</span>`;

  app().innerHTML = `<section class="section">
      <h2>Vos résultats</h2>
      <p class="notice">Pour chaque candidat : votre degré d'accord moyen avec ses propositions qui vous ont été présentées (0 % = « pas du tout d'accord » partout, 100 % = « tout à fait d'accord » partout), les thèmes essentiels comptant double. Les « sans avis » ne comptent pas. C'est un reflet de <strong>vos réponses sur un échantillon de mesures</strong>, <strong>pas une recommandation de vote</strong>.</p>
      <div class="table-wrap scroll-x"><table class="poll-table results">
        <thead><tr><th>Candidat</th><th class="num">Accord global</th>${st.tirage.map((b) => `<th class="num th-${b.theme}"><span class="th-pill">${esc(THEMES[b.theme].split(",")[0])}</span></th>`).join("")}</tr></thead>
        <tbody>${lignes.map((l) => `<tr>
          <td><span class="bloc"><span class="dot ${esc(candidats[l.id].bloc)}"></span><a class="name" href="${candidatUrl(l.id)}">${esc(candidats[l.id].nom)}</a></span></td>
          <td class="num">${l.global === null ? '<span class="props-empty">Sans avis</span>' : `<strong>${Math.round(l.global)} %</strong>`}</td>
          ${st.tirage.map((b) => `<td class="num">${cell(l.parTheme[b.theme])}</td>`).join("")}
        </tr>`).join("")}</tbody>
      </table></div>
      <p class="notice">Un tiret signifie qu'aucune proposition de ce candidat ne vous a été présentée sur ce thème, ou que vous avez répondu « sans avis ».</p>
    </section>

    <section class="section">
      <h2>Qui propose quoi</h2>
      <div class="fold-tools"><button type="button" class="chip" data-toggle="open">Tout déplier</button><button type="button" class="chip" data-toggle="close">Tout replier</button></div>
      ${st.tirage.map((b) => `<details class="card theme-block" id="t-${b.theme}">
          <summary><h3>${esc(THEMES[b.theme])}</h3><span class="fold-count">${b.refs.length}</span></summary>
          <ul class="measures">${b.refs.map((ref) => {
            const { id, m } = mesure(ref);
            const r = st.reponses[ref];
            const cls = r === undefined ? "none" : +r > 0 ? "oui" : +r < 0 ? "non" : "none";
            return `<li><span class="answer-tag ${cls}">${r === undefined ? "Pas de réponse" : REPONSES[r]}</span>
              <strong>${esc(candidats[id].nom)}</strong> — ${esc(m.texte)}
              <span class="tag ${esc(m.nature)}">${esc(NATURES[m.nature] || m.nature)}</span>${sourceHtml(m.source)}</li>`;
          }).join("")}</ul>
        </details>`).join("")}
    </section>

    <section class="section card">
      <h2>Partager ou reprendre</h2>
      <p class="notice">Ce lien contient vos réponses dans l'adresse elle-même : rien n'est stocké sur un serveur.</p>
      <p class="share"><input type="text" id="share" readonly value="${esc(location.href.split("#")[0] + encoder())}"><button type="button" class="chip" id="copy">Copier le lien</button></p>
      <p class="quiz-nav">
        <button type="button" class="chip" id="again">Recommencer avec d'autres propositions</button>
        <a class="cta" href="comparateur.html?c=${encodeURIComponent(lignes.slice(0, 4).map((l) => l.id).join(","))}&t=${encodeURIComponent(st.tirage.map((b) => b.theme).join(","))}">Comparer ces candidats en détail</a>
      </p>
    </section>
    ${limitesHtml()}`;

  app().querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", () =>
    app().querySelectorAll("details.theme-block").forEach((d) => { d.open = b.dataset.toggle === "open"; })));
  $("copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("share").value); $("copy").textContent = "Lien copié"; }
    catch { $("share").select(); }
  });
  $("again").addEventListener("click", () => { history.replaceState(null, "", location.pathname); st.etape = 0; renderPreparation(); haut(); });
}

async function init() {
  const data = await loadCandidats();
  const actifs = (data.candidats || []).filter((c) => EN_LICE.includes(c.statut));
  candidats = Object.fromEntries(actifs.map((c) => [c.id, c]));
  const fiches = await Promise.all(actifs.map((c) => loadProgramme(c.id)));
  actifs.forEach((c, i) => { if (fiches[i]?.mesures?.length) programmes[c.id] = fiches[i]; });
  if (decoder(location.hash)) renderResultats(); else renderPreparation();
}

init();
