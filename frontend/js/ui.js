// Utilidades de pantalla compartidas por todas las páginas.

let temporizadorAviso;

/** Muestra un aviso abajo de la pantalla durante 3 segundos. */
export function mostrarAviso(texto) {
  let aviso = document.getElementById('aviso');
  if (!aviso) {
    aviso = document.createElement('div');
    aviso.id = 'aviso';
    aviso.className = 'aviso';
    aviso.setAttribute('role', 'status');
    document.body.appendChild(aviso);
  }
  aviso.textContent = texto;
  aviso.classList.add('visible');
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => aviso.classList.remove('visible'), 3000);
}

/**
 * Crea un elemento HTML. Los textos se asignan con textContent (nunca como HTML),
 * así un nombre con caracteres como <script> se muestra tal cual y no se ejecuta.
 * Ejemplo: crear('span', {className: 'chip', texto: 'MESERO'})
 */
export function crear(etiqueta, { className, texto, ...atributos } = {}, hijos = []) {
  const elemento = document.createElement(etiqueta);
  if (className) elemento.className = className;
  if (texto !== undefined) elemento.textContent = texto;
  for (const [nombre, valor] of Object.entries(atributos)) elemento.setAttribute(nombre, valor);
  for (const hijo of hijos) elemento.appendChild(hijo);
  return elemento;
}

/** Iniciales para el círculo de la lista, por ejemplo "AV". */
export function iniciales(nombre, apellido) {
  return `${nombre[0] ?? ''}${apellido[0] ?? ''}`.toUpperCase();
}


/** Formatos colombianos para mostrar datos: dinero, cantidades y fechas. */
export const formato = {
  /** 181500 -> "$ 181.500" */
  dinero: (valor) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency', currency: 'COP', maximumFractionDigits: 0,
    }).format(valor),
  /** 12.5 -> "12,5" */
  cantidad: (valor) => new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 }).format(valor),
  /** "2026-10-20" o "2026-10-17T15:30:00" -> "20 oct 2026" */
  fecha: (iso) => {
    if (!iso) return '—';
    // Una fecha sin hora se toma como hora local (si no, el navegador la corre un día)
    const fecha = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
    return fecha.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
  },
};

// Animación de entrada de la pantalla: dura solo los primeros segundos (ver .entrando en estilos.css),
// así las listas que se actualizan solas después no vuelven a animarse.
document.documentElement.classList.add('entrando');
setTimeout(() => document.documentElement.classList.remove('entrando'), 2500);

// =====================================================================
//  Ventanas (dialog): cierre animado, tocar afuera para cerrar y, en el celular,
//  deslizar la hoja hacia abajo para cerrarla. Aplica a todas las pantallas.
// =====================================================================

const sinMovimiento = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const esCelular = () => matchMedia('(max-width: 600px)').matches;

const cerrarNativo = HTMLDialogElement.prototype.close;
const abrirNativo = HTMLDialogElement.prototype.showModal;

/** Cierra con animación (la hoja baja en el celular, la ventana se desvanece en el computador). */
HTMLDialogElement.prototype.close = function cerrarAnimado(valor) {
  if (!this.open || this.classList.contains('cerrando') || sinMovimiento()) {
    cerrarNativo.call(this, valor);
    return;
  }
  this.classList.add('cerrando');
  const terminar = () => {
    clearTimeout(this.temporizadorCierre);
    if (!this.classList.contains('cerrando')) return; // se volvió a abrir mientras se cerraba
    this.classList.remove('cerrando');
    this.style.removeProperty('--desde');
    this.style.transform = '';
    cerrarNativo.call(this, valor);
  };
  this.addEventListener('animationend', terminar, { once: true });
  this.temporizadorCierre = setTimeout(terminar, 350); // por si el navegador no anima
};

