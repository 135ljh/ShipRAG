const data = window.CHAPTER5_GRAPH;
const canvas = document.getElementById('graph');
const ctx = canvas.getContext('2d');
const detailBody = document.getElementById('detailBody');
const colors = {
  Chapter: '#64748b',
  ProcessObject: '#2563eb',
  Component: '#0891b2',
  Process: '#16a34a',
  Operation: '#ca8a04',
  ToolEquipment: '#9333ea',
  Measurement: '#db2777',
  Parameter: '#f97316',
  Material: '#0f766e',
  QualityRequirement: '#dc2626',
  Defect: '#7f1d1d',
  StandardSafety: '#475569'
};

const nodes = data.nodes.map(n => ({...n, vx: 0, vy: 0, visible: true}));
const nodeById = new Map(nodes.map(n => [n.id, n]));
const edges = data.edges.map(e => ({...e, sourceNode: nodeById.get(e.source), targetNode: nodeById.get(e.target)})).filter(e => e.sourceNode && e.targetNode);
let transform = {x: 0, y: 0, k: 1};
let draggingNode = null;
let panning = false;
let last = {x: 0, y: 0};
let showLabels = true;
let enabledTypes = new Set([...new Set(nodes.map(n => n.type))]);
let minDegree = 0;
let selected = null;

function resize() {
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.floor(rect.width * devicePixelRatio);
  canvas.height = Math.floor(rect.height * devicePixelRatio);
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  draw();
}

function world(screenX, screenY) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (screenX - rect.left - transform.x) / transform.k,
    y: (screenY - rect.top - transform.y) / transform.k
  };
}

function screen(node) {
  return {x: node.x * transform.k + transform.x, y: node.y * transform.k + transform.y};
}

function applyFilters() {
  nodes.forEach(n => n.visible = enabledTypes.has(n.type) && n.degree >= minDegree);
  draw();
}

function draw() {
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);
  ctx.lineWidth = 1 / transform.k;
  edges.forEach(e => {
    if (!e.sourceNode.visible || !e.targetNode.visible) return;
    ctx.strokeStyle = selected === e ? '#ef4444' : 'rgba(100,116,139,.26)';
    ctx.beginPath();
    ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
    ctx.lineTo(e.targetNode.x, e.targetNode.y);
    ctx.stroke();
  });
  nodes.forEach(n => {
    if (!n.visible) return;
    const r = 5 + Math.min(10, Math.sqrt(n.degree + 1) * 2);
    ctx.fillStyle = colors[n.type] || '#334155';
    ctx.strokeStyle = selected === n ? '#ef4444' : '#fff';
    ctx.lineWidth = selected === n ? 4 / transform.k : 2 / transform.k;
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    if (showLabels && (transform.k > .45 || n.degree >= 6)) {
      ctx.fillStyle = '#162033';
      ctx.font = `${12 / transform.k}px Microsoft YaHei`;
      ctx.fillText(n.name, n.x + r + 4, n.y + 4);
    }
  });
  ctx.restore();
}

