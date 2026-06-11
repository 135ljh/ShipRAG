const graph = window.DEEPSEEK_GRAPH;
const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");
const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
const adjacency = new Map();
const colors = {
  Chapter: "#2563eb",
  Process: "#059669",
  ProcessObject: "#0f766e",
  Component: "#ea580c",
  Operation: "#7c3aed",
  ToolEquipment: "#dc2626",
  Measurement: "#0891b2",
  Parameter: "#64748b",
  QualityRequirement: "#ca8a04",
  Defect: "#be123c",
  Material: "#8b5cf6",
  StandardSafety: "#475569",
  Unknown: "#111827",
};

for (const edge of graph.edges) {
  if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
  if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
  adjacency.get(edge.source).push(edge);
  adjacency.get(edge.target).push(edge);
}

const state = {
  scale: 0.45,
  offsetX: 0,
  offsetY: 0,
  selected: null,
  draggingNode: null,
  panning: false,
  lastX: 0,
  lastY: 0,
  relation: "ALL",
  minDegree: 0,
  showLabels: true,
  enabledTypes: new Set([...new Set(graph.nodes.map((node) => node.type))]),
};

function resize() {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

function worldToScreen(x, y) {
  return { x: x * state.scale + state.offsetX, y: y * state.scale + state.offsetY };
}

function screenToWorld(x, y) {
  return { x: (x - state.offsetX) / state.scale, y: (y - state.offsetY) / state.scale };
}

function isNodeVisible(node) {
  return state.enabledTypes.has(node.type) && node.degree >= state.minDegree;
}

function isEdgeVisible(edge) {
  if (state.relation !== "ALL" && edge.relation !== state.relation) return false;
  const source = nodeById.get(edge.source);
  const target = nodeById.get(edge.target);
  return source && target && isNodeVisible(source) && isNodeVisible(target);
}

function nodeRadius(node) {
  return Math.max(4, Math.min(22, 4 + Math.sqrt(node.degree + 1) * 1.35));
}

function draw() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  ctx.clearRect(0, 0, width, height);

  const visibleEdges = graph.edges.filter(isEdgeVisible);
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(71, 85, 105, 0.18)";
  for (const edge of visibleEdges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    const a = worldToScreen(source.x, source.y);
    const b = worldToScreen(target.x, target.y);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  const visibleNodes = graph.nodes.filter(isNodeVisible);
  for (const node of visibleNodes) {
    const p = worldToScreen(node.x, node.y);
    const r = nodeRadius(node);
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
    ctx.fillStyle = colors[node.type] || colors.Unknown;
    ctx.globalAlpha = state.selected && state.selected.id !== node.id ? 0.72 : 1;
    ctx.fill();
    ctx.globalAlpha = 1;
    if (state.selected && state.selected.id === node.id) {
      ctx.lineWidth = 4;
      ctx.strokeStyle = "#111827";
      ctx.stroke();
    } else {
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "rgba(255,255,255,0.95)";
      ctx.stroke();
    }
  }

  if (state.showLabels) {
    ctx.font = "12px Microsoft YaHei, Segoe UI, sans-serif";
    ctx.textBaseline = "middle";
    for (const node of visibleNodes) {
      if (node.degree < 3 && state.scale < 0.7 && (!state.selected || state.selected.id !== node.id)) continue;
      const p = worldToScreen(node.x, node.y);
      const r = nodeRadius(node);
      ctx.fillStyle = "rgba(15, 23, 42, 0.86)";
      ctx.fillText(node.name, p.x + r + 4, p.y);
    }
  }

  document.getElementById("visibleCount").textContent = `${visibleNodes.length}/${visibleEdges.length}`;
}

function findNodeAt(x, y) {
  let best = null;
  let bestDistance = Infinity;
  for (const node of graph.nodes) {
    if (!isNodeVisible(node)) continue;
    const p = worldToScreen(node.x, node.y);
    const distance = Math.hypot(p.x - x, p.y - y);
    if (distance < nodeRadius(node) + 6 && distance < bestDistance) {
      best = node;
      bestDistance = distance;
    }
  }
  return best;
}

function showDetails(node) {
  const panel = document.getElementById("detailPanel");
  if (!node) {
    panel.innerHTML = "<h2>选择一个实体</h2><p>点击节点后查看实体定义、来源页和相邻关系。</p>";
    return;
  }
  const edges = (adjacency.get(node.id) || []).slice(0, 18);
  const edgeHtml = edges
    .map((edge) => {
      const otherId = edge.source === node.id ? edge.target : edge.source;
      const other = nodeById.get(otherId);
      return `<div class="edgeItem"><strong>${edge.head} ${edge.relation_zh || edge.relation} ${edge.tail}</strong><p>${edge.evidence || "无证据文本"} ${formatPages(edge.source_pages)}</p></div>`;
    })
    .join("");
  panel.innerHTML = `
    <h2>${escapeHtml(node.name)}</h2>
    <div class="detailMeta">
      <span class="pill">${escapeHtml(node.type)}</span>
      <span class="pill">degree ${node.degree}</span>
      <span class="pill">confidence ${Number(node.confidence || 0).toFixed(2)}</span>
    </div>
    <p>${escapeHtml(node.definition || "暂无定义。")}</p>
    <p>来源页：${formatPages(node.source_pages)}</p>
    <div class="edgeList">${edgeHtml || "<p>没有相邻关系。</p>"}</div>
  `;
}

function formatPages(pages) {
  if (!pages || !pages.length) return "无页码";
  return `页码 ${pages.slice(0, 8).join(", ")}${pages.length > 8 ? " ..." : ""}`;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

function centerOnNode(node) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  state.selected = node;
  state.offsetX = width / 2 - node.x * state.scale;
  state.offsetY = height / 2 - node.y * state.scale;
  showDetails(node);
  draw();
}

function fitView() {
  const nodes = graph.nodes.filter(isNodeVisible);
  if (!nodes.length) return;
  const minX = Math.min(...nodes.map((node) => node.x));
  const maxX = Math.max(...nodes.map((node) => node.x));
  const minY = Math.min(...nodes.map((node) => node.y));
  const maxY = Math.max(...nodes.map((node) => node.y));
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const scaleX = width / Math.max(1, maxX - minX + 220);
  const scaleY = height / Math.max(1, maxY - minY + 220);
  state.scale = Math.max(0.08, Math.min(1.4, Math.min(scaleX, scaleY)));
  state.offsetX = width / 2 - ((minX + maxX) / 2) * state.scale;
  state.offsetY = height / 2 - ((minY + maxY) / 2) * state.scale;
  draw();
}

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mouse = { x: event.clientX - rect.left, y: event.clientY - rect.top };
  const before = screenToWorld(mouse.x, mouse.y);
  const factor = event.deltaY < 0 ? 1.12 : 0.89;
  state.scale = Math.max(0.05, Math.min(4, state.scale * factor));
  state.offsetX = mouse.x - before.x * state.scale;
  state.offsetY = mouse.y - before.y * state.scale;
  draw();
});

