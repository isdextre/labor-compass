/* ============================================================================
   state.js — Persistencia ligera de la demo (localStorage)
   ============================================================================
   No hay backend de usuarios/pagos en esta versión de hackathon. Todo lo que
   necesita "recordarse" entre pantallas (perfil demo activo, prueba Premium,
   cursos guardados, hacks completados, modo mentor, reservas, candidatos
   guardados) vive aquí, en el navegador. Un solo objeto, una sola clave.
   ========================================================================= */

const PROXIMO_STATE_KEY = 'proximo_demo_state_v1';
const ANALYSIS_STORAGE_KEY = 'proximo_last_analysis_v1'; // usado por upload.js (escribe) y results.js (lee)

const DEFAULT_STATE = {
  currentCvId: 'USER_006', // Técnico de mantenimiento en minería, Arequipa — persona flagship de la demo
  premiumTrialActive: true,
  trialEndsAt: null,
  savedCourses: [],
  completedHacks: [],
  mentorModeActive: false,
  mentorProfile: null,
  bookings: [],
  savedCandidates: [],
};
function obtenerUserId() {
  let userId = localStorage.getItem('proximo_user_id');
  if (!userId) {
    userId = 'USER_' + Math.random().toString(36).substring(2, 10);
    localStorage.setItem('proximo_user_id', userId);
  }
  return userId;
}

function obtenerPerfilActual() {
  return {
    userId: obtenerUserId(),
    nombre: localStorage.getItem('proximo_nombre'),
    rol: localStorage.getItem('proximo_rol')
  };
}

function ProximoState() {
  function read() {
    try {
      const raw = localStorage.getItem(PROXIMO_STATE_KEY);
      if (!raw) return { ...DEFAULT_STATE };
      return { ...DEFAULT_STATE, ...JSON.parse(raw) };
    } catch (err) {
      return { ...DEFAULT_STATE };
    }
  }

  function write(state) {
    try {
      localStorage.setItem(PROXIMO_STATE_KEY, JSON.stringify(state));
    } catch (err) {
      /* localStorage no disponible (modo privado, etc.) — la demo sigue
         funcionando en memoria durante la sesión actual. */
    }
  }

  function update(patchFn) {
    const current = read();
    const next = patchFn(current) || current;
    write(next);
    return next;
  }

  function reset() {
    write({ ...DEFAULT_STATE });
  }

 

  return { read, write, update, reset };
}

const proximoState = ProximoState();
