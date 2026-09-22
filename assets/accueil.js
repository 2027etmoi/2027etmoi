// Accueil : compte à rebours et prochaines étapes du calendrier (data/calendrier.json).

const PREMIER_TOUR = new Date("2027-04-18T08:00:00+02:00");
const STATUT_ETAPE = { officielle: "Date officielle", prevue: "Prévue", estimee: "Estimée" };

(async () => {
  const jours = Math.ceil((PREMIER_TOUR - new Date()) / 86400000);
  $("jours").textContent = jours > 0 ? jours : "0";

  const cal = await loadOptional("/data/calendrier.json");
  const aujourdhui = new Date().toISOString().slice(0, 10);
  const prochaines = (cal?.etapes || []).filter((e) => (e.fin || e.date) >= aujourdhui).slice(0, 4);
  $("steps").innerHTML = prochaines.map((e) => `<li class="step card">
      <span class="step-date">${esc(formatDate(e.date))}${e.fin && e.fin !== e.date ? ` – ${esc(formatDate(e.fin))}` : ""}</span>
      <span class="step-t">${esc(e.titre)}</span>
      <span class="badge ${e.statut === "officielle" ? "declare" : e.statut === "prevue" ? "primaire" : "pressenti"}">${esc(STATUT_ETAPE[e.statut] || e.statut)}</span>
      ${sourceHtml(e.source)}
    </li>`).join("");
})();
