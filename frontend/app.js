/* ============================================================================
   Transition Radar - Frontend
   ============================================================================
   Este archivo SOLO habla con el backend Flask vía fetch() y dibuja los
   resultados en el HTML. No toca ningún archivo de datos directamente:
   toda la lógica de negocio (difficulty_score, cursos, wellness, etc.)
   vive en claude/app.py. Aquí solo pedimos y mostramos.
   ========================================================================= */

const API_BASE = 'http://127.0.0.1:5000';

// Estado simple en memoria (no localStorage - ver nota de la skill de artifacts,
// pero aquí ni aplica: esto corre como archivo local, no como artifact).
let perfilActual = null; // lo que devuelve /api/parse-cv

// ----------------------------------------------------------------------------
// Helper genérico para llamar al backend
// ----------------------------------------------------------------------------
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Error ${res.status} en ${path}`);
  }
  return res.json();
}

// ----------------------------------------------------------------------------
// HEALTH CHECK - se corre apenas carga la página
// ----------------------------------------------------------------------------
async function checkHealth() {
  const statusEl = document.getElementById('status');
  try {
    const data = await apiFetch('/health');
    statusEl.textContent = `Backend conectado · ${data.data_loaded.cursos} cursos, ${data.data_loaded.skills_mapping} ocupaciones cargadas`;
    statusEl.className = 'status status-ok';
  } catch (err) {
    statusEl.textContent = 'No se pudo conectar al backend. ¿Corriste "python app.py"?';
    statusEl.className = 'status status-error';
  }
}

// ----------------------------------------------------------------------------
// PASO 1: Parse CV
// ----------------------------------------------------------------------------
async function cargarCV() {
  const btn = document.getElementById('btn-load-cv');
  btn.disabled = true;
  btn.textContent = 'Cargando...';

  try {
    const cv = await apiFetch('/api/parse-cv', {
      method: 'POST',
      body: JSON.stringify({}),
    });

    perfilActual = cv;

    document.getElementById('cv-nombre').textContent = cv.nombre;
    document.getElementById('cv-ocupacion').textContent = cv.ocupacion_actual;
    document.getElementById('cv-experiencia').textContent = `${cv.experiencia_años} años`;
    document.getElementById('cv-salario').textContent = `$${cv.salario_actual_usd} USD`;
    document.getElementById('cv-ubicacion').textContent = cv.ubicacion;

    const skillsEl = document.getElementById('cv-skills');
    skillsEl.innerHTML = '';
    cv.skills_identificadas.forEach(skill => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = skill;
      skillsEl.appendChild(chip);
    });

    document.getElementById('cv-result').classList.remove('hidden');
    document.getElementById('btn-matching').disabled = false;
  } catch (err) {
    alert(`Error cargando CV: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Cargar otro CV de ejemplo';
  }
}

// ----------------------------------------------------------------------------
// PASO 2: Matching
// ----------------------------------------------------------------------------
async function verOpciones() {
  if (!perfilActual) return;

  const btn = document.getElementById('btn-matching');
  const contenedor = document.getElementById('matching-result');
  btn.disabled = true;
  btn.textContent = 'Calculando...';
  contenedor.innerHTML = '';

  try {
    const data = await apiFetch('/api/matching', {
      method: 'POST',
      body: JSON.stringify({
        ocupacion_actual: perfilActual.ocupacion_actual,
        skills_actuales: perfilActual.skills_identificadas,
      }),
    });

    data.ocupaciones_objetivo.forEach((ocu, i) => {
      contenedor.appendChild(renderMatchCard(ocu, i));
    });

    // Animar las barras de progreso después de insertarlas en el DOM
    requestAnimationFrame(() => {
      document.querySelectorAll('.bar-fill').forEach(bar => {
        const pct = bar.dataset.pct;
        setTimeout(() => { bar.style.width = `${pct}%`; }, 50);
      });
    });
  } catch (err) {
    contenedor.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Actualizar opciones';
  }
}

function renderMatchCard(ocu, index) {
  const matchPct = Math.round(100 - ocu.difficulty_score); // % de compatibilidad (inverso a dificultad)

  const card = document.createElement('div');
  card.className = 'match-card';
  card.style.animationDelay = `${index * 80}ms`;

  const comunes = ocu.skills_comunes.map(s => `<span class="chip common">${s}</span>`).join('');
  const faltantes = ocu.skills_faltantes.map(s => `<span class="chip missing">${s}</span>`).join('');

  const cursosHtml = ocu.cursos_recomendados.length
    ? ocu.cursos_recomendados.map(c => `
        <div class="course-item">
          <span>${c.nombre} (${c.duracion_horas}h, ${c.dificultad})</span>
          ${c.certificacion ? '<span class="cert">✓ Certificado</span>' : ''}
        </div>
      `).join('')
    : '<p class="muted" style="margin:6px 0 0;">No hay cursos que cubran los skills faltantes.</p>';

  card.innerHTML = `
    <div class="match-head">
      <h3>${ocu.ocupacion_objetivo}</h3>
      <span class="match-score"><b>${matchPct}%</b> match</span>
    </div>
    <div class="bar-track">
      <div class="bar-fill" data-pct="${matchPct}"></div>
    </div>
    <div class="match-detail"><span class="label">Ya tienes:</span> ${comunes || '<span class="muted">—</span>'}</div>
    <div class="match-detail"><span class="label">Te falta:</span> ${faltantes || '<span class="muted">nada, ¡ya calificas!</span>'}</div>
    <div class="courses-list">${cursosHtml}</div>
  `;

  return card;
}

