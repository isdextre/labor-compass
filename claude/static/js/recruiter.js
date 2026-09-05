/* ============================================================================
   recruiter.js — Módulo de reclutador: matching semántico TF-IDF real contra
   un pool de candidatos de demostración (ver claude/app.py /api/recruiter/match).
   ========================================================================= */

function renderCandidateRow(candidato, guardado) {
  return `
    <div class="candidate-row">
      <div>
        <p style="font-weight:700;">${candidato.nombre}</p>
        <p class="text-sm text-muted">${candidato.ocupacion_actual} · ${candidato.ubicacion} · ${candidato.experiencia_años} años</p>
        <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px;">
          ${candidato.skills.map(s => `<span class="chip">${s}</span>`).join('')}
        </div>
        <p class="text-xs text-muted" style="margin-top:8px;">Disponibilidad: ${candidato.disponibilidad}</p>
      </div>
      <div class="candidate-compat">
        <p class="candidate-compat-value">${candidato.compatibilidad_pct}%</p>
        <p class="text-xs text-muted">similitud de texto</p>
        <div class="btn-group" style="justify-content:flex-end; margin-top:8px;">
          <button class="btn btn-secondary btn-sm" onclick='showInfoModal({title:"${candidato.nombre}", body:"Perfil de demostración. En una versión con datos reales, aquí se mostraría el CV completo del candidato."})'>Ver perfil</button>
          <button class="btn btn-primary btn-sm" data-cand-id="${candidato.id}" onclick='toggleGuardado(${JSON.stringify(candidato).replace(/'/g, "&#39;")}, this)'>${guardado ? '★ Guardado' : 'Guardar'}</button>
        </div>
      </div>
    </div>
  `;
}

async function ejecutarMatching() {
  const titulo = document.getElementById('rec-titulo').value.trim();
  const descripcion = document.getElementById('rec-descripcion').value.trim();
  const processing = document.getElementById('rec-processing');
  const errorBox = document.getElementById('rec-error');
  const results = document.getElementById('rec-results');
  const methodNote = document.getElementById('rec-method-note');

  errorBox.hidden = true;
  methodNote.hidden = true;
  results.innerHTML = '';

  if (!descripcion) {
    errorBox.hidden = false;
    errorBox.textContent = 'Escribe una descripción del puesto antes de buscar candidatos.';
    return;
  }

  processing.hidden = false;

  try {
    const data = await apiPost('/api/recruiter/match', { titulo_puesto: titulo, descripcion });
    processing.hidden = true;

    if (!data.candidatos.length) {
      results.innerHTML = `<div class="empty-state"><h3>Sin coincidencias</h3><p>No encontramos candidatos para esta descripción en el pool de demostración.</p></div>`;
      return;
    }

    methodNote.hidden = false;
    methodNote.textContent = data.metodo;

    const state = proximoState.read();
    results.innerHTML = data.candidatos
      .map(c => renderCandidateRow(c, state.savedCandidates.some(sc => sc.id === c.id)))
      .join('');
  } catch (err) {
    processing.hidden = true;
    errorBox.hidden = false;
    errorBox.textContent = `No se pudo ejecutar el matching: ${err.message}`;
  }
}

function toggleGuardado(candidato, btn) {
  const next = proximoState.update(s => {
    const yaGuardado = s.savedCandidates.some(c => c.id === candidato.id);
    const savedCandidates = yaGuardado
      ? s.savedCandidates.filter(c => c.id !== candidato.id)
      : [...s.savedCandidates, candidato];
    return { ...s, savedCandidates };
  });
  const guardado = next.savedCandidates.some(c => c.id === candidato.id);
  btn.textContent = guardado ? '★ Guardado' : 'Guardar';
  showToast(guardado ? 'Candidato guardado' : 'Candidato quitado de guardados');
  renderGuardados();
}

function renderGuardados() {
  const state = proximoState.read();
  const el = document.getElementById('rec-saved');
  if (!state.savedCandidates.length) {
    el.innerHTML = `<p class="text-sm text-muted">Todavía no has guardado candidatos.</p>`;
    return;
  }
  el.innerHTML = state.savedCandidates.map(c => renderCandidateRow(c, true)).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-buscar-candidatos').addEventListener('click', ejecutarMatching);
  renderGuardados();
});
