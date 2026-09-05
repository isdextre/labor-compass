/* ============================================================================
   mentors.js — Catálogo de mentores, activación de modo mentor, reserva
   simulada y dashboard de comisiones. Todo vive en localStorage: no hay
   backend de pagos ni de cuentas en esta versión.
   ========================================================================= */

const COMISION_PLATAFORMA_PCT = 15;
const HORARIOS_DEMO = ['Hoy 4:00 pm', 'Mañana 10:00 am', 'Mañana 6:00 pm', 'Pasado mañana 2:00 pm'];

function initMentorTabs() {
  const tabs = document.querySelectorAll('.tab-btn[data-mpanel]');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.setAttribute('aria-selected', 'false'));
      tab.setAttribute('aria-selected', 'true');
      document.querySelectorAll('[data-mpanel-content]').forEach(p => p.hidden = true);
      document.getElementById(tab.dataset.mpanel).hidden = false;
    });
  });
}

function todosLosMentores() {
  const state = proximoState.read();
  const propio = state.mentorModeActive && state.mentorProfile ? [state.mentorProfile] : [];
  return [...propio, ...MENTORS_DEMO];
}

function initFiltros() {
  const mentores = todosLosMentores();
  const temaSelect = document.getElementById('mf-tema');
  const regionSelect = document.getElementById('mf-region');

  const temas = [...new Set(mentores.map(m => m.tema))];
  const regiones = [...new Set(mentores.map(m => m.region))];
  temas.forEach(t => temaSelect.appendChild(new Option(t, t)));
  regiones.forEach(r => regionSelect.appendChild(new Option(r, r)));

  [temaSelect, regionSelect, document.getElementById('mf-precio')].forEach(sel => {
    sel.addEventListener('change', renderMentorGrid);
  });
}

function renderMentorGrid() {
  const tema = document.getElementById('mf-tema').value;
  const region = document.getElementById('mf-region').value;
  const precioMax = document.getElementById('mf-precio').value;

  let mentores = todosLosMentores();
  if (tema) mentores = mentores.filter(m => m.tema === tema);
  if (region) mentores = mentores.filter(m => m.region === region);
  if (precioMax) mentores = mentores.filter(m => m.precio <= Number(precioMax));

  const grid = document.getElementById('mentors-grid');

  if (!mentores.length) {
    grid.innerHTML = `<div class="empty-state"><h3>No hay mentores con estos filtros</h3><p>Prueba quitando alguno de los filtros seleccionados.</p></div>`;
    return;
  }

  grid.innerHTML = mentores.map(m => `
    <div class="mentor-card">
      <div class="mentor-top">
        <div class="avatar">${m.nombre.split(' ').map(n => n[0]).slice(0,2).join('')}</div>
        <div>
          <p class="mentor-name">${m.nombre}</p>
          <p class="mentor-role">${m.etapa}</p>
        </div>
        ${m.es_demo === false ? '<span class="badge badge-success" style="margin-left:auto;">Tu perfil</span>' : ''}
      </div>
      <p class="mentor-help">${m.ayuda}</p>
      <div class="chip-list" style="display:flex; gap:6px; flex-wrap:wrap;">
        <span class="chip">${m.tema}</span>
        <span class="chip">${m.region}</span>
        <span class="chip">${m.modalidad}</span>
      </div>
      <div class="mentor-footer">
        <div>
          <p class="mentor-price">S/ ${m.precio} · ${m.duracion_min} min</p>
          <p class="text-xs text-muted">Disponible: ${m.disponibilidad}</p>
        </div>
        <button class="btn btn-primary btn-sm" onclick='abrirReserva(${JSON.stringify(m).replace(/'/g, "&#39;")})'>Reservar sesión</button>
      </div>
    </div>
  `).join('');
}

