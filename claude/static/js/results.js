/* ============================================================================
   results.js — Dashboard de resultados del análisis (8 secciones)
   ============================================================================
   Lee el resultado guardado por upload.js en localStorage (proximo_last_analysis_v1).
   Si no existe (alguien llega directo a /resultados sin pasar por /analizar),
   redirige de vuelta al flujo de carga en vez de mostrar una pantalla rota.
   ========================================================================= */

const GROWTH_LABEL = { high: 'Alta', medium: 'Media', low: 'Baja' };
const GROWTH_COLOR = { high: 'confidence-alto', medium: 'confidence-medio', low: 'confidence-bajo' };

function cargarAnalisis() {
  const raw = localStorage.getItem(ANALYSIS_STORAGE_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

/* Heurística de tiempo estimado — NO es un modelo entrenado, es una regla
   simple y declarada como tal: ~3 semanas por skill faltante, con piso de
   1 mes y techo de 12. Sirve para dar una referencia, no una certeza. */
function estimarMeses(numSkillsFaltantes) {
  return Math.min(12, Math.max(1, Math.round(numSkillsFaltantes * 0.75)));
}

/* Heurística de confianza — combina disponibilidad de señal de mercado real
   con qué tan bajo es el difficulty_score. También declarada como heurística. */
function estimarConfianza(ocupacion) {
  const tieneSeñal = !!ocupacion.señal_mercado;
  if (tieneSeñal && ocupacion.difficulty_score < 30) return 'alto';
  if (ocupacion.difficulty_score < 55) return 'medio';
  return 'bajo';
}

function initSidebarNav() {
  const links = document.querySelectorAll('.side-link');
  links.forEach(link => {
    link.addEventListener('click', () => {
      links.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      document.querySelectorAll('.result-section').forEach(s => s.hidden = true);
      document.getElementById(`section-${link.dataset.section}`).hidden = false;
      window.scrollTo({ top: document.querySelector('.app-shell').offsetTop - 90, behavior: 'smooth' });
    });
  });
}

function renderContextBar(cv, fecha) {
  const bar = document.getElementById('context-bar');
  const fechaFmt = new Date(fecha).toLocaleDateString('es-PE', { day: 'numeric', month: 'long', year: 'numeric' });
  bar.innerHTML = `
    <div><dt>Perfil</dt><dd>${cv.nombre}</dd></div>
    <div><dt>Ubicación</dt><dd>${cv.ubicacion}</dd></div>
    <div><dt>Sector actual</dt><dd>${cv.ocupacion_actual}</dd></div>
    <div><dt>Fecha del análisis</dt><dd>${fechaFmt}</dd></div>
    <div style="margin-left:auto;"><a href="/analizar" class="btn btn-tertiary btn-sm">Actualizar CV</a></div>
  `;
}

/* ---------------------------------------------------------------------- */
/* 1. RESUMEN EJECUTIVO                                                    */
/* ---------------------------------------------------------------------- */
function renderResumen(cv, matching) {
  const top = matching.ocupaciones_objetivo[0];
  if (!top) {
    document.getElementById('resumen-content').innerHTML = `<div class="empty-state"><h3>Sin transiciones disponibles</h3><p>No encontramos otra ocupación en el catálogo demo para comparar.</p></div>`;
    return;
  }
  const compat = Math.round(100 - top.difficulty_score);
  const meses = estimarMeses(top.num_skills_faltantes);
  const confianza = estimarConfianza(top);
  const señal = top.señal_mercado;

  const perspectiva = señal
    ? (señal.growth_indicator === 'high' ? 'En crecimiento' : señal.growth_indicator === 'medium' ? 'Estable' : 'Riesgo moderado')
    : 'Sin señal de mercado disponible';

  document.getElementById('resumen-content').innerHTML = `
    <div class="summary-hero">
      <div>
        <p class="text-xs text-muted">Tu situación actual</p>
        <p style="font-weight:700; font-size:var(--text-lg); margin-bottom:12px;">${cv.ocupacion_actual} · ${cv.experiencia_años} años de experiencia</p>
        <p class="text-xs text-muted">Transición principal recomendada</p>
        <p style="font-weight:700; font-size:var(--text-lg); color:var(--color-primary);">${top.ocupacion_objetivo}</p>
        <p class="text-sm text-muted" style="margin-top:8px;">Perspectiva de tu sector: <strong>${perspectiva}</strong></p>
      </div>
      <div class="summary-compat">
        <span class="summary-compat-value">${compat}%</span>
        <span class="text-xs text-muted">compatibilidad
          <span class="tooltip-wrap"><span class="tooltip-trigger" tabindex="0">i</span>
            <span class="tooltip-bubble">100% menos el porcentaje de habilidades que aún te faltan para esta ocupación.</span>
          </span>
        </span>
      </div>
    </div>

    <div class="metric-row">
      <div class="metric-item">
        <dt>Dificultad
          <span class="tooltip-wrap"><span class="tooltip-trigger" tabindex="0">i</span><span class="tooltip-bubble">Basada en cuántas habilidades requeridas aún no tienes.</span></span>
        </dt>
        <dd>${top.difficulty_score < 30 ? 'Baja' : top.difficulty_score < 60 ? 'Media' : 'Alta'}</dd>
      </div>
      <div class="metric-item">
        <dt>Tiempo estimado
          <span class="tooltip-wrap"><span class="tooltip-trigger" tabindex="0">i</span><span class="tooltip-bubble">Estimación orientativa (heurística de demostración), no un cálculo garantizado.</span></span>
        </dt>
        <dd>${meses} meses</dd>
      </div>
      <div class="metric-item">
        <dt>Nivel de confianza
          <span class="tooltip-wrap"><span class="tooltip-trigger" tabindex="0">i</span><span class="tooltip-bubble">Combina la disponibilidad de datos reales de mercado con qué tan completa está tu compatibilidad.</span></span>
        </dt>
        <dd><span class="confidence-tag confidence-${confianza}">${confianza === 'alto' ? 'Alto' : confianza === 'medio' ? 'Medio' : 'Bajo'}</span></dd>
      </div>
      <div class="metric-item">
        <dt>Habilidades por aprender</dt>
        <dd>${top.num_skills_faltantes}</dd>
      </div>
    </div>

    <div class="alert alert-info">
      <div><strong>Tu siguiente acción:</strong> revisa la brecha de habilidades y empieza por el curso que cubre más habilidades faltantes a la vez (sección "Cursos").</div>
    </div>
  `;
}

/* ---------------------------------------------------------------------- */
/* 2. PANORAMA DEL SECTOR                                                  */
/* ---------------------------------------------------------------------- */
function renderPanorama(matching) {
  const señal = matching.señal_mercado_actual;
  const el = document.getElementById('panorama-content');

  if (!señal) {
    el.innerHTML = `
      <div class="alert alert-warning">
        No encontramos una señal de mercado real para "${matching.ocupacion_actual}" en el dataset procesado.
        Esta ocupación no tiene una categoría equivalente en los datos de LinkedIn disponibles.
      </div>`;
    return;
  }

  const skills = señal.top_required_skills.map(s => `<span class="chip">${s}</span>`).join('');

  el.innerHTML = `
    <div class="card" style="margin-bottom:16px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div>
          <p class="text-xs text-muted">Categoría de mercado más cercana</p>
          <p style="font-weight:700;">${señal.categoria_linkedin}</p>
        </div>
        <span class="badge badge-real">Dato calculado</span>
      </div>
      ${señal.es_categoria_generica ? `<p class="text-sm text-muted" style="margin-bottom:12px;">${señal.categoria_linkedin === 'Other' ? 'El dataset no tiene una categoría específica para tu ocupación; se muestra la más cercana disponible.' : ''}</p>` : ''}

      <div class="metric-row" style="margin-block:0; padding-block:16px;">
        <div class="metric-item">
          <dt>Vacantes observadas</dt>
          <dd>${señal.position_count.toLocaleString('es-PE')}</dd>
        </div>
        <div class="metric-item">
          <dt>Indicador de crecimiento</dt>
          <dd><span class="confidence-tag ${GROWTH_COLOR[señal.growth_indicator]}">${GROWTH_LABEL[señal.growth_indicator]}</span></dd>
        </div>
        <div class="metric-item">
          <dt>Adopción de trabajo remoto</dt>
          <dd>${Math.round(señal.remote_adoption_rate * 100)}%</dd>
        </div>
        <div class="metric-item">
          <dt>Sobre el dataset</dt>
          <dd class="text-sm">${señal.total_dataset_positions.toLocaleString('es-PE')} empleos analizados</dd>
        </div>
      </div>

      <p class="text-xs text-muted" style="margin-bottom:6px;">Habilidades más pedidas en esta categoría</p>
      <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px;">${skills}</div>
    </div>

    <div class="alert alert-info">
      <div>
        <strong>Fuente:</strong> ${señal.fuente}. <strong>Tipo de dato:</strong> calculado (no es una opinión generada, es un conteo real sobre ese dataset).
        No incluye series históricas por ocupación específica en esta versión — el proyecto sí tiene datos históricos de INEI (2009–2021) a nivel nacional, pero
        todavía no están cruzados automáticamente por ocupación individual.
      </div>
    </div>
  `;
}

/* ---------------------------------------------------------------------- */
/* 3. TRANSITION RADAR                                                     */
/* ---------------------------------------------------------------------- */
function renderRadar(matching, sortBy = 'compat') {
  const el = document.getElementById('radar-content');
  let ocupaciones = [...matching.ocupaciones_objetivo];

  const sorters = {
    compat: (a, b) => a.difficulty_score - b.difficulty_score,
    dificultad: (a, b) => a.difficulty_score - b.difficulty_score,
    crecimiento: (a, b) => {
      const orden = { high: 0, medium: 1, low: 2, undefined: 3 };
      return orden[a.señal_mercado?.growth_indicator] - orden[b.señal_mercado?.growth_indicator];
    },
    tiempo: (a, b) => estimarMeses(a.num_skills_faltantes) - estimarMeses(b.num_skills_faltantes),
  };
  ocupaciones.sort(sorters[sortBy] || sorters.compat);

  el.innerHTML = ocupaciones.map(ocu => {
    const compat = Math.round(100 - ocu.difficulty_score);
    const meses = estimarMeses(ocu.num_skills_faltantes);
    const confianza = estimarConfianza(ocu);
    const comunes = ocu.skills_comunes.slice(0, 4).map(s => `<span class="chip chip-common">${s}</span>`).join('');
    const faltantes = ocu.skills_faltantes.slice(0, 4).map(s => `<span class="chip chip-missing">${s}</span>`).join('');
    const señal = ocu.señal_mercado;

    return `
      <div class="route-card">
        <div class="route-head">
          <h3>${ocu.ocupacion_objetivo}</h3>
          <span class="route-compat">${compat}%</span>
        </div>
        <div class="route-meta">
          <span>Dificultad: ${ocu.difficulty_score < 30 ? 'Baja' : ocu.difficulty_score < 60 ? 'Media' : 'Alta'}</span>
          <span>${meses} meses</span>
          <span class="confidence-tag confidence-${confianza}">Confianza ${confianza}</span>
          ${señal ? `<span class="confidence-tag ${GROWTH_COLOR[señal.growth_indicator]}">Demanda ${GROWTH_LABEL[señal.growth_indicator].toLowerCase()}</span>` : ''}
        </div>
        <div class="route-skills">
          <div><span class="text-xs text-muted">Ya tienes</span><div class="chip-list">${comunes || '<span class="text-xs text-muted">—</span>'}</div></div>
          <div><span class="text-xs text-muted">Te falta</span><div class="chip-list">${faltantes || '<span class="text-xs text-muted">nada</span>'}</div></div>
        </div>
        <p class="text-xs text-muted">Aparece recomendada porque comparte ${ocu.skills_comunes.length} de ${ocu.skills_comunes.length + ocu.skills_faltantes.length} habilidades requeridas con tu perfil actual.</p>
        <button class="btn btn-secondary btn-sm" style="align-self:flex-start;" onclick="explorarRuta('${ocu.ocupacion_objetivo}')">Explorar esta ruta</button>
      </div>
    `;
  }).join('');
}

function explorarRuta(nombre) {
  document.querySelector('[data-section="brecha"]').click();
  showToast(`Mostrando brecha de habilidades para ${nombre}`);
}

/* ---------------------------------------------------------------------- */
/* 4. BRECHA DE HABILIDADES                                                */
/* ---------------------------------------------------------------------- */
function renderBrecha(matching) {
  const top = matching.ocupaciones_objetivo[0];
  const el = document.getElementById('brecha-content');
  if (!top) { el.innerHTML = ''; return; }

  const comunes = top.skills_comunes.map(s => `<span class="chip chip-common">${s}</span>`).join('') || '<span class="text-sm text-muted">Ninguna coincidencia</span>';
  const faltantes = top.skills_faltantes.map(s => `<span class="chip chip-missing">${s}</span>`).join('') || '<span class="text-sm text-muted">Ninguna — ya calificas</span>';
  const pctCubierto = Math.round((top.skills_comunes.length / (top.skills_comunes.length + top.skills_faltantes.length || 1)) * 100);

  el.innerHTML = `
    <div class="card">
      <p class="text-xs text-muted" style="margin-bottom:4px;">Comparando tu perfil con: <strong>${top.ocupacion_objetivo}</strong></p>
      <div class="progress-summary">
        <span class="text-sm text-muted">${pctCubierto}% de la brecha ya cubierta</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pctCubierto}%;"></div></div>
      </div>
      <div class="grid grid-2" style="margin-top:16px;">
        <div>
          <p class="text-xs text-muted" style="margin-bottom:8px;">Habilidades que ya tienes</p>
          <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px;">${comunes}</div>
        </div>
        <div>
          <p class="text-xs text-muted" style="margin-bottom:8px;">Habilidades por desarrollar</p>
          <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px;">${faltantes}</div>
        </div>
      </div>
    </div>
    <p class="text-xs text-muted" style="margin-top:12px;">Para ver la brecha de otra ocupación, ve a "Transiciones recomendadas" y presiona "Explorar esta ruta".</p>
  `;
}

/* ---------------------------------------------------------------------- */
/* 5. CURSOS RECOMENDADOS                                                  */
/* ---------------------------------------------------------------------- */
function renderCursos(matching) {
  const el = document.getElementById('cursos-content');
  const vistos = new Set();
  const cursos = [];

  matching.ocupaciones_objetivo.forEach(ocu => {
    ocu.cursos_recomendados.forEach(curso => {
      if (vistos.has(curso.id)) return;
      vistos.add(curso.id);
      const pctCierre = Math.round((curso.skills_cubre.length / (ocu.num_skills_faltantes || 1)) * 100);
      cursos.push({ ...curso, ocupacion: ocu.ocupacion_objetivo, pctCierre });
    });
  });

  if (!cursos.length) {
    el.innerHTML = `<div class="empty-state"><h3>Sin cursos que mostrar todavía</h3><p>No hay cursos en el catálogo demo que cubran las habilidades faltantes.</p></div>`;
    return;
  }

  const state = proximoState.read();

  el.innerHTML = cursos.map(curso => {
    const guardado = state.savedCourses.includes(curso.id);
    return `
      <div class="course-card">
        <div class="course-head">
          <span class="course-title">${curso.nombre}</span>
          ${curso.certificacion ? '<span class="badge badge-success">Con certificación</span>' : ''}
        </div>
        <p class="text-xs text-muted">Para: ${curso.ocupacion}</p>
        <div class="course-meta">
          <span>${curso.duracion_horas}h</span>
          <span style="text-transform:capitalize;">${curso.dificultad}</span>
        </div>
        <p class="course-gap">Cierra ~${curso.pctCierre}% de la brecha para esta ruta.</p>
        <div class="course-actions">
          <button class="btn btn-tertiary btn-sm" onclick="verCurso('${curso.id}')">Ver curso</button>
          <button class="btn btn-secondary btn-sm" data-course-id="${curso.id}" onclick="toggleCurso('${curso.id}', this)">${guardado ? '★ Guardado' : 'Guardar'}</button>
        </div>
      </div>
    `;
  }).join('');
}

function verCurso(cursoId) {
  showInfoModal({
    title: 'Curso de ejemplo',
    body: `Este curso (${cursoId}) es parte de un catálogo simulado construido para la demo — no enlaza a una plataforma real todavía. En una versión posterior, este botón llevaría a Coursera, Platzi o SENATI según la fuente real del curso.`,
  });
}

function toggleCurso(cursoId, btn) {
  const next = proximoState.update(s => {
    const saved = s.savedCourses.includes(cursoId)
      ? s.savedCourses.filter(id => id !== cursoId)
      : [...s.savedCourses, cursoId];
    return { ...s, savedCourses: saved };
  });
  const guardado = next.savedCourses.includes(cursoId);
  btn.textContent = guardado ? '★ Guardado' : 'Guardar';
  showToast(guardado ? 'Curso guardado' : 'Curso quitado de guardados');
}

/* ---------------------------------------------------------------------- */
/* 6. HACKS PARA EL PERFIL                                                 */
/* ---------------------------------------------------------------------- */
function renderHacks() {
  const state = proximoState.read();
  const el = document.getElementById('hacks-content');

  el.innerHTML = HACKS_DEMO.map(hack => {
    const completado = state.completedHacks.includes(hack.id);
    return `
      <div class="hack-item ${completado ? 'completed' : ''}" data-hack-id="${hack.id}">
        <button class="hack-checkbox" aria-pressed="${completado}" aria-label="Marcar como completado" onclick="toggleHack('${hack.id}')">${completado ? '✓' : ''}</button>
        <div class="hack-body">
          <p class="hack-title">${hack.titulo}</p>
          <p class="text-sm text-muted">${hack.razon}</p>
          <div class="hack-meta">
            <span>Impacto: ${hack.impacto}</span>
            <span>Esfuerzo: ${hack.esfuerzo}</span>
            <span>${hack.tiempo}</span>
          </div>
        </div>
        <button class="btn btn-tertiary btn-sm" onclick="showInfoModal({title:'${hack.titulo}', body:'${hack.razon} (Acción de demostración: en la versión completa esto abriría el editor de tu CV.)'})">${hack.accion}</button>
      </div>
    `;
  }).join('');

  actualizarProgresoHacks();
}

function toggleHack(hackId) {
  proximoState.update(s => {
    const completados = s.completedHacks.includes(hackId)
      ? s.completedHacks.filter(id => id !== hackId)
      : [...s.completedHacks, hackId];
    return { ...s, completedHacks: completados };
  });
  renderHacks();
}

function actualizarProgresoHacks() {
  const state = proximoState.read();
  const total = HACKS_DEMO.length;
  const completados = state.completedHacks.length;
  document.getElementById('hacks-progress-label').textContent = `${completados} de ${total} completados`;
  document.getElementById('hacks-progress-bar').style.width = `${(completados / total) * 100}%`;
}

/* ---------------------------------------------------------------------- */
/* 7. DEMANDA FUTURA                                                       */
/* ---------------------------------------------------------------------- */
function renderFuturo(matching) {
  const el = document.getElementById('futuro-content');
  const conSeñal = matching.ocupaciones_objetivo.filter(o => o.señal_mercado);

  if (!conSeñal.length) {
    el.innerHTML = `<div class="empty-state"><h3>Sin datos de crecimiento disponibles</h3></div>`;
    return;
  }

  el.innerHTML = conSeñal.map(ocu => {
    const señal = ocu.señal_mercado;
    const riesgo = señal.growth_indicator === 'high' ? 'Bajo' : señal.growth_indicator === 'medium' ? 'Moderado' : 'Alto';
    const cursosTop = ocu.cursos_recomendados.slice(0, 2).map(c => `<span class="chip">${c.nombre}</span>`).join('');
    return `
      <div class="card" style="margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:8px;">
          <h3 style="font-size:var(--text-base);">${ocu.ocupacion_objetivo}</h3>
          <span class="confidence-tag ${GROWTH_COLOR[señal.growth_indicator]}">Crecimiento ${GROWTH_LABEL[señal.growth_indicator].toLowerCase()}</span>
        </div>
        <div class="metric-row" style="grid-template-columns:repeat(3,1fr); margin-block:8px; padding-block:8px;">
          <div class="metric-item"><dt>Horizonte</dt><dd>12 meses</dd></div>
          <div class="metric-item"><dt>Riesgo de obsolescencia</dt><dd>${riesgo}</dd></div>
          <div class="metric-item"><dt>Vacantes observadas</dt><dd>${señal.position_count.toLocaleString('es-PE')}</dd></div>
        </div>
        <p class="text-xs text-muted" style="margin-bottom:8px;">Cursos que cubren esta dirección:</p>
        <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px;">${cursosTop || '<span class="text-xs text-muted">Sin cursos asociados</span>'}</div>
      </div>
    `;
  }).join('') + `<p class="text-xs text-muted">Evidencia: ${conSeñal[0].señal_mercado.fuente}. El crecimiento no es una garantía de continuidad futura, es una tendencia observada.</p>`;
}

/* ---------------------------------------------------------------------- */
/* 8. QUÉ BUSCAN LOS EMPLEADORES                                           */
/* ---------------------------------------------------------------------- */
function renderEmpleadores(matching) {
  const el = document.getElementById('empleadores-content');
  const opciones = matching.ocupaciones_objetivo.filter(o => o.señal_mercado);

  if (!opciones.length) {
    el.innerHTML = `<div class="empty-state"><h3>Sin datos disponibles</h3></div>`;
    return;
  }

  el.innerHTML = `
    <div class="field" style="max-width:320px;">
      <label for="empleadores-select">Ver por ocupación</label>
      <select id="empleadores-select" class="select">
        ${opciones.map((o, i) => `<option value="${i}">${o.ocupacion_objetivo}</option>`).join('')}
      </select>
    </div>
    <div id="empleadores-detalle"></div>
  `;

  function pintar(index) {
    const ocu = opciones[index];
    const señal = ocu.señal_mercado;
    const skills = señal.top_required_skills.map(s => `<span class="chip">${s}</span>`).join('');
    document.getElementById('empleadores-detalle').innerHTML = `
      <div class="card">
        <p class="text-xs text-muted" style="margin-bottom:8px;">Habilidades más solicitadas (${señal.categoria_linkedin})</p>
        <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:16px;">${skills}</div>
        <p class="text-xs text-muted" style="margin-bottom:8px;">Tus habilidades actuales</p>
        <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:16px;">
          ${matching.skills_actuales.map(s => `<span class="chip chip-common">${s}</span>`).join('')}
        </div>
        <p class="text-xs text-muted">Nota: las habilidades de empleadores vienen de categorías generales de LinkedIn y las tuyas de un catálogo distinto — se muestran una junto a la otra para comparar a simple vista, no se calcula un porcentaje automático de coincidencia entre ambas.</p>
      </div>
    `;
  }

  document.getElementById('empleadores-select').addEventListener('change', e => pintar(Number(e.target.value)));
  pintar(0);
}

/* ---------------------------------------------------------------------- */
/* INIT                                                                    */
/* ---------------------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  const analisis = cargarAnalisis();
  if (!analisis) {
    window.location.href = '/analizar';
    return;
  }

  const { cv, matching, fecha } = analisis;

  renderPremiumStrip('#premium-strip-target');
  renderContextBar(cv, fecha);
  initSidebarNav();

  renderResumen(cv, matching);
  renderPanorama(matching);
  renderRadar(matching);
  renderBrecha(matching);
  renderCursos(matching);
  renderHacks();
  renderFuturo(matching);
  renderEmpleadores(matching);

  document.querySelectorAll('#radar-filters button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#radar-filters button').forEach(b => b.setAttribute('aria-pressed', 'false'));
      btn.setAttribute('aria-pressed', 'true');
      renderRadar(matching, btn.dataset.sort);
    });
  });
});
