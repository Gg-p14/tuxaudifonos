/* Utilidades compartidas: API, sesión, carrito, encabezado y pie. */
const $ = (s, r = document) => r.querySelector(s);
const money = (n) => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(n || 0));
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const qs = (k) => new URLSearchParams(location.search).get(k);
const fechaMX = (f) => new Date(f).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });

async function api(url, opts = {}) {
  const r = await fetch('/api' + url, { credentials: 'same-origin', ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) } });
  let d = {};
  try { d = await r.json(); } catch {}
  if (!r.ok) {
    const msg = Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join('. ') : (d.detail || 'Ocurrió un error.');
    const e = new Error(msg); e.status = r.status; throw e;
  }
  return d;
}

function toast(msg) {
  const t = $('#toast'); if (!t) return alert(msg);
  t.textContent = msg; t.classList.add('show');
  clearTimeout(window._tt); window._tt = setTimeout(() => t.classList.remove('show'), 2600);
}
function aviso(el, texto, tipo = '') {
  if (!el) return;
  el.textContent = texto; el.className = 'notice ' + tipo;
  if (!texto) el.classList.add('hidden');
}
function irA(ruta) { location.href = ruta; }

/* ---------- Sesión ---------- */
let _usuario;
async function usuario(forzar = false) {
  if (_usuario !== undefined && !forzar) return _usuario;
  try { _usuario = (await api('/auth/me')).usuario; } catch { _usuario = null; }
  return _usuario;
}
async function exigirSesion() {
  const u = await usuario();
  if (!u) { location.href = '/iniciar-sesion?next=' + encodeURIComponent(location.pathname + location.search); return null; }
  return u;
}

/* ---------- Carrito (localStorage: {id_audifono, nombre, precio, imagen, cantidad, marca, existencias}) ---------- */
const CART_KEY = 'tux_carrito_v2';
const carrito = {
  leer() { try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); } catch { return []; } },
  guardar(items) { localStorage.setItem(CART_KEY, JSON.stringify(items)); this.actualizarContador(); window.dispatchEvent(new Event('carrito')); },
  agregar(prod, cantidad = 1) {
    const items = this.leer();
    const it = items.find((x) => x.id_audifono === prod.id_audifono);
    const tope = Math.min(20, prod.existencias);
    if (it) it.cantidad = Math.min(tope, it.cantidad + cantidad);
    else items.push({ id_audifono: prod.id_audifono, nombre: prod.nombre, marca: prod.marca, precio: prod.precio,
                      imagen: prod.imagen, existencias: prod.existencias, cantidad: Math.min(tope, cantidad) });
    this.guardar(items);
  },
  cambiar(id, delta) {
    const items = this.leer().map((x) => x.id_audifono === id ? { ...x, cantidad: Math.max(1, Math.min(x.existencias, 20, x.cantidad + delta)) } : x);
    this.guardar(items);
  },
  quitar(id) { this.guardar(this.leer().filter((x) => x.id_audifono !== id)); },
  vaciar() { this.guardar([]); },
  total() { return this.leer().reduce((n, x) => n + Number(x.precio) * x.cantidad, 0); },
  piezas() { return this.leer().reduce((n, x) => n + x.cantidad, 0); },
  actualizarContador() { const el = $('#cart-count'); if (el) el.textContent = this.piezas(); },
};
const imgDe = (p) => p.imagen
  ? `<img src="${esc(p.imagen)}" alt="${esc(p.nombre)}" loading="lazy">`
  : `<div class="ph">${esc((p.nombre || 'T')[0])}</div>`;

/* ---------- Encabezado y pie ---------- */
async function montarLayout() {
  const u = await usuario();
  let cats = [];
  try { cats = (await api('/categorias')).categorias; } catch {}
  const path = location.pathname;
  const on = (r) => (path === r ? 'on' : '');
  const admin = u && u.rol === 'admin' ? `<a class="${on('/admin')}" href="/admin">Administración</a>` : '';
  $('#site-header').innerHTML = `
  <header class="top"><div class="bar">
    <a class="brand" href="/"><b>t</b>tuxaudifonos</a>
    <nav class="nav">
      <a class="${on('/')}" href="/">Catálogo</a>
      ${cats.map((c) => `<a href="/?categoria=${esc(c.slug)}">${esc(c.nombre)}</a>`).join('')}
    </nav>
    <div class="right">
      ${u ? `<a href="/pedidos">Pedidos</a><a href="/perfil">Mi cuenta</a>${admin}<a href="#" id="salir">Salir</a>`
          : `<a href="/iniciar-sesion">Iniciar sesión</a><a class="btn chico" href="/registro">Crear cuenta</a>`}
      <a href="/carrito" aria-label="Carrito">Carrito <span class="badge" id="cart-count">0</span></a>
    </div>
  </div></header>
  <div id="toast"></div>`;
  $('#salir')?.addEventListener('click', async (e) => {
    e.preventDefault(); await api('/auth/logout', { method: 'POST' }); _usuario = null; location.href = '/';
  });
  carrito.actualizarContador();
  window.addEventListener('carrito', () => carrito.actualizarContador());
}
document.addEventListener('DOMContentLoaded', montarLayout);