/* ---------------------------------------------------------------------- */
/* RESERVA SIMULADA                                                        */
/* ---------------------------------------------------------------------- */
function abrirReserva(mentor) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="booking-title">
      <div class="modal-head">
        <h3 id="booking-title">Reservar con ${mentor.nombre}</h3>
        <button class="btn btn-tertiary" aria-label="Cerrar" id="booking-close">✕</button>
      </div>
      <div class="field">
        <label for="booking-horario">Horario</label>
        <select id="booking-horario" class="select">
          ${HORARIOS_DEMO.map(h => `<option>${h}</option>`).join('')}
        </select>
      </div>
      <p class="text-sm text-muted">Duración: ${mentor.duracion_min} min · Precio: S/ ${mentor.precio}</p>
      <div class="field">
        <label for="booking-nota">Nota para el mentor (opcional)</label>
        <textarea id="booking-nota" class="textarea" placeholder="Cuéntale brevemente qué necesitas."></textarea>
      </div>
      <div class="alert alert-info text-sm" style="margin-bottom:16px;">No se realizará ningún cobro real: esta es una reserva de demostración.</div>
      <button class="btn btn-primary btn-block" id="booking-confirm">Confirmar reserva</button>
    </div>
  `;
  document.body.appendChild(overlay);

  function close() { overlay.remove(); }
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  overlay.querySelector('#booking-close').addEventListener('click', close);
  document.addEventListener('keydown', function onKey(e) {
    if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onKey); }
  });

  overlay.querySelector('#booking-confirm').addEventListener('click', () => {
    const horario = document.getElementById('booking-horario').value;
    const nota = document.getElementById('booking-nota').value;
    confirmarReserva(mentor, horario, nota);
    close();
  });
}

function confirmarReserva(mentor, horario, nota) {
  const comision = Math.round(mentor.precio * (COMISION_PLATAFORMA_PCT / 100) * 100) / 100;
  const ingresoMentor = Math.round((mentor.precio - comision) * 100) / 100;

  const booking = {
    id: `BOOK_${Date.now()}`,
    mentor: mentor.nombre,
    monto: mentor.precio,
    comision_pct: COMISION_PLATAFORMA_PCT,
    comision_monto: comision,
    ingreso_mentor: ingresoMentor,
    estado: 'Confirmada',
    fecha: new Date().toISOString(),
    horario,
    nota,
  };

  proximoState.update(s => ({ ...s, bookings: [...s.bookings, booking] }));

  showToast(`Reserva confirmada con ${mentor.nombre} — ${horario}`);
  showInfoModal({
    title: 'Reserva confirmada',
    body: `Tu sesión con ${mentor.nombre} quedó agendada para ${horario}. No se realizó ningún cobro real: esto es una demostración. Puedes ver el detalle en "Mis reservas e ingresos".`,
  });

  renderIngresos();
}

/* ---------------------------------------------------------------------- */
/* ACTIVAR MODO MENTOR                                                     */
/* ---------------------------------------------------------------------- */
function initSerMentor() {
  const state = proximoState.read();
  if (state.mentorModeActive && state.mentorProfile) {
    mostrarMentorPublicado(state.mentorProfile);
  }

  document.getElementById('btn-publicar-mentor').addEventListener('click', () => {
    const nombre = document.getElementById('mentor-nombre').value.trim();
    const etapa = document.getElementById('mentor-etapa').value.trim();
    const ayuda = document.getElementById('mentor-ayuda').value.trim();
    const duracion = Number(document.getElementById('mentor-duracion').value);
    const precio = Number(document.getElementById('mentor-precio').value);
    const disponibilidad = document.getElementById('mentor-disponibilidad').value.trim() || 'Por definir';

    if (!nombre || !etapa || !ayuda) {
      showToast('Completa al menos tu nombre, etapa y en qué puedes ayudar.');
      return;
    }

    const perfil = {
      id: 'MENTOR_YO',
      nombre, etapa, ayuda,
      tema: 'General', industria: 'General', region: 'Tu región',
      precio, duracion_min: duracion, disponibilidad,
      modalidad: 'Virtual', es_demo: false,
    };

    proximoState.update(s => ({ ...s, mentorModeActive: true, mentorProfile: perfil }));
    mostrarMentorPublicado(perfil);
    showToast('Tu perfil de mentor está publicado (demo)');
    renderMentorGrid();
  });

  document.getElementById('btn-desactivar-mentor').addEventListener('click', () => {
    proximoState.update(s => ({ ...s, mentorModeActive: false, mentorProfile: null }));
    document.getElementById('mentor-form-view').hidden = false;
    document.getElementById('mentor-published-view').hidden = true;
    renderMentorGrid();
  });
}

function mostrarMentorPublicado(perfil) {
  document.getElementById('mentor-form-view').hidden = true;
  document.getElementById('mentor-published-view').hidden = false;
  document.getElementById('mentor-published-card').innerHTML = `
    <div class="mentor-card">
      <div class="mentor-top">
        <div class="avatar">${perfil.nombre.split(' ').map(n => n[0]).slice(0,2).join('')}</div>
        <div><p class="mentor-name">${perfil.nombre}</p><p class="mentor-role">${perfil.etapa}</p></div>
      </div>
      <p class="mentor-help">${perfil.ayuda}</p>
      <p class="mentor-price">S/ ${perfil.precio} · ${perfil.duracion_min} min · ${perfil.disponibilidad}</p>
    </div>
  `;
}

/* ---------------------------------------------------------------------- */
/* DASHBOARD DE INGRESOS / COMISIONES                                      */
/* ---------------------------------------------------------------------- */
function renderIngresos() {
  const state = proximoState.read();
  const el = document.getElementById('ingresos-content');
  const bookings = state.bookings;

  if (!bookings.length) {
    el.innerHTML = `<div class="empty-state"><h3>Todavía no tienes reservas</h3><p>Cuando reserves o recibas una sesión de mentoría, aparecerá aquí.</p></div>`;
    return;
  }

  const totalMonto = bookings.reduce((sum, b) => sum + b.monto, 0);
  const totalComision = bookings.reduce((sum, b) => sum + b.comision_monto, 0);

  el.innerHTML = `
    <div class="metric-row" style="margin-top:0;">
      <div class="metric-item"><dt>Reservas totales</dt><dd>${bookings.length}</dd></div>
      <div class="metric-item"><dt>Monto total</dt><dd>S/ ${totalMonto.toFixed(2)}</dd></div>
      <div class="metric-item"><dt>Comisión de plataforma (${COMISION_PLATAFORMA_PCT}%)</dt><dd>S/ ${totalComision.toFixed(2)}</dd></div>
      <div class="metric-item"><dt>Estado</dt><dd><span class="badge badge-demo">Sin cobro real</span></dd></div>
    </div>
    <div style="overflow-x:auto;">
      <table class="data-table">
        <thead><tr><th>Mentor</th><th>Horario</th><th>Monto</th><th>Comisión</th><th>Ingreso mentor</th><th>Estado</th></tr></thead>
        <tbody>
          ${bookings.map(b => `
            <tr>
              <td data-label="Mentor">${b.mentor}</td>
              <td data-label="Horario">${b.horario}</td>
              <td data-label="Monto">S/ ${b.monto.toFixed(2)}</td>
              <td data-label="Comisión">S/ ${b.comision_monto.toFixed(2)}</td>
              <td data-label="Ingreso mentor">S/ ${b.ingreso_mentor.toFixed(2)}</td>
              <td data-label="Estado"><span class="badge badge-success">${b.estado}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

document.addEventListener('DOMContentLoaded', () => {
  initMentorTabs();
  initFiltros();
  renderMentorGrid();
  initSerMentor();
  renderIngresos();
});
