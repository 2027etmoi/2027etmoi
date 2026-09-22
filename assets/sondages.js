// Page sondages : moyenne calculée à partir de data/sondages.json, puis détail.

async function init() {
  const [cands, data] = await Promise.all([loadCandidats().catch(() => ({ candidats: [] })), loadSondages()]);
  const byId = Object.fromEntries((cands.candidats || []).map((c) => [c.id, c]));
  const nom = (id) => byId[id]?.nom || data?.noms_hors_liste?.[id] || id;
  const person = (id) => byId[id]
    ? `<span class="bloc"><span class="dot ${esc(byId[id].bloc)}"></span><a class="name" href="${candidatUrl(id)}">${esc(nom(id))}</a></span>`
    : esc(nom(id));

  if (!data?.sondages?.length) {
    $("avg-empty").hidden = false;
    return;
  }

  const f = data.fenetre;
  if (f) $("lede").textContent = `Moyenne des ${data.sondages.length} sondages dont le terrain s'est achevé entre le ${formatDate(f.debut)} et le ${formatDate(f.fin)}, puis détail de chaque enquête avec sa source.`;

  const moy = computeMoyennes(data);
  const rows = Object.entries(moy).sort((a, b) => b[1].moyenne - a[1].moyenne);
  const top = rows[0]?.[1].moyenne || 1;
  $("avg").innerHTML = rows.map(([id, m]) => `<tr id="${esc(id)}">
      <td>${person(id)}</td>
      <td class="num"><strong>${formatPct(m.moyenne)}</strong></td>
      <td class="num">${m.n > 1 ? `${formatPct(m.min)} – ${formatPct(m.max)}` : "—"}</td>
      <td class="num">${m.n}</td>
      <td class="bar-cell"><div class="bar" style="width:${(m.moyenne / top) * 100}%"></div></td>
    </tr>`).join("");

  $("polls").innerHTML = data.sondages.map((s) => `<div class="card poll-card">
      <h3>${esc(s.institut)}${s.commanditaire ? ` pour ${esc(s.commanditaire)}` : ""}</h3>
      <div class="notice">Terrain du ${esc(formatDate(s.terrain_debut))} au ${esc(formatDate(s.terrain_fin))}${s.echantillon ? ` · ${Number(s.echantillon).toLocaleString("fr-FR")} personnes interrogées` : ""}</div>
      ${sourceHtml(s.source)}
      ${s.source_primaire_verifiee === false ? `<div class="warn">Chiffres relevés sur une source secondaire : publication de l'institut non consultée.</div>` : ""}
      ${(s.hypotheses || []).map((h) => `<div class="hyp"><strong>${esc(h.label || "Hypothèse")}</strong>
        ${Object.entries(h.scores || {}).sort((a, b) => b[1] - a[1]).map(([id, v]) => `${esc(nom(id))} ${formatPct(v)}`).join(" · ")}
      </div>`).join("")}
    </div>`).join("");

  // L'ancre (#id) n'existait pas au chargement : on y retourne une fois le tableau rendu
  if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
}

init();
