const DATA_BASE = "data/";
const SHORTLIST_KEY = "cre-signal-shortlist";

function parseCSV(text) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i], next = text[i + 1];
    if (ch === '"' && quoted && next === '"') { cell += '"'; i += 1; continue; }
    if (ch === '"') { quoted = !quoted; continue; }
    if (ch === "," && !quoted) { row.push(cell); cell = ""; continue; }
    if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && next === "\n") i += 1;
      row.push(cell); cell = "";
      if (row.some(value => value !== "")) rows.push(row);
      row = []; continue;
    }
    cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const headers = rows.shift() || [];
  return rows.map(values => Object.fromEntries(headers.map((key, index) => [key, values[index] || ""])));
}

async function loadData() {
  const [statusResponse, historyResponse] = await Promise.all([
    fetch(`${DATA_BASE}status.json`, {cache: "no-store"}),
    fetch(`${DATA_BASE}history.csv`, {cache: "no-store"}),
  ]);
  if (!statusResponse.ok || !historyResponse.ok) throw new Error("Data files are not available yet.");
  return {status: await statusResponse.json(), history: parseCSV(await historyResponse.text())};
}

function setConnection(text, offline = false) {
  const item = document.getElementById("connection-status");
  if (item) { item.textContent = text; if (offline) item.style.background = "#fae8dc"; }
}

