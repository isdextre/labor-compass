/* ============================================================================
   demo-data.js — Catálogo de mentores de demostración
   ============================================================================
   Nota importante del producto: un mentor NO tiene que ser un "experto"
   certificado. Puede ser un estudiante de universidad ofreciendo una sesión
   corta de orientación en algo que ya domina. Por eso el catálogo mezcla
   perfiles muy distintos a propósito.
   ========================================================================= */

const MENTORS_DEMO = [
  {
    id: 'MENTOR_001',
    nombre: 'Valeria Ponce',
    etapa: 'Estudiante de Derecho, 3er año — UNMSM',
    tema: 'Derecho',
    industria: 'Legal',
    region: 'Lima',
    ayuda: 'Orientación básica sobre trámites laborales, contratos y derechos del trabajador para alguien que recién empieza a averiguar.',
    precio: 15,
    duracion_min: 15,
    disponibilidad: 'Esta semana',
    modalidad: 'Virtual',
    es_demo: true,
  },
  {
    id: 'MENTOR_002',
    nombre: 'Renzo Aguilar',
    etapa: 'Técnico en Energía Solar, 2 años de experiencia',
    tema: 'Energía renovable',
    industria: 'Energía',
    region: 'Arequipa',
    ayuda: 'Cómo es el día a día del trabajo en instalación fotovoltaica y qué certificación conviene sacar primero.',
    precio: 25,
    duracion_min: 20,
    disponibilidad: 'Mañana',
    modalidad: 'Virtual',
    es_demo: true,
  },
  {
    id: 'MENTOR_003',
    nombre: 'Camila Torres',
    etapa: 'Data Analyst Senior — 6 años de experiencia',
    tema: 'Datos y analítica',
    industria: 'Tecnología',
    region: 'Lima',
    ayuda: 'Revisión de portafolio y consejos para tu primera entrevista técnica en análisis de datos.',
    precio: 45,
    duracion_min: 30,
    disponibilidad: 'Próxima semana',
    modalidad: 'Virtual',
    es_demo: true,
  },
  {
    id: 'MENTOR_004',
    nombre: 'Diego Salazar',
    etapa: 'Estudiante de Administración, 4to año — UNSA',
    tema: 'Emprendimiento',
    industria: 'Negocios',
    region: 'Arequipa',
    ayuda: 'Cómo armar un plan simple para un pequeño negocio familiar, desde alguien que está aprendiendo lo mismo en la universidad.',
    precio: 10,
    duracion_min: 15,
    disponibilidad: 'Hoy',
    modalidad: 'Virtual',
    es_demo: true,
  },
];

const HACKS_DEMO = [
  {
    id: 'hack_keyword',
    titulo: 'Añade "mantenimiento preventivo" como palabra clave en tu CV',
    razon: 'Es una de las habilidades más pedidas en las vacantes de energía solar que revisamos.',
    impacto: 'Alto',
    esfuerzo: 'Bajo',
    tiempo: '10 minutos',
    accion: 'Editar mi CV',
  },
  {
    id: 'hack_logro',
    titulo: 'Reescribe un logro usando una métrica concreta',
    razon: 'Un logro con número ("reduje fallas de equipo en 20%") pesa más que una descripción genérica de funciones.',
    impacto: 'Alto',
    esfuerzo: 'Medio',
    tiempo: '20 minutos',
    accion: 'Ver ejemplo',
  },
  {
    id: 'hack_cert',
    titulo: 'Completa una certificación corta de seguridad eléctrica',
    razon: 'Aparece como requisito en la mayoría de vacantes técnicas de energía renovable.',
    impacto: 'Medio',
    esfuerzo: 'Medio',
    tiempo: '1 semana',
    accion: 'Ver cursos',
  },
  {
    id: 'hack_titular',
    titulo: 'Actualiza tu titular profesional',
    razon: '"Técnico de mantenimiento en transición a energía solar" comunica mejor tu dirección que solo tu puesto actual.',
    impacto: 'Medio',
    esfuerzo: 'Bajo',
    tiempo: '5 minutos',
    accion: 'Editar titular',
  },
  {
    id: 'hack_transferible',
    titulo: 'Destaca "trabajo en campo" como habilidad transferible',
    razon: 'Ya la tienes de tu experiencia en minería y es igual de valiosa en instalaciones solares.',
    impacto: 'Medio',
    esfuerzo: 'Bajo',
    tiempo: '5 minutos',
    accion: 'Editar mi CV',
  },
];
