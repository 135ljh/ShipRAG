const $ = (id) => document.getElementById(id);

const viewMeta = {
  qa: {
    title: 'RAG 问答',
    sub: '融合 Pangu、多智能体、知识图谱与向量检索，生成可追溯答案。'
  },
  trace: {
    title: '智能执行链路',
    sub: '查看 Planner、Vector、Graph、Fusion、Answer、Verifier 的协作过程。'
  },
  evidence: {
    title: '检索证据',
    sub: '集中查看关联实体、图谱事实和教材片段，快速判断答案依据。'
  }
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function switchView(view) {
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.classList.toggle('active', item.dataset.view === view);
  });
  document.querySelectorAll('.view').forEach((item) => {
    item.classList.toggle('active', item.id === `view-${view}`);
  });
  $('pageTitle').textContent = viewMeta[view].title;
  $('pageSub').textContent = viewMeta[view].sub;
}

async function checkHealth() {
  try {
    const res = await fetch('/health');
    const data = await res.json();
    $('status').innerHTML = [
      `服务：${escapeHtml(data.status)}`,
      `文本块：${escapeHtml(data.chunks)}`,
      `实体：${escapeHtml(data.entities)}`,
      `关系：${escapeHtml(data.relations)}`,
      `向量库：${data.qdrant_enabled ? escapeHtml(data.qdrant_collection) : '未启用'}`,
      `Pangu：${escapeHtml(data.pangu?.status || 'unknown')}`
    ].join('<br>');
  } catch (err) {
    $('status').textContent = `服务异常：${err}`;
  }
}

function renderItems(id, rows, mapper) {
  const box = $(id);
  box.innerHTML = '';
  if (!rows || rows.length === 0) {
    box.innerHTML = '<div class="muted">暂无内容。生成一次答案后，这里会显示对应证据。</div>';
    return;
  }
  rows.slice(0, 18).forEach((row) => {
    const div = document.createElement('div');
    div.className = 'item';
    div.innerHTML = mapper(row);
    box.appendChild(div);
  });
}

function renderTrace(rows) {
  const box = $('agentTrace');
  box.innerHTML = '';
  const count = rows?.length || 0;
  $('traceCount').textContent = `${count} 个步骤`;
  $('metricAgents').textContent = `智能体 ${count}`;
  if (!rows || rows.length === 0) {
    box.innerHTML = '<div class="muted">暂无执行链路。请先在 RAG 问答页生成答案。</div>';
    return;
  }
  rows.forEach((step, index) => {
    const div = document.createElement('div');
    div.className = 'agent-step';
    div.innerHTML = `<strong>${index + 1}. ${escapeHtml(step.agent)}</strong>
      <span class="muted">${escapeHtml(step.action)} | ${escapeHtml(step.elapsed_ms)}ms</span>
      <code>${escapeHtml(JSON.stringify(step.detail || {}, null, 2))}</code>`;
    box.appendChild(div);
  });
}

function updateEvidenceMetrics(data) {
  const docs = data?.evidence?.documents?.length || 0;
  const graph = data?.evidence?.graph?.length || 0;
  $('metricDocs').textContent = `文档 ${docs}`;
  $('metricGraph').textContent = `图谱 ${graph}`;
}

async function ask() {
  const question = $('question').value.trim();
  if (!question) return;
  $('badge').textContent = '生成中';
  $('answer').textContent = '正在调度多智能体，检索向量库、知识图谱和教材证据...';
  const started = performance.now();
  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        question,
        top_k: Number($('topK').value || 5),
        graph_hops: Number($('hops').value || 1)
      })
    });
    const data = await res.json();
    const elapsed = Math.round(performance.now() - started);
    $('badge').textContent = `已生成 | ${elapsed}ms`;
    $('answer').textContent = data.answer || '无答案';
    renderTrace(data.metadata?.agent_trace);
    updateEvidenceMetrics(data);
    renderItems('entities', data.linked_entities, (e) => `<strong>${escapeHtml(e.name)}</strong><span class="muted">${escapeHtml(e.type)} | score ${escapeHtml(e.score)}</span><br>${escapeHtml(e.definition || '')}`);
    renderItems('graph', data.evidence?.graph, (g) => `<strong>${escapeHtml(g.head)} --${escapeHtml(g.relation_zh || g.relation)}--> ${escapeHtml(g.tail)}</strong><span class="muted">score ${escapeHtml(g.score)}</span><br>${escapeHtml(g.evidence || '')}`);
    renderItems('docs', data.evidence?.documents, (d) => `<strong>${escapeHtml(d.id)}</strong><span class="muted">位置 ${escapeHtml(d.page_start)} | ${escapeHtml(d.retrieval_source || 'unknown')} | score ${escapeHtml(d.score)}</span><br>${escapeHtml((d.text || '').slice(0, 260))}`);
  } catch (err) {
    $('badge').textContent = '失败';
    $('answer').textContent = String(err);
  }
}

document.querySelectorAll('.nav-item').forEach((button) => {
  button.addEventListener('click', () => switchView(button.dataset.view));
});

document.querySelectorAll('.tab').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.tab-page').forEach((item) => item.classList.remove('active'));
    button.classList.add('active');
    $(button.dataset.target).classList.add('active');
  });
});

$('askBtn').addEventListener('click', ask);
renderTrace([]);
renderItems('entities', [], () => '');
renderItems('graph', [], () => '');
renderItems('docs', [], () => '');
checkHealth();
