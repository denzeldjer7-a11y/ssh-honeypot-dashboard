"use strict";

const nf = new Intl.NumberFormat("fr-FR");
const $ = (id) => document.getElementById(id);

// Mots de passe, identifiants et commandes viennent des attaquants : on n'utilise
// jamais innerHTML, uniquement textContent, sinon un bot pourrait injecter du HTML.
function el(tag, text, attrs) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  return node;
}

function rankTable(id, rows) {
  const body = $(id).querySelector("tbody");
  const max = Math.max(1, ...rows.map((r) => r.count));
  for (const r of rows) {
    const bar = el("span", "", { class: "bar" });
    bar.style.width = `${(r.count / max) * 100}%`;
    const cell = el("div", undefined, { class: "cell" });
    cell.append(el("span", undefined, { class: "track", "aria-hidden": "true" }), el("span", nf.format(r.count), { class: "num" }));
    cell.firstChild.append(bar);
    const td = el("td");
    td.append(cell);
    const tr = el("tr");
    tr.append(el("th", r.label || "(vide)", { scope: "row" }), td);
    body.append(tr);
  }
}

function pointsTable(points) {
  const body = $("t-points").querySelector("tbody");
  for (const p of points.slice(0, 30)) {
    const tr = el("tr");
    tr.append(el("td", p.country), el("td", p.ip), el("td", nf.format(p.hits)));
    body.append(tr);
  }
}

function drawMap(points) {
  if (!window.L) {
    $("map").textContent = "Carte indisponible : la bibliothèque Leaflet n'a pas pu se charger.";
    return;
  }
  const map = L.map("map", { worldCopyJump: true }).setView([25, 10], 2);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 6,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  const max = Math.max(1, ...points.map((p) => p.hits));
  for (const p of points) {
    const tip = el("div", `${p.country}, ${p.ip}, ${nf.format(p.hits)} sessions`);
    L.circleMarker([p.lat, p.lon], {
      radius: 4 + 14 * Math.sqrt(p.hits / max),
      color: "#0a5555",
      weight: 1,
      fillColor: "#0a5555",
      fillOpacity: 0.45,
    }).bindTooltip(tip).addTo(map);
  }
}

function drawTimeline(rows) {
  const svg = $("timeline");
  const NS = "http://www.w3.org/2000/svg";
  const W = 700, H = 180, PAD = 24;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  if (!rows.length) return;
  const max = Math.max(...rows.map((r) => r.count));
  const slot = (W - 2 * PAD) / rows.length;
  rows.forEach((r, i) => {
    const h = (r.count / max) * (H - 2 * PAD);
    const rect = document.createElementNS(NS, "rect");
    rect.setAttribute("x", PAD + i * slot + 2);
    rect.setAttribute("y", H - PAD - h);
    rect.setAttribute("width", Math.max(1, slot - 4));
    rect.setAttribute("height", h);
    rect.setAttribute("fill", "#0a5555");
    const title = document.createElementNS(NS, "title");
    title.textContent = `${r.day} : ${nf.format(r.count)} sessions`;
    rect.append(title);
    svg.append(rect);
  });
  for (const [x, anchor, text] of [[PAD, "start", rows[0].day], [W - PAD, "end", rows[rows.length - 1].day]]) {
    const label = document.createElementNS(NS, "text");
    label.setAttribute("x", x);
    label.setAttribute("y", H - 6);
    label.setAttribute("text-anchor", anchor);
    label.setAttribute("font-size", "12");
    label.setAttribute("fill", "#55524b");
    label.textContent = text;
    svg.append(label);
  }
  svg.setAttribute("aria-label", `Sessions par jour du ${rows[0].day} au ${rows[rows.length - 1].day}. Maximum : ${nf.format(max)} sessions en une journée.`);
}

function render(s) {
  $("demo-banner").hidden = !s.demo;
  $("n-sessions").textContent = nf.format(s.totals.sessions);
  $("n-ips").textContent = nf.format(s.totals.unique_ips);
  $("n-attempts").textContent = nf.format(s.totals.login_attempts);
  $("n-successes").textContent = nf.format(s.totals.login_successes);
  $("generated").textContent = new Date(s.generated_at).toLocaleString("fr-FR");
  $("generated").setAttribute("datetime", s.generated_at);

  drawMap(s.points);
  pointsTable(s.points);
  drawTimeline(s.timeline);
  rankTable("t-days", s.timeline.map((r) => ({ label: r.day, count: r.count })));
  rankTable("t-passwords", s.top_passwords);
  rankTable("t-usernames", s.top_usernames);
  rankTable("t-commands", s.top_commands);
  rankTable("t-countries", s.top_countries);
}

fetch("stats.json")
  .then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then(render)
  .catch((err) => {
    const box = $("error");
    box.textContent = `Impossible de charger stats.json (${err.message}). En local, lance : python3 -m http.server -d dashboard`;
    box.hidden = false;
  });