function esc(value) { return String(value || "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[char])); }
function daysBetween(start, end) { return Math.max(0, Math.round((new Date(`${end}T00:00:00Z`) - new Date(`${start}T00:00:00Z`)) / 86400000)); }
function postingMarkup(row, compact = false, saved = false) {
  return `<article class="${compact ? "posting-row" : "posting-card"}"><a href="${esc(row.url)}" target="_blank" rel="noreferrer">${esc(row.title)}</a><div class="posting-meta">${esc(row.employer)} · ${esc(row.location || "Location not provided")}${row.department ? ` · ${esc(row.department)}` : ""}</div>${row.first_seen ? `<span class="tag">First seen ${esc(row.first_seen)}</span>` : ""}${compact ? "" : `<button class="star ${saved ? "saved" : ""}" data-star="${esc(row.posting_id)}" aria-label="${saved ? "Remove from shortlist" : "Save to shortlist"}">${saved ? "★" : "☆"}</button>`}</article>`;
}

function renderToday({status, history}) {
  setConnection("Online");
  document.getElementById("last-run").textContent = status.run_time ? new Date(status.run_time).toLocaleString() : "Not run";
  document.getElementById("first-run").textContent = status.first_run_date ? `History began ${status.first_run_date}` : "Waiting for first raw file";
  ["days", "open", "new", "removed"].forEach(key => { document.getElementById(`metric-${key}`).textContent = status[key === "days" ? "days_with_success" : key === "new" ? "new_today" : key === "removed" ? "removed_today" : key]; });
  const sources = document.getElementById("source-grid");
  sources.innerHTML = status.sources.map(source => `<div class="source-item"><strong>${esc(source.name)}</strong><span><span><i class="dot ${source.ok ? "ok" : ""}"></i>${source.ok ? "Healthy" : "Failed"}</span><b>${source.count}</b></span></div>`).join("");
  const latest = status.run_time ? status.run_time.slice(0, 10) : "";
  const newRows = history.filter(row => row.first_seen === latest && row.first_run !== "true");
  const removedRows = history.filter(row => row.removed_date === latest);
  document.getElementById("new-count").textContent = newRows.length;
  document.getElementById("removed-count").textContent = removedRows.length;
  document.getElementById("new-list").innerHTML = newRows.length ? newRows.map(row => postingMarkup(row, true)).join("") : `<div class="empty">No new postings in the latest run.</div>`;
  document.getElementById("removed-list").innerHTML = removedRows.length ? removedRows.map(row => postingMarkup(row, true)).join("") : `<div class="empty">No postings were removed in the latest run.</div>`;
}

function renderBrowse({history}) {
  setConnection("Online");
  let roleOnly = true;
  const shortlist = new Set(JSON.parse(localStorage.getItem(SHORTLIST_KEY) || "[]"));
  const employer = document.getElementById("employer-filter"), location = document.getElementById("location-filter");
  [...new Set(history.map(row => row.employer).filter(Boolean))].sort().forEach(value => employer.insertAdjacentHTML("beforeend", `<option value="${esc(value)}">${esc(value)}</option>`));
  [...new Set(history.map(row => row.location).filter(Boolean))].sort().forEach(value => location.insertAdjacentHTML("beforeend", `<option value="${esc(value)}">${esc(value)}</option>`));
  const render = () => {
    const search = document.getElementById("title-search").value.toLowerCase().trim();
    const selectedEmployer = employer.value, selectedLocation = location.value, minDays = Number(document.getElementById("days-filter").value || 0), sort = document.getElementById("sort-filter").value;
    const latest = history.reduce((max, row) => row.last_seen > max ? row.last_seen : max, "");
    let rows = history.filter(row => row.status === "open" && (!roleOnly || row.in_role === "true") && (!selectedEmployer || row.employer === selectedEmployer) && (!selectedLocation || row.location === selectedLocation) && (!search || row.title.toLowerCase().includes(search)) && (!minDays || daysBetween(row.first_seen, latest) >= minDays));
    rows.sort((a, b) => sort === "oldest" ? a.first_seen.localeCompare(b.first_seen) : b.first_seen.localeCompare(a.first_seen));
    document.getElementById("result-count").textContent = `${rows.length} open posting${rows.length === 1 ? "" : "s"}`;
    document.getElementById("shortlist-count").textContent = `${shortlist.size} shortlisted`;
    document.getElementById("browse-results").innerHTML = rows.length ? rows.map(row => postingMarkup(row, false, shortlist.has(row.posting_id))).join("") : `<div class="empty">No postings match these filters.</div>`;
    document.querySelectorAll("[data-star]").forEach(button => button.addEventListener("click", () => { const id = button.dataset.star; shortlist.has(id) ? shortlist.delete(id) : shortlist.add(id); localStorage.setItem(SHORTLIST_KEY, JSON.stringify([...shortlist])); render(); }));
  };
  [employer, location, document.getElementById("days-filter"), document.getElementById("sort-filter")].forEach(element => element.addEventListener("change", render));
  document.getElementById("title-search").addEventListener("input", render);
  document.getElementById("role-only").addEventListener("click", () => { roleOnly = true; document.getElementById("role-only").classList.add("active"); document.getElementById("all-postings").classList.remove("active"); render(); });
  document.getElementById("all-postings").addEventListener("click", () => { roleOnly = false; document.getElementById("all-postings").classList.add("active"); document.getElementById("role-only").classList.remove("active"); render(); });
  render();
}

function makeBars(element, data, warm = false) {
  if (!data.length) { element.innerHTML = `<div class="empty">Not enough history yet.</div>`; return; }
  const max = Math.max(...data.map(item => item.value), 1);
  element.innerHTML = data.map(item => `<div class="bar-group"><span class="bar-value">${item.value}</span><div class="bar ${warm ? "warm" : ""}" style="height:${Math.max(3, item.value / max * 120)}px"></div><span class="bar-label">${esc(item.label)}</span></div>`).join("");
}

function makeDualBars(element, allData, roleData) {
  const all = new Map(allData.map(item => [item.label, item.value]));
  const role = new Map(roleData.map(item => [item.label, item.value]));
  const labels = [...new Set([...all.keys(), ...role.keys()])].sort().slice(-12);
  if (!labels.length) { element.innerHTML = `<div class="empty">Not enough history yet.</div>`; return; }
  const max = Math.max(...labels.flatMap(label => [all.get(label) || 0, role.get(label) || 0]), 1);
  element.innerHTML = labels.map(label => {
    const allValue = all.get(label) || 0, roleValue = role.get(label) || 0;
    return `<div class="bar-group"><span class="bar-value">${allValue}/${roleValue}</span><div class="bar-pair"><div class="bar" style="height:${Math.max(3, allValue / max * 120)}px"></div><div class="bar role-bar" style="height:${Math.max(3, roleValue / max * 120)}px"></div></div><span class="bar-label">${esc(label)}</span></div>`;
  }).join("");
}

function median(values) { const sorted = [...values].sort((a, b) => a - b); if (!sorted.length) return null; const mid = Math.floor(sorted.length / 2); return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2; }
function renderMarket({history}) {
  setConnection("Online");
  const latest = history.reduce((max, row) => row.last_seen > max ? row.last_seen : max, "");
  const countBy = (rows, field, limit = 12) => Object.entries(rows.reduce((acc, row) => { const key = row[field] || "Unknown"; acc[key] = (acc[key] || 0) + 1; return acc; }, {})).sort((a, b) => b[1] - a[1]).slice(0, limit).map(([label, value]) => ({label, value}));
  const newAll = countBy(history.filter(row => row.first_run !== "true"), "first_seen", Number.MAX_SAFE_INTEGER).sort((a, b) => a.label.localeCompare(b.label));
  const newRole = countBy(history.filter(row => row.first_run !== "true" && row.in_role === "true"), "first_seen", Number.MAX_SAFE_INTEGER).sort((a, b) => a.label.localeCompare(b.label));
  makeDualBars(document.querySelector('[data-chart="new"]'), newAll, newRole);
  makeBars(document.querySelector('[data-chart="removed"]'), countBy(history.filter(row => row.removed_date), "removed_date").sort((a, b) => a.label.localeCompare(b.label)), true);
  const employers = countBy(history.filter(row => row.status === "open"), "employer"); makeBars(document.querySelector('[data-chart="employers"]'), employers); document.getElementById("employer-finding").textContent = employers.length ? `${employers[0].label} has the largest open-posting footprint.` : "Open roles are distributed across the watchlist.";
  const eligibleDays = history.filter(row => row.first_run !== "true" && row.status === "removed" && row.first_seen && row.removed_date).map(row => daysBetween(row.first_seen, row.removed_date));
  const med = median(eligibleDays); document.getElementById("days-open-finding").textContent = med === null ? "Days open are still being measured." : `The median removed posting lasted ${med} day${med === 1 ? "" : "s"}.`; document.getElementById("days-open-stat").innerHTML = med === null ? `<div class="empty">Need a removed non-first-run posting.</div>` : `<div class="big-stat">${med}<small> days</small></div>`;
  const eligibleSurvival = history.filter(row => row.first_run !== "true" && row.first_seen && latest && daysBetween(row.first_seen, latest) >= 7); const removedWithinSeven = eligibleSurvival.filter(row => row.removed_date && daysBetween(row.first_seen, row.removed_date) <= 7).length; const share = eligibleSurvival.length ? removedWithinSeven / eligibleSurvival.length : null; document.getElementById("survival-finding").textContent = share === null ? "The seven-day removal share is still being measured." : `${Math.round(share * 100)}% of eligible postings were removed within seven days.`; document.getElementById("survival-stat").innerHTML = share === null ? `<div class="empty">Need seven days of eligible history.</div>` : `<div class="big-stat">${Math.round(share * 100)}<small>%</small></div>`;
  const locations = countBy(history.filter(row => row.status === "open"), "location"); makeBars(document.querySelector('[data-chart="locations"]'), locations); document.getElementById("location-finding").textContent = locations.length ? `${locations[0].label} is the most common open-posting location.` : "Open postings are spread across the market.";
}

async function boot() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("service-worker.js").catch(() => {});
  try {
    const data = await loadData();
    const page = document.body.dataset.page;
    if (page === "today") renderToday(data); else if (page === "browse") renderBrowse(data); else renderMarket(data);
  } catch (error) {
    setConnection("Offline", true);
    document.querySelectorAll(".empty").forEach(node => { node.textContent = "The data is not available yet. Run the pipeline once, then reload."; });
    console.error(error);
  }
}
boot();
