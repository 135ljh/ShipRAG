const $ = (id) => document.getElementById(id);

function setPanel(name) {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.panel === name));
  document.querySelectorAll(".panel").forEach((item) => item.classList.remove("active-panel"));
  $(`panel-${name}`).classList.add("active-panel");
}

document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => setPanel(item.dataset.panel)));

function item(title, meta = "", body = "") {
  return `<div class="item">
    <div class="item-title">${escapeHtml(title)}</div>
    ${meta ? `<div class="item-meta">${escapeHtml(meta)}</div>` : ""}
    ${body ? `<div class="item-body">${escapeHtml(body)}</div>` : ""}
  </div>`;
}

function traceItem(step, index) {
  return `<div class="trace-item">
    <div class="trace-index">${index + 1}</div>
    <div>
      <div class="trace-title">${escapeHtml(step.agent)} <span>${escapeHtml(step.status)}</span></div>
      <div class="trace-meta">${escapeHtml(step.role)} | ${escapeHtml(step.detail)} | ${Number(step.elapsed_ms || 0).toFixed(2)}ms</div>
    </div>
  </div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

$("healthBtn").addEventListener("click", async () => {
  const res = await fetch("/health");
  alert(JSON.stringify(await res.json()));
});

$("askBtn").addEventListener("click", async () => {
  $("answerStatus").textContent = "检索中";
  $("answerStatus").className = "badge info";
  $("answerBox").textContent = "正在调度多智能体，检索 Neo4j 与 Qdrant...";
  $("agentTraceBox").innerHTML = "";
  try {
    const data = await postJson("/ask", {
      question: $("questionInput").value,
      top_k: Number($("topKInput").value),
      graph_hops: Number($("hopsInput").value)
    });
    const elapsed = data.metadata?.elapsed_ms ? `${Math.round(data.metadata.elapsed_ms)}ms` : "";
    const cache = data.metadata?.cache_hit ? "缓存" : "";
    $("answerStatus").textContent = ["已生成", cache, elapsed].filter(Boolean).join(" | ");
    $("answerStatus").className = "badge success";
    $("answerBox").textContent = data.answer;
    $("entitiesBox").innerHTML = data.linked_entities.map((e) => item(e.name, e.type, e.definition)).join("");
    $("graphBox").innerHTML = data.evidence.graph.map((g) => item(`${g.head} --${g.relation_zh || g.relation_type}--> ${g.tail}`, g.path, g.evidence)).join("");
    $("docsBox").innerHTML = data.evidence.documents.map((d) => item(d.chunk_id, `page ${d.page_start} | score ${Number(d.score).toFixed(4)}`, d.text)).join("");
    $("agentTraceBox").innerHTML = (data.metadata?.agent_trace || []).map(traceItem).join("");
  } catch (err) {
    $("answerStatus").textContent = "失败";
    $("answerStatus").className = "badge info";
    $("answerBox").textContent = String(err);
  }
});

$("graphBtn").addEventListener("click", async () => {
  const data = await postJson("/graph/search", { entity: $("graphEntityInput").value, hops: 2, limit: 80 });
  $("graphSearchBox").innerHTML = [
    ...data.entities.map((e) => item(e.name, e.type, e.definition)),
    ...data.facts.map((g) => item(`${g.head} --${g.relation_zh || g.relation_type}--> ${g.tail}`, g.path, g.evidence))
  ].join("");
});

$("vectorBtn").addEventListener("click", async () => {
  const data = await postJson("/vector/search", { query: $("vectorQueryInput").value, top_k: 8 });
  $("vectorSearchBox").innerHTML = data.documents.map((d) => item(d.chunk_id, `page ${d.page_start} | score ${Number(d.score).toFixed(4)}`, d.text)).join("");
});
