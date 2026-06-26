const $ = (id) => document.getElementById(id);

async function checkHealth() {
  try {
    const res = await fetch('/health');
    const data = await res.json();
    $('status').innerHTML = [
      `服务：${data.status}`,
      `Chunks：${data.chunks}`,
      `实体：${data.entities}`,
      `关系：${data.relations}`,
      `Pangu：${data.pangu?.status || 'unknown'}`
    ].join('<br>');
  } catch (err) {
    $('status').textContent = `服务异常：${err}`;
  }
}

function renderItems(id, rows, mapper) {
  const box = $(id);
  box.innerHTML = '';
  if (!rows || rows.length === 0) {
    box.innerHTML = '<div class="muted">无</div>';
    return;
  }
  rows.slice(0, 8).forEach((row) => {
    const div = document.createElement('div');
    div.className = 'item';
    div.innerHTML = mapper(row);
    box.appendChild(div);
  });
}

async function ask() {
  const question = $('question').value.trim();
  if (!question) return;
  $('badge').textContent = '生成中';
  $('answer').textContent = '正在检索第五章图谱和教材证据...';
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
    renderItems('entities', data.linked_entities, (e) => `<strong>${e.name}</strong><span class="muted">${e.type} | score ${e.score}</span><br>${e.definition || ''}`);
    renderItems('graph', data.evidence?.graph, (g) => `<strong>${g.head} --${g.relation_zh || g.relation}--> ${g.tail}</strong><span class="muted">score ${g.score}</span><br>${g.evidence || ''}`);
    renderItems('docs', data.evidence?.documents, (d) => `<strong>${d.id}</strong><span class="muted">位置 ${d.page_start} | score ${d.score}</span><br>${(d.text || '').slice(0, 220)}`);
  } catch (err) {
    $('badge').textContent = '失败';
    $('answer').textContent = String(err);
  }
}

$('askBtn').addEventListener('click', ask);
checkHealth();
