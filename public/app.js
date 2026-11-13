"use strict";

// Mully Rating website: asks /api/rating and draws the result.

const MATCH_OPTIONS = ["10", "30", "50", "100"];
const DEFAULT_MATCHES = "30";

// Same thresholds as mully_rating/rating/tiers.py.
const TIERS = [["S", 90], ["A", 75], ["B", 60], ["C", 45], ["D", 0]];

const PARTS = [
  ["combat", "Combat", "ADR, K/D, K/R, MVPs"],
  ["multi", "Multikills", "Rounds with 2+ kills"],
  ["entry", "Entry", "Opening duels won"],
  ["clutch", "Clutch", "Compared with average"],
];

const STATS = [
  ["adr", "ADR", (v) => v.toFixed(1)],
  ["kd", "K/D", (v) => v.toFixed(2)],
  ["kr", "Kills per round", (v) => v.toFixed(2)],
  ["mvp", "MVPs per match", (v) => v.toFixed(1)],
  ["entry", "Opening duels won", (v) => `${Math.round(v * 100)}%`],
  ["clutch", "Clutches vs. average", (v) => `×${v.toFixed(2)}`],
  ["multi", "Multikill points / round", (v) => v.toFixed(2)],
];

const $ = (id) => document.getElementById(id);

const form = $("search");
const input = $("player");
const submitButton = $("submit");
const statusBox = $("status");
const result = $("result");

let currentRequest = 0;
let elapsedTimer = null;

// ---------- small helpers ----------

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}

function svg(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function tierOf(score) {
  for (const [tier, lowest] of TIERS) {
    if (score >= lowest) return tier;
  }
  return "D";
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

// A bar from 0 to 100 with a mark at 50 (average player).
function meter(value) {
  const fill = el("div", { class: "meter-fill" });
  const bar = el("div", { class: `meter tier-${tierOf(value)}` }, fill, el("span", { class: "meter-average" }));
  // Two frames so the bar grows from 0 instead of appearing at once.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    fill.style.width = `${clamp(value)}%`;
  }));
  return bar;
}

// ---------- URL: ?player=nick&matches=30 ----------

function readUrl() {
  const params = new URLSearchParams(location.search);
  const matches = params.get("matches");
  return {
    player: (params.get("player") || "").trim(),
    matches: MATCH_OPTIONS.includes(matches) ? matches : DEFAULT_MATCHES,
  };
}

function writeUrl(player, matches) {
  const query = new URLSearchParams({ player, matches }).toString();
  if (location.search === `?${query}`) return;
  history.pushState(null, "", `${location.pathname}?${query}`);
}

function fillForm({ player, matches }) {
  input.value = player;
  form.elements.matches.value = matches;
}

// ---------- status line ----------

function showLoading(matches) {
  const elapsed = el("span", { class: "muted small" });
  statusBox.className = "status";
  statusBox.replaceChildren(
    el("span", { class: "spinner", "aria-hidden": "true" }),
    el("span", { text: `Analyzing the last ${matches} matches… ` }),
    elapsed,
  );

  const started = Date.now();
  clearInterval(elapsedTimer);
  elapsedTimer = setInterval(() => {
    elapsed.textContent = `${Math.round((Date.now() - started) / 1000)}s`;
  }, 1000);
}

function showError(message) {
  clearInterval(elapsedTimer);
  statusBox.className = "status error";
  statusBox.replaceChildren(el("span", { text: message }));
}

function clearStatus() {
  clearInterval(elapsedTimer);
  statusBox.className = "status";
  statusBox.replaceChildren();
}

// ---------- request ----------

async function analyze(player, matches) {
  const request = ++currentRequest;

  submitButton.disabled = true;
  result.hidden = true;
  showLoading(matches);

  try {
    const response = await fetch(`/api/rating?${new URLSearchParams({ player, matches })}`);
    const data = await response.json().catch(() => ({}));

    if (request !== currentRequest) return; // a newer search started

    if (!response.ok) {
      showError(data.error || `Something went wrong (HTTP ${response.status}). Please try again.`);
      return;
    }

    clearStatus();
    render(data);

    // Show the real nickname instead of a pasted profile link.
    input.value = data.player.nickname;
    const query = new URLSearchParams({ player: data.player.nickname, matches }).toString();
    history.replaceState(null, "", `${location.pathname}?${query}`);
  } catch (error) {
    if (request === currentRequest) {
      showError("Could not reach the server. Check your connection and try again.");
    }
  } finally {
    if (request === currentRequest) submitButton.disabled = false;
  }
}

// ---------- rendering ----------

let trendMatches = [];

