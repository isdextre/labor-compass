/* ============================================================================
   nav.js — Menú móvil, toasts y modal informativo compartidos por toda la app
   ========================================================================= */

function initMobileNav() {
  const toggle = document.querySelector('.nav-toggle');
  const mobileNav = document.querySelector('.mobile-nav');
  if (!toggle || !mobileNav) return;

  function close() {
    mobileNav.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-open');
  }
  function open() {
    mobileNav.classList.add('open');
    toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('nav-open');
    const firstLink = mobileNav.querySelector('a, button');
    if (firstLink) firstLink.focus();
  }

  toggle.addEventListener('click', () => {
    const isOpen = mobileNav.classList.contains('open');
    isOpen ? close() : open();
  });

  mobileNav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', close);
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && mobileNav.classList.contains('open')) {
      close();
      toggle.focus();
    }
  });
}

function markActiveNavLink() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a, .mobile-nav a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === path) link.classList.add('active');
  });
}

/* ---------- TOASTS ---------- */
function ensureToastRegion() {
  let region = document.querySelector('.toast-region');
  if (!region) {
    region = document.createElement('div');
    region.className = 'toast-region';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    document.body.appendChild(region);
  }
  return region;
}

function showToast(message, duration = 3200) {
  const region = ensureToastRegion();
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  region.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

/* ---------- MODAL informativo (para acciones aún no implementadas) ---------- */
function showInfoModal({ title, body }) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div class="modal-head">
        <h3 id="modal-title">${title}</h3>
        <button class="btn btn-tertiary" aria-label="Cerrar">✕</button>
      </div>
      <p class="text-muted">${body}</p>
    </div>
  `;
  document.body.appendChild(overlay);

  function close() {
    overlay.remove();
    document.removeEventListener('keydown', onKey);
  }
  function onKey(e) {
    if (e.key === 'Escape') close();
  }
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  overlay.querySelector('button').addEventListener('click', close);
  document.addEventListener('keydown', onKey);
  overlay.querySelector('button').focus();
}

/* ---------- FRANJA PREMIUM (discreta, no invasiva) ---------- */
function renderPremiumStrip(targetSelector) {
  const target = document.querySelector(targetSelector);
  if (!target) return;
  const state = proximoState.read();
  if (!state.premiumTrialActive) {
    target.innerHTML = '';
    return;
  }
  target.innerHTML = `<span class="premium-strip">✦ Prueba Premium activa — acceso completo por tiempo limitado</span>`;
}

document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  markActiveNavLink();
});
