// Utilidades de pantalla compartidas por todas las páginas.

let temporizadorAviso;

/** Palomita en SVG que se dibuja sola (ver .aviso-palomita en estilos.css). */
function palomita() {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', 'aviso-palomita');
  svg.setAttribute('aria-hidden', 'true');
  const circulo = document.createElementNS(ns, 'circle');
  circulo.setAttribute('cx', '12');
  circulo.setAttribute('cy', '12');
  circulo.setAttribute('r', '10');
  const trazo = document.createElementNS(ns, 'path');
  trazo.setAttribute('d', 'M7 12.5l3.2 3.2L17 9');
  svg.append(circulo, trazo);
  return svg;
}

/** Muestra un aviso abajo de la pantalla durante 3 segundos. tipo: 'exito' (palomita) o 'error'. */
export function mostrarAviso(texto, tipo = '') {
  let aviso = document.getElementById('aviso');
  if (!aviso) {
    aviso = document.createElement('div');
    aviso.id = 'aviso';
    aviso.className = 'aviso';
    aviso.setAttribute('role', 'status');
    document.body.appendChild(aviso);
  }
  const visible = aviso.classList.contains('visible');
  aviso.className = ['aviso', tipo, visible ? 'visible' : ''].filter(Boolean).join(' ');
  const icono = tipo === 'exito' ? [palomita()]
    : tipo === 'error' ? [crear('span', { className: 'icono aviso-icono', texto: 'error', 'aria-hidden': 'true' })] : [];
  aviso.replaceChildren(...icono, crear('span', { texto }));
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

/** Quita tildes y mayúsculas para buscar: así "limon" encuentra "Limón". */
export function normalizar(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

/**
 * Cambia el contenido de una lista sin saltos (se usa igual que replaceChildren).
 * Cada fila se reconoce por su data-clave o, si no la trae, por su texto: las que ya estaban
 * y no cambiaron se quedan quietas, las nuevas aparecen con un fundido corto y las que traen
 * la misma clave con otra data-version (por ejemplo otro stock) se iluminan un momento.
 */
export function pintarSuave(contenedor, ...filas) {
  filas = filas.flat();
  const clave = (el) => el.dataset?.clave ?? el.textContent;
  const antes = new Map([...contenedor.children].map((el) => [clave(el), el.dataset.version]));
  let nuevas = 0;
  for (const fila of filas) {
    if (!(fila instanceof HTMLElement)) continue;
    let clase = null;
    if (!antes.has(clave(fila))) clase = 'nueva';
    else if (antes.get(clave(fila)) !== fila.dataset.version) clase = 'cambiada';
    if (!clase) continue;
    if (clase === 'nueva') fila.style.setProperty('--i', Math.min(nuevas++, 8)); // cascada corta
    fila.classList.add(clase);
    fila.addEventListener('animationend', () => fila.classList.remove(clase), { once: true });
  }
  contenedor.classList.remove('actualizando');
  contenedor.replaceChildren(...filas);
}

/**
 * Al recargar una lista: si ya tiene filas se atenúan mientras llegan los datos (sin vaciarla)
 * y devuelve false; si está vacía devuelve true para que la pantalla muestre "Cargando…".
 */
export function empezarCarga(contenedor) {
  if (contenedor.children.length) {
    contenedor.classList.add('actualizando');
    setTimeout(() => contenedor.classList.remove('actualizando'), 8000); // si la carga falló, no queda atenuada
    return false;
  }
  return true;
}

/**
 * Muestra el bloque #estado en lugar de la lista: cargando, lista vacía o error.
 * opciones: { icono, detalle, accion: { texto, icono, alHacer }, reintentar }.
 * Con un ícono se ve como estado vacío (ícono grande, mensaje y botón para crear el primero).
 */
export function mostrarEstado(texto, { icono = '', detalle = '', accion = null, reintentar = false, cargando = false } = {}) {
  const estado = document.getElementById('estado');
  // Cargando: filas «esqueleto» con un brillo que pasa, en vez del texto solo
  let esqueleto = estado.querySelector('.esqueleto');
  if (cargando && !esqueleto) {
    esqueleto = crear('div', { className: 'esqueleto', 'aria-hidden': 'true' },
      [1, 2, 3, 4].map(() => crear('div', { className: 'esqueleto-fila' }, [
        crear('span', { className: 'esqueleto-circulo' }),
        crear('span', { className: 'esqueleto-lineas' }, [crear('i'), crear('i')]),
      ])));
    estado.prepend(esqueleto);
  }
  if (esqueleto) esqueleto.hidden = !cargando;
  estado.classList.toggle('cargando', cargando);
  const botonReintentar = document.getElementById('reintentar');
  const conIcono = icono || (reintentar ? 'cloud_off' : '');
  // El ícono, el detalle y el botón se crean la primera vez que hacen falta
  let simbolo = estado.querySelector('.estado-icono');
  if (!simbolo) {
    simbolo = crear('span', { className: 'icono estado-icono', 'aria-hidden': 'true' });
    estado.prepend(simbolo);
  }
  let explicacion = estado.querySelector('.estado-detalle');
  if (!explicacion) {
    explicacion = crear('p', { className: 'estado-detalle' });
    document.getElementById('estado-texto').after(explicacion);
  }
  simbolo.textContent = conIcono;
  simbolo.hidden = !conIcono;
  explicacion.textContent = detalle;
  explicacion.hidden = !detalle;
  document.getElementById('estado-texto').textContent = texto;
  estado.querySelector('.estado-accion')?.remove();
  if (accion) {
    const boton = crear('button', { type: 'button', className: 'boton-principal estado-accion' }, [
      crear('span', { className: 'icono', texto: accion.icono ?? 'add', 'aria-hidden': 'true' }),
      document.createTextNode(` ${accion.texto}`),
    ]);
    boton.addEventListener('click', accion.alHacer);
    estado.insertBefore(boton, botonReintentar);
  }
  botonReintentar.hidden = !reintentar;
  estado.classList.toggle('vacio', Boolean(conIcono));
  estado.hidden = false;
}

/** Lleva un número de su valor anterior al nuevo en un instante, como un contador. */
export function contarHasta(elemento, valor, formatear = String) {
  const desde = Number(elemento.dataset.valor ?? 0);
  elemento.dataset.valor = valor;
  if (desde === valor || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    elemento.textContent = formatear(valor);
    return;
  }
  const inicio = performance.now();
  const paso = (ahora) => {
    if (elemento.dataset.valor !== String(valor)) return; // llegó un valor más nuevo: ese manda
    const avance = Math.min((ahora - inicio) / 500, 1);
    const suave = 1 - (1 - avance) ** 3; // frena al final
    elemento.textContent = formatear(avance < 1 ? Math.round(desde + (valor - desde) * suave) : valor);
    if (avance < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

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

const CON_ONDA = '.boton-principal, .boton-texto, .tarjeta-modulo, .mesa, .fila.editable, .chip.filtro, .plato, .tarjeta-hoy';

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

// =====================================================================
//  Pestañas: la línea de la pestaña elegida se desliza hasta la nueva en vez de saltar
// =====================================================================

function prepararPestanas(barra) {
  const indicador = crear('span', { className: 'indicador-pestana', 'aria-hidden': 'true' });
  barra.appendChild(indicador);
  let primera = true;
  const mover = () => {
    if (!barra.contains(indicador)) barra.appendChild(indicador); // la pantalla volvió a pintar las pestañas
    const elegida = barra.querySelector('[aria-selected="true"]');
    if (!elegida) return;
    if (primera) indicador.style.transition = 'none'; // la primera vez aparece en su sitio
    indicador.style.width = `${elegida.offsetWidth}px`;
    indicador.style.transform = `translateX(${elegida.offsetLeft}px)`;
    if (primera) {
      void indicador.offsetWidth;
      indicador.style.transition = '';
      primera = false;
    }
    if (barra.scrollWidth > barra.clientWidth) elegida.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
  };
  new MutationObserver(mover).observe(barra, { subtree: true, childList: true, attributes: true, attributeFilter: ['aria-selected'] });
  addEventListener('resize', mover);
  document.fonts?.ready.then(mover);
  mover();
}

document.querySelectorAll('.pestanas').forEach(prepararPestanas);

// =====================================================================
//  Tarjetas con relieve: se inclinan hacia el mouse y un brillo lo sigue.
//  Solo con mouse (en el celular no hay "pasar por encima") y si no se pidió menos movimiento.
// =====================================================================

const TARJETAS_RELIEVE = '.tarjeta-modulo, .mesa, .tarjeta-resumen';

if (matchMedia('(hover: hover) and (pointer: fine)').matches && !sinMovimiento()) {
  let actual = null;
  const soltar = () => {
    if (!actual) return;
    actual.classList.remove('relieve');
    actual.style.removeProperty('--rx');
    actual.style.removeProperty('--ry');
    actual = null;
  };
  document.addEventListener('pointermove', (evento) => {
    const tarjeta = evento.target.closest?.(TARJETAS_RELIEVE);
    if (tarjeta !== actual) soltar();
    if (!tarjeta) return;
    actual = tarjeta;
    const caja = tarjeta.getBoundingClientRect();
    const x = (evento.clientX - caja.left) / caja.width; // 0 a 1
    const y = (evento.clientY - caja.top) / caja.height;
    tarjeta.classList.add('relieve');
    tarjeta.style.setProperty('--rx', `${(0.5 - y) * 8}deg`);
    tarjeta.style.setProperty('--ry', `${(x - 0.5) * 10}deg`);
    tarjeta.style.setProperty('--mx', `${x * 100}%`);
    tarjeta.style.setProperty('--my', `${y * 100}%`);
  });
  document.addEventListener('pointerleave', soltar);
}

// =====================================================================
//  Paneles que aparecen al hacer scroll: los que se pintan fuera de la vista entran
//  cuando llegan a ella (menú, ventas y reportes vuelven a pintar sus paneles).
// =====================================================================

if (!sinMovimiento() && 'IntersectionObserver' in window) {
  const vigia = new IntersectionObserver((entradas) => {
    for (const entrada of entradas) {
      if (!entrada.isIntersecting) continue;
      entrada.target.classList.add('revelado');
      vigia.unobserve(entrada.target);
    }
  }, { rootMargin: '0px 0px -40px 0px' });
  const preparar = (panel) => {
    if (panel.dataset.revelar) return;
    panel.dataset.revelar = '1';
    if (panel.getBoundingClientRect().top < innerHeight) return; // ya se ve: no se esconde
    panel.classList.add('por-revelar');
    vigia.observe(panel);
  };
  const buscar = (raiz) => {
    if (!(raiz instanceof Element)) return;
    if (raiz.matches('main .panel')) preparar(raiz);
    raiz.querySelectorAll('main .panel').forEach(preparar);
  };
  new MutationObserver((cambios) => cambios.forEach((c) => c.addedNodes.forEach(buscar)))
    .observe(document.body, { childList: true, subtree: true });
  buscar(document.body);
}