function fit() {
  const visible = nodes.filter(n => n.visible);
  if (!visible.length) return;
  const xs = visible.map(n => n.x);
  const ys = visible.map(n => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const rect = canvas.getBoundingClientRect();
  const k = Math.min(rect.width / Math.max(1, maxX - minX + 220), rect.height / Math.max(1, maxY - minY + 220));
  transform.k = Math.max(.2, Math.min(1.8, k));
  transform.x = rect.width / 2 - ((minX + maxX) / 2) * transform.k;
  transform.y = rect.height / 2 - ((minY + maxY) / 2) * transform.k;
  draw();
}

function nearest(screenX, screenY) {
  const w = world(screenX, screenY);
  let best = null, bestDist = Infinity;
  nodes.forEach(n => {
    if (!n.visible) return;
    const d = Math.hypot(n.x - w.x, n.y - w.y);
    const r = 10 + Math.min(12, Math.sqrt(n.degree + 1) * 2);
    if (d < r && d < bestDist) { best = n; bestDist = d; }
  });
  if (best) return best;
  edges.forEach(e => {
    if (!e.sourceNode.visible || !e.targetNode.visible) return;
    const d = pointLineDistance(w, e.sourceNode, e.targetNode);
    if (d < 6 / transform.k && d < bestDist) { best = e; bestDist = d; }
  });
  return best;
}

function pointLineDistance(p, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const len = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

function showDetail(item) {
  selected = item;
  if (!item) {
    detailBody.textContent = '点击节点或关系查看信息。';
  } else if (item.name) {
    detailBody.innerHTML = `<div class="kv"><strong>${item.name}</strong></div>
      <div class="kv muted">${item.type} | degree ${item.degree}</div>
      <div class="kv">${item.definition || '无定义'}</div>
      <div class="kv muted">source_pages: ${(item.source_pages || []).join(', ') || '无'}</div>`;
  } else {
    detailBody.innerHTML = `<div class="kv"><strong>${item.sourceNode.name} --${item.relation_zh || item.relation}--> ${item.targetNode.name}</strong></div>
      <div class="kv muted">${item.relation} | confidence ${item.confidence}</div>
      <div class="kv">${item.evidence || '无证据文本'}</div>
      <div class="kv muted">chunks: ${(item.source_chunks || []).join(', ') || '无'}</div>`;
  }
  draw();
}

canvas.addEventListener('mousedown', e => {
  const hit = nearest(e.clientX, e.clientY);
  last = {x: e.clientX, y: e.clientY};
  if (hit && hit.name) draggingNode = hit;
  else panning = true;
  if (hit) showDetail(hit);
});
window.addEventListener('mousemove', e => {
  if (draggingNode) {
    const w = world(e.clientX, e.clientY);
    draggingNode.x = w.x;
    draggingNode.y = w.y;
    draw();
  } else if (panning) {
    transform.x += e.clientX - last.x;
    transform.y += e.clientY - last.y;
    last = {x: e.clientX, y: e.clientY};
    draw();
  }
});
window.addEventListener('mouseup', () => { draggingNode = null; panning = false; });
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const before = world(e.clientX, e.clientY);
  const factor = e.deltaY < 0 ? 1.12 : .89;
  transform.k = Math.max(.08, Math.min(4, transform.k * factor));
  const after = world(e.clientX, e.clientY);
  transform.x += (after.x - before.x) * transform.k;
  transform.y += (after.y - before.y) * transform.k;
  draw();
}, {passive: false});

function setup() {
  document.getElementById('stats').innerHTML = [
    `实体：${data.nodes.length}`,
    `关系：${data.edges.length}`,
    `孤立实体：${data.summary.isolated_entities || 0}`
  ].join('<br>');
  const box = document.getElementById('typeFilters');
  [...enabledTypes].sort().forEach(type => {
    const label = document.createElement('label');
    label.className = 'chip';
    label.innerHTML = `<input type="checkbox" checked data-type="${type}"><span class="swatch" style="background:${colors[type] || '#334155'}"></span>${type}`;
    box.appendChild(label);
  });
  box.addEventListener('change', e => {
    if (!e.target.dataset.type) return;
    if (e.target.checked) enabledTypes.add(e.target.dataset.type);
    else enabledTypes.delete(e.target.dataset.type);
    applyFilters();
  });
  document.getElementById('degree').addEventListener('input', e => {
    minDegree = Number(e.target.value);
    document.getElementById('degreeValue').textContent = minDegree;
    applyFilters();
  });
  document.getElementById('fit').addEventListener('click', fit);
  document.getElementById('toggleLabels').addEventListener('click', () => { showLabels = !showLabels; draw(); });
  document.getElementById('search').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const q = e.target.value.trim();
    const n = nodes.find(item => item.name.includes(q));
    if (n) {
      transform.x = canvas.getBoundingClientRect().width / 2 - n.x * transform.k;
      transform.y = canvas.getBoundingClientRect().height / 2 - n.y * transform.k;
      showDetail(n);
    }
  });
  resize();
  fit();
}

window.addEventListener('resize', resize);
setup();