/** Si una ventana se vuelve a abrir mientras se cerraba, el cierre se cancela. */
HTMLDialogElement.prototype.showModal = function abrirSinChocar() {
  if (this.classList.contains('cerrando')) {
    clearTimeout(this.temporizadorCierre);
    this.classList.remove('cerrando');
    this.style.removeProperty('--desde');
    this.style.transform = '';
    if (this.open) return;
  }
  abrirNativo.call(this);
};

function prepararVentana(dialogo) {
  // Tocar la zona oscura de afuera cierra la ventana (igual que el botón Cancelar o Cerrar)
  dialogo.addEventListener('click', (evento) => {
    if (evento.target !== dialogo) return;
    const r = dialogo.getBoundingClientRect();
    const afuera = evento.clientX < r.left || evento.clientX > r.right
      || evento.clientY < r.top || evento.clientY > r.bottom;
    if (afuera) dialogo.close();
  });

  // Celular: deslizar hacia abajo desde la barrita (o con el contenido arriba del todo)
  let inicioY = null;
  let inicioT = 0;
  let distancia = 0;
  let arrastrando = false;

  dialogo.addEventListener('touchstart', (evento) => {
    inicioY = null;
    if (!esCelular() || evento.touches.length > 1) return;
    if (evento.target.closest('input, select, textarea, [contenteditable]')) return;
    const toque = evento.touches[0];
    const enLaBarrita = toque.clientY - dialogo.getBoundingClientRect().top < 56;
    if (!enLaBarrita && dialogo.scrollTop > 0) return; // está leyendo más abajo: es un scroll normal
    inicioY = toque.clientY;
    inicioT = performance.now();
    distancia = 0;
    arrastrando = false;
  }, { passive: true });

  dialogo.addEventListener('touchmove', (evento) => {
    if (inicioY === null) return;
    distancia = evento.touches[0].clientY - inicioY;
    if (!arrastrando && distancia > 8) {
      arrastrando = true;
      dialogo.classList.add('arrastrando');
    }
    if (!arrastrando) return;
    evento.preventDefault(); // mientras se arrastra, la hoja se mueve en vez de hacer scroll
    dialogo.style.transform = `translateY(${Math.max(0, distancia)}px)`;
  }, { passive: false });

  const soltar = () => {
    if (inicioY === null) return;
    inicioY = null;
    if (!arrastrando) return;
    arrastrando = false;
    dialogo.classList.remove('arrastrando');
    const velocidad = distancia / Math.max(1, performance.now() - inicioT); // px por ms
    const alto = dialogo.getBoundingClientRect().height;
    if (distancia > alto * 0.25 || (velocidad > 0.6 && distancia > 40)) {
      navigator.vibrate?.(12); // un toque cortito en los celulares que lo permiten
      dialogo.style.setProperty('--desde', `${Math.max(0, distancia)}px`);
      dialogo.close();
    } else {
      dialogo.style.transform = ''; // no llegó lejos: vuelve a su lugar (con transición)
    }
  };
  dialogo.addEventListener('touchend', soltar);
  dialogo.addEventListener('touchcancel', soltar);
}

document.querySelectorAll('dialog').forEach(prepararVentana);

// =====================================================================
//  Efecto de onda al tocar botones, tarjetas, mesas y filas
// =====================================================================

const CON_ONDA = '.boton-principal, .boton-texto, .tarjeta-modulo, .mesa, .fila.editable, .chip.filtro';

document.addEventListener('pointerdown', (evento) => {
  const elemento = evento.target.closest(CON_ONDA);
  if (!elemento || elemento.disabled || sinMovimiento()) return;
  const r = elemento.getBoundingClientRect();
  const tamano = Math.max(r.width, r.height) * 2;
  const onda = document.createElement('span');
  onda.className = 'onda';
  onda.style.width = onda.style.height = `${tamano}px`;
  onda.style.left = `${evento.clientX - r.left - tamano / 2}px`;
  onda.style.top = `${evento.clientY - r.top - tamano / 2}px`;
  elemento.appendChild(onda);
  onda.addEventListener('animationend', () => onda.remove(), { once: true });
});
