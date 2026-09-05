/* ============================================================================
   upload.js — Flujo de carga de CV / selección de perfil demo
   ========================================================================= */
let archivoSeleccionado = null
const MAX_FILE_MB = 8; // ANALYSIS_STORAGE_KEY vive en state.js (se comparte con results.js)

function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.setAttribute('aria-selected', 'false'));
      tab.setAttribute('aria-selected', 'true');
      document.querySelectorAll('[role="tabpanel"]').forEach(p => p.hidden = true);
      document.getElementById(tab.dataset.panel).hidden = false;
    });
  });
}

function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const input = document.getElementById('file-input');
  const fileLoaded = document.getElementById('file-loaded');
  const fileError = document.getElementById('file-error');
  const btnAnalizar = document.getElementById('btn-analizar');
  const btnRemove = document.getElementById('btn-remove-file');
  if (!dropzone) return;

  function reset() {
    input.value = '';
    fileLoaded.hidden = true;
    fileError.hidden = true;
    btnAnalizar.disabled = true;
    dropzone.hidden = false;
  }

  function validarYCargar(file) {
    fileError.hidden = true;
    if (!file) return;

    if (file.type !== 'application/pdf') {
      fileError.hidden = false;
      fileError.textContent = 'Solo se aceptan archivos PDF.';
      return;
    }
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      fileError.hidden = false;
      fileError.textContent = `El archivo supera el tamaño máximo de ${MAX_FILE_MB} MB.`;
      return;
    }
    archivoSeleccionado = file;

    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-size').textContent = `${(file.size / 1024).toFixed(0)} KB`;
    fileLoaded.hidden = false;
    dropzone.hidden = true;
    btnAnalizar.disabled = false;
  }

  dropzone.addEventListener('click', () => input.click());
  dropzone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
  });
  input.addEventListener('change', () => validarYCargar(input.files[0]));

  ['dragenter', 'dragover'].forEach(evt => {
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--color-primary)';
    });
  });
  ['dragleave', 'drop'].forEach(evt => {
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--color-border)';
    });
  });
  dropzone.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    validarYCargar(file);
  });

  btnRemove.addEventListener('click', reset);

  btnAnalizar.addEventListener('click', () => ejecutarAnalisisConArchivo(archivoSeleccionado));
}

async function ejecutarAnalisis(cvId) {
  document.getElementById('panel-upload').hidden = true;
  document.getElementById('panel-manual').hidden = true;
  document.querySelector('.tabs').hidden = true;
  const processing = document.getElementById('processing-state');
  const errorBox = document.getElementById('processing-error');
  processing.hidden = false;
  errorBox.hidden = true;

  const steps = processing.querySelectorAll('#processing-steps li');
  steps.forEach(s => s.style.color = '');

  function marcarPaso(n) {
    steps.forEach(s => {
      const step = Number(s.dataset.step);
      if (step < n) { s.style.color = 'var(--color-success)'; s.textContent = '✓ ' + s.textContent.replace('✓ ', ''); }
      if (step === n) { s.style.color = 'var(--color-primary)'; s.style.fontWeight = '700'; }
    });
  }

  try {
    marcarPaso(1);
    const cv = await apiPost('/api/parse-cv', { cv_id: cvId });

    await esperar(500);
    marcarPaso(2);

    await esperar(500);
    marcarPaso(3);
    const matching = await apiPost('/api/matching', {
      ocupacion_actual: cv.ocupacion_actual,
      skills_actuales: cv.skills_identificadas,
    });

    await esperar(400);
    marcarPaso(4);

    await esperar(400);
    marcarPaso(5);
    await esperar(400);

    localStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify({ cv, matching, fecha: new Date().toISOString() }));
    proximoState.update(s => ({ ...s, currentCvId: cvId }));

    window.location.href = '/resultados';
  } catch (err) {
    processing.hidden = true;
    errorBox.hidden = false;
    errorBox.innerHTML = `No pudimos completar el análisis: ${err.message}. <button class="btn btn-tertiary" onclick="location.reload()">Reintentar</button>`;
  }
}
async function ejecutarAnalisisConArchivo(archivo) {
  document.getElementById('panel-upload').hidden = true;
  document.getElementById('panel-manual').hidden = true;
  document.querySelector('.tabs').hidden = true;
  const processing = document.getElementById('processing-state');
  const errorBox = document.getElementById('processing-error');
  processing.hidden = false;
  errorBox.hidden = true;

  const steps = processing.querySelectorAll('#processing-steps li');
  steps.forEach(s => s.style.color = '');

  function marcarPaso(n) {
    steps.forEach(s => {
      const step = Number(s.dataset.step);
      if (step < n) { s.style.color = 'var(--color-success)'; s.textContent = '✓ ' + s.textContent.replace('✓ ', ''); }
      if (step === n) { s.style.color = 'var(--color-primary)'; s.style.fontWeight = '700'; }
    });
  }

  try {
    marcarPaso(1);

    // Subimos el archivo real al nuevo endpoint (form-data, no JSON)
    const formData = new FormData();
    formData.append('cv_file', archivo);
    const respuesta = await fetch('/api/parse-cv-upload', { method: 'POST', body: formData });
    const cv = await respuesta.json();
    if (!respuesta.ok) throw new Error(cv.error || 'No se pudo analizar el CV');

    await esperar(500);
    marcarPaso(2);

    await esperar(500);
    marcarPaso(3);
    const matching = await apiPost('/api/matching', {
      ocupacion_actual: cv.ocupacion_actual,
      skills_actuales: cv.skills_identificadas,
    });

    await esperar(400);
    marcarPaso(4);

    await esperar(400);
    marcarPaso(5);
    await esperar(400);

    localStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify({ cv, matching, fecha: new Date().toISOString() }));
    proximoState.update(s => ({ ...s, currentCvId: cv.user_id || 'PDF_REAL' }));

    window.location.href = '/resultados';
  } catch (err) {
    processing.hidden = true;
    errorBox.hidden = false;
    errorBox.innerHTML = `No pudimos completar el análisis: ${err.message}. <button class="btn btn-tertiary" onclick="location.reload()">Reintentar</button>`;
  }
}
function esperar(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initDropzone();

  const btnManual = document.getElementById('btn-analizar-manual');
  if (btnManual) {
    btnManual.addEventListener('click', () => {
      const cvId = document.getElementById('perfil-demo').value;
      ejecutarAnalisis(cvId);
    });
  }
});