function render(data) {
  result.hidden = false; // visible first, so the chart can measure its width

  renderPlayer(data);
  renderScore(data);
  renderBreakdown(data.components);
  renderStats(data.stats, data.averages);
  trendMatches = data.matches;
  renderTrend(trendMatches);
  renderMaps(data.maps);

  document.title = `${data.player.nickname}: ${data.score.toFixed(1)} — Mully Rating`;

  if (result.getBoundingClientRect().top > window.innerHeight * 0.6) {
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderPlayer(data) {
  const player = data.player;

  const avatar = $("avatar");
  const fallback = $("avatar-fallback");
  fallback.textContent = player.nickname.slice(0, 1).toUpperCase();
  fallback.hidden = false;
  avatar.hidden = true;
  avatar.onload = () => { avatar.hidden = false; fallback.hidden = true; };
  avatar.onerror = () => { avatar.hidden = true; fallback.hidden = false; };
  avatar.removeAttribute("src");
  if (player.avatar) avatar.src = player.avatar;

  const profile = `https://www.faceit.com/en/players/${encodeURIComponent(player.nickname)}`;
  $("nickname").replaceChildren(
    el("a", { href: profile, target: "_blank", rel: "noopener", title: "Open FACEIT profile", text: player.nickname }),
  );

  const meta = [];
  if (player.flag) meta.push(el("span", { title: (player.country || "").toUpperCase(), text: player.flag }));
  meta.push(el("span", { class: "level", text: `Level ${player.level}` }));
  meta.push(el("span", { text: `${player.elo} ELO` }));
  $("player-meta").replaceChildren(...meta);

  $("matches-note").textContent = data.matches_analyzed < data.matches_requested
    ? `${data.matches_analyzed} of ${data.matches_requested} matches analyzed`
    : `${data.matches_analyzed} matches analyzed`;
}

function renderScore(data) {
  const card = $("score-card");
  card.className = `card score-card tier-${data.tier}`;
  $("score").textContent = data.score.toFixed(1);
  $("tier").textContent = `${data.tier} · ${data.tier_name}`;

  const fill = $("score-fill");
  fill.style.width = "0";
  requestAnimationFrame(() => requestAnimationFrame(() => {
    fill.style.width = `${clamp(data.score)}%`;
  }));
}

function renderBreakdown(components) {
  const rows = PARTS.map(([key, name, hint]) => {
    const value = components[key];
    return el("div", { class: "part" },
      el("div", { class: "part-name", text: name }, el("small", { text: hint })),
      meter(value),
      el("div", { class: "part-value", text: String(value) }),
    );
  });
  $("breakdown").replaceChildren(...rows);
}

function renderStats(stats, averages) {
  const tiles = STATS.map(([key, label, format]) => {
    const value = stats[key];
    const average = averages[key];
    // Within 3% of average counts as average.
    const direction = value > average * 1.03 ? "up" : value < average * 0.97 ? "down" : "";
    return el("div", { class: "stat" },
      el("div", { class: "stat-label", text: label }),
      el("div", { class: `stat-value ${direction}`, text: format(value) }),
      el("div", { class: "stat-average", text: `avg ${format(average)}` }),
    );
  });
  $("stats").replaceChildren(...tiles);
}

function renderTrend(matches) {
  const box = $("trend");
  box.replaceChildren();

  if (!matches.length) {
    box.append(el("p", { class: "muted", text: "No matches to show." }));
    return;
  }

  // Drawn in real pixels for the current width, so text stays readable on phones.
  const W = Math.max(280, Math.round(box.clientWidth || 720));
  const H = W < 520 ? 220 : 260;
  const L = 34, R = 14, T = 14, B = 28;
  const plotW = W - L - R;
  const plotH = H - T - B;
  const n = matches.length;
  const x = (i) => (n === 1 ? L + plotW / 2 : L + (i * plotW) / (n - 1));
  const y = (v) => T + (1 - clamp(v) / 100) * plotH;

  const chart = svg("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": `Mully Rating in each of the last ${n} matches, oldest first`,
  });

  const gradient = svg("linearGradient", { id: "trend-fill", x1: "0", y1: "0", x2: "0", y2: "1" });
  gradient.append(
    svg("stop", { offset: "0%", "stop-color": "#ff5500", "stop-opacity": "0.35" }),
    svg("stop", { offset: "100%", "stop-color": "#ff5500", "stop-opacity": "0" }),
  );
  const defs = svg("defs");
  defs.append(gradient);
  chart.append(defs);

  for (const value of [0, 25, 50, 75, 100]) {
    chart.append(svg("line", { class: "grid-line", x1: L, x2: W - R, y1: y(value), y2: y(value) }));
    const label = svg("text", { class: "axis-label", x: L - 8, y: y(value) + 4, "text-anchor": "end" });
    label.textContent = value;
    chart.append(label);
  }

  for (const [text, posX, anchor] of [["oldest", L, "start"], ["newest", W - R, "end"]]) {
    const label = svg("text", { class: "axis-label", x: posX, y: H - 6, "text-anchor": anchor });
    label.textContent = text;
    chart.append(label);
  }

  const points = matches.map((match, i) => [x(i), y(match.score)]);
  const path = points.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join(" ");
  const bottom = y(0).toFixed(1);

  chart.append(svg("path", {
    class: "area",
    d: `${path} L${points[n - 1][0].toFixed(1)},${bottom} L${points[0][0].toFixed(1)},${bottom} Z`,
  }));
  chart.append(svg("path", { class: "line", d: path }));

  const average = matches.reduce((sum, match) => sum + match.score, 0) / n;
  chart.append(svg("line", { class: "average-line", x1: L, x2: W - R, y1: y(average), y2: y(average) }));
  const averageLabel = svg("text", {
    class: "average-label",
    x: W - R,
    y: average > 88 ? y(average) + 16 : y(average) - 7,
    "text-anchor": "end",
  });
  averageLabel.textContent = `Match average ${average.toFixed(1)}`;

  const cursor = svg("line", { class: "cursor", y1: T, y2: T + plotH });
  chart.append(cursor);

  const spacing = plotW / Math.max(n - 1, 1);
  const radius = clamp(spacing / 3, 2, 4.5);
  const circles = matches.map((match, i) => {
    const circle = svg("circle", {
      class: `point tier-${tierOf(match.score)}`,
      cx: points[i][0],
      cy: points[i][1],
      r: radius,
    });
    chart.append(circle);
    return circle;
  });

  // Added last so it is drawn on top of the points.
  chart.append(averageLabel);

  const tooltip = el("div", { class: "tooltip" });
  tooltip.hidden = true;
  box.append(chart, tooltip);

  let active = -1;

  function show(i) {
    if (i === active) return;
    if (active >= 0) {
      circles[active].classList.remove("active");
      circles[active].setAttribute("r", radius);
    }
    active = i;

    const match = matches[i];
    circles[i].classList.add("active");
    circles[i].setAttribute("r", radius + 2);
    cursor.setAttribute("x1", points[i][0]);
    cursor.setAttribute("x2", points[i][0]);
    cursor.classList.add("visible");

    tooltip.className = `tooltip tier-${tierOf(match.score)}`;
    tooltip.replaceChildren(
      el("span", { class: "muted", text: `Match ${i + 1} · ${match.map} ` }),
      el("strong", { text: match.score.toFixed(1) }),
    );
    tooltip.hidden = false;

    // Keep the tooltip inside the chart near the left and right edges.
    const scale = box.clientWidth / W;
    const half = tooltip.offsetWidth / 2;
    const left = clamp(points[i][0] * scale, half, box.clientWidth - half);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${points[i][1] * scale}px`;
  }

  function hide() {
    if (active >= 0) {
      circles[active].classList.remove("active");
      circles[active].setAttribute("r", radius);
    }
    active = -1;
    cursor.classList.remove("visible");
    tooltip.hidden = true;
  }

  function pointAt(event) {
    const rect = chart.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * W;
    const i = n === 1 ? 0 : Math.round(((px - L) / plotW) * (n - 1));
    show(clamp(i, 0, n - 1));
  }

  // pointerdown: a tap on a phone does not send pointermove.
  chart.addEventListener("pointerdown", pointAt);
  chart.addEventListener("pointermove", pointAt);
  chart.addEventListener("pointerleave", (event) => {
    // On touch screens the finger "leaves" right after the tap; keep the tooltip.
    if (event.pointerType !== "touch") hide();
  });
}

function renderMaps(maps) {
  const box = $("maps");

  if (!maps.length) {
    box.replaceChildren(el("p", { class: "muted", text: "No map data." }));
    return;
  }

  const head = el("thead", {}, el("tr", {},
    el("th", { text: "Map" }),
    el("th", { class: "bar-cell", "aria-hidden": "true" }),
    el("th", { class: "num", text: "Rating" }),
    el("th", { class: "num", text: "Games" }),
  ));

  const rows = maps.map((map) => el("tr", { class: `tier-${map.tier}` },
    el("td", {}, el("span", { class: "map-name" }, el("span", { class: "dot", "aria-hidden": "true" }), map.map)),
    el("td", { class: "bar-cell" }, meter(map.score)),
    el("td", { class: "num", text: map.score.toFixed(1) }),
    el("td", { class: "num", text: String(map.games) }),
  ));

  box.replaceChildren(el("table", { class: "maps-table" }, head, el("tbody", {}, ...rows)));
}

// ---------- events ----------

let resizeTimer = null;
let lastWidth = window.innerWidth;
window.addEventListener("resize", () => {
  if (window.innerWidth === lastWidth || result.hidden || !trendMatches.length) return;
  lastWidth = window.innerWidth;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => renderTrend(trendMatches), 150);
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const player = input.value.trim();
  if (!player) return;
  const matches = form.elements.matches.value;
  writeUrl(player, matches);
  analyze(player, matches);
});

window.addEventListener("popstate", () => {
  const state = readUrl();
  fillForm(state);
  if (state.player) {
    analyze(state.player, state.matches);
  } else {
    currentRequest++;
    clearStatus();
    result.hidden = true;
    submitButton.disabled = false;
  }
});

$("copy-link").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(location.href);
    button.textContent = "Link copied ✓";
    setTimeout(() => { button.textContent = "Copy link to this result"; }, 2000);
  } catch {
    window.prompt("Copy this link:", location.href);
  }
});

// Open a shared link like /?player=nick&matches=30 right away.
const initial = readUrl();
fillForm(initial);
if (initial.player) analyze(initial.player, initial.matches);
