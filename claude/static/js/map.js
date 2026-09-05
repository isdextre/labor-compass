/* ============================================================================
   map.js — Explorador territorial (Leaflet)
   ============================================================================
   Un mismo script sirve dos vistas:
   - "compact": mini mapa de la landing (solo marcadores + popup).
   - "full": página /mapa completa, con panel lateral, filtros y drawer móvil.
   Los datos de las regiones son demostrativos (ver data/territorio_demo.json,
   servido por GET /api/territorio) — se etiquetan como tales en toda la UI.
   ========================================================================= */

function nivelOportunidadColor(nivel) {
  if (nivel === 'alto') return '#059669';
  if (nivel === 'medio') return '#D97706';
  return '#DC2626';
}

function renderRegionDetail(container, region, ajustes) {
  if (!region) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>Selecciona una región</h3>
        <p>Haz clic en un punto del mapa para ver sus datos.</p>
      </div>
    `;
    return;
  }

  const industrias = region.industrias_crecimiento.map(ind => `
    <li class="text-sm" style="display:flex; justify-content:space-between; padding-block:4px;">
      <span>${ind.nombre}</span>
      <span style="color:${ind.variacion_pct >= 0 ? 'var(--color-success)' : 'var(--color-danger)'}; font-weight:700;">
        ${ind.variacion_pct >= 0 ? '+' : ''}${ind.variacion_pct}%
      </span>
    </li>
  `).join('');

  const skills = region.skills_demandados.map(s => `<span class="chip">${s}</span>`).join('');

  const factor = ajustes?.factor ?? 1;
  const vacantesAjustadas = Math.max(1, Math.round(region.vacantes_aproximadas * factor));
  const notaAjuste = ajustes?.activo
    ? `<p class="text-xs text-muted" style="margin-top:6px;">Estimación ajustada (demostrativa) según los filtros de experiencia, modalidad y horizonte seleccionados.</p>`
    : '';

  container.innerHTML = `
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <h3>${region.nombre}</h3>
        <span class="badge badge-demo">Demostrativo</span>
      </div>

      <p class="text-xs text-muted" style="margin-bottom:4px;">Industrias en movimiento</p>
      <ul style="margin-bottom:16px;">${industrias}</ul>

      <p class="text-xs text-muted" style="margin-bottom:6px;">Habilidades más demandadas</p>
      <div class="chip-list" style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:16px;">${skills}</div>

      <div class="metric-row" style="grid-template-columns: repeat(2,1fr); margin-block:12px; padding-block:12px;">
        <div class="metric-item">
          <dt>Vacantes aproximadas</dt>
          <dd>${vacantesAjustadas}</dd>
        </div>
        <div class="metric-item">
          <dt>Salario estimado</dt>
          <dd>S/ ${region.salario_estimado_soles.min}–${region.salario_estimado_soles.max}</dd>
        </div>
        <div class="metric-item">
          <dt>Nivel de oportunidad</dt>
          <dd style="text-transform:capitalize; color:${nivelOportunidadColor(region.nivel_oportunidad)};">${region.nivel_oportunidad}</dd>
        </div>
        <div class="metric-item">
          <dt>Cursos disponibles</dt>
          <dd>${region.cursos_disponibles}</dd>
        </div>
      </div>
      ${notaAjuste}
    </div>
  `;
}

async function initTerritoryMap() {
  const mapEl = document.getElementById('map-canvas');
  if (!mapEl || typeof L === 'undefined') return;

  const mode = mapEl.dataset.mode || 'compact';
  let data;
  try {
    data = await apiGet('/api/territorio');
  } catch (err) {
    mapEl.innerHTML = `<div class="empty-state"><h3>No se pudo cargar el mapa</h3><p>${err.message}</p></div>`;
    return;
  }

  const regiones = data.regiones || [];

  const map = L.map(mapEl, {
    scrollWheelZoom: false,
    zoomControl: mode === 'full',
  }).setView([-9.19, -75.0], mode === 'full' ? 5.2 : 5);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 10,
  }).addTo(map);

  const detailPanel = document.getElementById('map-detail');
  const markers = {};

  regiones.forEach(region => {
    const marker = L.circleMarker([region.lat, region.lon], {
      radius: 10,
      color: nivelOportunidadColor(region.nivel_oportunidad),
      fillColor: nivelOportunidadColor(region.nivel_oportunidad),
      fillOpacity: 0.7,
      weight: 2,
    }).addTo(map);

    marker.bindTooltip(region.nombre, { permanent: false, direction: 'top' });

    marker.on('click', () => {
      if (detailPanel) {
        renderRegionDetail(detailPanel, region);
      } else {
        marker.bindPopup(`<strong>${region.nombre}</strong><br>Nivel de oportunidad: ${region.nivel_oportunidad}<br>Vacantes aprox.: ${region.vacantes_aproximadas}`).openPopup();
      }
    });

    markers[region.id] = marker;
  });

  if (mode === 'full') {
    let regionActiva = regiones[0];
    renderRegionDetail(detailPanel, regionActiva, leerAjustesDemo());
    initMapFilters(regiones, markers, map, {
      onRegionChange: (region) => { regionActiva = region; renderRegionDetail(detailPanel, regionActiva, leerAjustesDemo()); },
      onAjusteChange: () => renderRegionDetail(detailPanel, regionActiva, leerAjustesDemo()),
    });
  }
}

/* Multiplicadores puramente demostrativos: dejan ver que los filtros SÍ
   modifican el contenido, sin fingir que existe una segmentación real por
   experiencia/modalidad/horizonte en el dataset (que no existe). */
const FACTOR_EXPERIENCIA = { '': 1, junior: 0.6, semi: 1, senior: 0.3 };
const FACTOR_MODALIDAD = { '': 1, remoto: 0.4, hibrido: 0.7, presencial: 1 };
const FACTOR_HORIZONTE = { '': 1, '6': 0.6, '12': 1, '24': 1.4 };

function leerAjustesDemo() {
  const experiencia = document.getElementById('filter-experiencia')?.value || '';
  const modalidad = document.getElementById('filter-modalidad')?.value || '';
  const horizonte = document.getElementById('filter-horizonte')?.value || '';
  return {
    experiencia, modalidad, horizonte,
    factor: FACTOR_EXPERIENCIA[experiencia] * FACTOR_MODALIDAD[modalidad] * FACTOR_HORIZONTE[horizonte],
    activo: !!(experiencia || modalidad || horizonte),
  };
}

function initMapFilters(regiones, markers, map, { onRegionChange, onAjusteChange }) {
  const industrias = new Set();
  regiones.forEach(r => r.industrias_crecimiento.forEach(i => industrias.add(i.nombre)));

  const regionSelect = document.getElementById('filter-region');
  if (regionSelect) {
    regiones.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.id;
      opt.textContent = r.nombre;
      regionSelect.appendChild(opt);
    });
    regionSelect.addEventListener('change', () => {
      const region = regiones.find(r => r.id === regionSelect.value);
      if (region) {
        map.flyTo([region.lat, region.lon], 7, { duration: 0.6 });
        onRegionChange(region);
      }
    });
  }

  const industriaSelect = document.getElementById('filter-industria');
  if (industriaSelect) {
    industrias.forEach(nombre => {
      const opt = document.createElement('option');
      opt.value = nombre;
      opt.textContent = nombre;
      industriaSelect.appendChild(opt);
    });
    industriaSelect.addEventListener('change', () => {
      const val = industriaSelect.value;
      regiones.forEach(region => {
        const coincide = !val || region.industrias_crecimiento.some(i => i.nombre === val);
        const marker = markers[region.id];
        if (marker) {
          marker.setStyle({ opacity: coincide ? 1 : 0.15, fillOpacity: coincide ? 0.7 : 0.08 });
        }
      });
    });
  }

  ['filter-experiencia', 'filter-modalidad', 'filter-horizonte'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', onAjusteChange);
  });

  const drawerToggle = document.querySelector('.drawer-toggle');
  const filtersPanel = document.querySelector('.map-filters-panel');
  if (drawerToggle && filtersPanel) {
    drawerToggle.addEventListener('click', () => {
      filtersPanel.classList.toggle('open');
    });
  }
}

document.addEventListener('DOMContentLoaded', initTerritoryMap);