canvas.addEventListener("pointerdown", (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const node = findNodeAt(x, y);
  state.lastX = x;
  state.lastY = y;
  if (node) {
    state.draggingNode = node;
    state.selected = node;
    showDetails(node);
  } else {
    state.panning = true;
  }
  canvas.setPointerCapture(event.pointerId);
  draw();
});

canvas.addEventListener("pointermove", (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  if (state.draggingNode) {
    const world = screenToWorld(x, y);
    state.draggingNode.x = world.x;
    state.draggingNode.y = world.y;
    draw();
  } else if (state.panning) {
    state.offsetX += x - state.lastX;
    state.offsetY += y - state.lastY;
    draw();
  }
  state.lastX = x;
  state.lastY = y;
});

canvas.addEventListener("pointerup", (event) => {
  state.draggingNode = null;
  state.panning = false;
  canvas.releasePointerCapture(event.pointerId);
});

function initControls() {
  document.getElementById("nodeCount").textContent = graph.nodes.length;
  document.getElementById("edgeCount").textContent = graph.edges.length;

  const entityList = document.getElementById("entityList");
  entityList.innerHTML = graph.nodes
    .sort((a, b) => b.degree - a.degree)
    .slice(0, 500)
    .map((node) => `<option value="${escapeHtml(node.name)}"></option>`)
    .join("");

  const relationFilter = document.getElementById("relationFilter");
  const relationTypes = [...new Set(graph.edges.map((edge) => edge.relation))].sort();
  relationFilter.innerHTML = `<option value="ALL">全部关系</option>` + relationTypes.map((rel) => `<option value="${rel}">${rel}</option>`).join("");
  relationFilter.addEventListener("change", () => {
    state.relation = relationFilter.value;
    draw();
  });

  const typeFilters = document.getElementById("typeFilters");
  const types = [...new Set(graph.nodes.map((node) => node.type))].sort();
  typeFilters.innerHTML = types
    .map((type) => `<label class="typeChip"><input type="checkbox" value="${type}" checked /> <span style="color:${colors[type] || colors.Unknown}">●</span>${type}</label>`)
    .join("");
  typeFilters.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) state.enabledTypes.add(input.value);
      else state.enabledTypes.delete(input.value);
      draw();
    });
  });

  document.getElementById("resetTypes").addEventListener("click", () => {
    state.enabledTypes = new Set(types);
    typeFilters.querySelectorAll("input").forEach((input) => (input.checked = true));
    draw();
  });

  const degreeFilter = document.getElementById("degreeFilter");
  degreeFilter.addEventListener("input", () => {
    state.minDegree = Number(degreeFilter.value);
    document.getElementById("degreeValue").textContent = state.minDegree;
    draw();
  });

  document.getElementById("labelToggle").addEventListener("change", (event) => {
    state.showLabels = event.target.checked;
    draw();
  });

  document.getElementById("fitButton").addEventListener("click", fitView);
  document.getElementById("resetButton").addEventListener("click", () => {
    state.scale = 0.45;
    state.offsetX = canvas.clientWidth / 2;
    state.offsetY = canvas.clientHeight / 2;
    draw();
  });

  document.getElementById("searchButton").addEventListener("click", runSearch);
  document.getElementById("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") runSearch();
  });
}

function runSearch() {
  const value = document.getElementById("searchInput").value.trim();
  if (!value) return;
  const node =
    graph.nodes.find((item) => item.name === value) ||
    graph.nodes.find((item) => item.name.includes(value)) ||
    graph.nodes.find((item) => value.includes(item.name));
  if (node) centerOnNode(node);
}

window.addEventListener("resize", resize);
initControls();
resize();
fitView();