// ----------------------------------------------------------------------------
// PASO 3: Wellness
// ----------------------------------------------------------------------------
async function pedirApoyo() {
  const stress = Number(document.getElementById('stress').value);
  const confidence = Number(document.getElementById('confidence').value);
  const ocupacionObjetivo = document.querySelector('.match-card h3')?.textContent || 'Data Analyst';

  const btn = document.getElementById('btn-wellness');
  const contenedor = document.getElementById('wellness-result');
  btn.disabled = true;
  btn.textContent = 'Consultando...';

  try {
    const data = await apiFetch('/api/wellness', {
      method: 'POST',
      body: JSON.stringify({
        stress_level: stress,
        confidence_level: confidence,
        ocupacion_objetivo: ocupacionObjetivo,
      }),
    });

    const cohort = data.cohort_recommendation;

    contenedor.innerHTML = `
      <div class="wellness-card">
        <p class="wellness-msg">"${data.mensaje}"</p>
        <p class="wellness-action">→ ${data.accion_sugerida}</p>
        ${cohort ? `
          <div class="cohort-box">
            <h4>${cohort.nombre}</h4>
            <p class="cohort-meta">${cohort.ubicacion} · ${Math.round(cohort.tasa_finalizacion * 100)}% tasa de finalización · Facilitador: ${cohort.facilitador}</p>
          </div>
        ` : ''}
      </div>
    `;
    contenedor.classList.remove('hidden');
  } catch (err) {
    contenedor.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
    contenedor.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Actualizar';
  }
}

// ----------------------------------------------------------------------------
// EXPLORAR: cursos, ocupaciones, cohorts
// ----------------------------------------------------------------------------
async function cargarCursos() {
  const panel = document.getElementById('tab-cursos');
  panel.innerHTML = '<p class="muted">Cargando...</p>';
  try {
    const data = await apiFetch('/api/cursos');
    panel.innerHTML = data.cursos.map(c => `
      <div class="row-item">
        <span>${c.nombre}</span>
        <span class="row-sub">${c.duracion_horas}h · ${c.dificultad}</span>
      </div>
    `).join('');
  } catch (err) {
    panel.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
  }
}

async function cargarOcupaciones() {
  const panel = document.getElementById('tab-ocupaciones');
  panel.innerHTML = '<p class="muted">Cargando...</p>';
  try {
    const data = await apiFetch('/api/ocupaciones');
    panel.innerHTML = data.ocupaciones.map(o => `
      <div class="row-item">
        <span>${o.nombre}</span>
        <span class="row-sub">${o.skills_requeridos.length} skills</span>
      </div>
    `).join('');
  } catch (err) {
    panel.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
  }
}

async function cargarCohorts() {
  const panel = document.getElementById('tab-cohorts');
  panel.innerHTML = '<p class="muted">Cargando...</p>';
  try {
    const data = await apiFetch('/api/cohorts');
    panel.innerHTML = data.cohorts.map(c => `
      <div class="row-item">
        <span>${c.nombre}</span>
        <span class="row-sub">${c.ubicacion}</span>
      </div>
    `).join('');
  } catch (err) {
    panel.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
  }
}

function initTabs() {
  const buttons = document.querySelectorAll('.tab-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
      const targetPanel = document.getElementById(`tab-${btn.dataset.tab}`);
      targetPanel.classList.remove('hidden');

      if (btn.dataset.tab === 'cursos') cargarCursos();
      if (btn.dataset.tab === 'ocupaciones') cargarOcupaciones();
      if (btn.dataset.tab === 'cohorts') cargarCohorts();
    });
  });
}

// ----------------------------------------------------------------------------
// INIT
// ----------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  initTabs();
  cargarCursos(); // tab por defecto

  document.getElementById('btn-load-cv').addEventListener('click', cargarCV);
  document.getElementById('btn-matching').addEventListener('click', verOpciones);
  document.getElementById('btn-wellness').addEventListener('click', pedirApoyo);

  document.getElementById('stress').addEventListener('input', e => {
    document.getElementById('stress-val').textContent = e.target.value;
  });
  document.getElementById('confidence').addEventListener('input', e => {
    document.getElementById('confidence-val').textContent = e.target.value;
  });
});
