// Utilidades de pantalla compartidas por todas las páginas.

let temporizadorAviso;

/** Atajo para document.getElementById, el mismo en todas las pantallas. */
export const $ = (id) => document.getElementById(id);

/** RF-03.10 Categorías de insumos (también subdividen a los proveedores, RF-02.9). */
export const CATEGORIAS_INSUMO = {
  CARNES: 'Carnes', GRANOS: 'Granos', LACTEOS: 'Lácteos y huevos', FRUTAS_VERDURAS: 'Frutas y verduras',
  BEBIDAS: 'Bebidas', ABARROTES: 'Abarrotes', DESECHABLES: 'Desechables', LIMPIEZA: 'Limpieza',
  MOBILIARIO: 'Mobiliario y menaje', OTROS: 'Otros',
};

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

/**
 * Muestra un aviso abajo de la pantalla durante 3 segundos. tipo: 'exito' (palomita) o 'error'.
 * Suena según el tipo; con { sonido: 'pago' | 'listo' | ... } suena otro, y con { sonido: null }, ninguno.
 */
export function mostrarAviso(texto, tipo = '', { sonido = tipo === 'exito' || tipo === 'error' ? tipo : null } = {}) {
  if (sonido) sonar(sonido);
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
  for (const [nombre, valor] of Object.entries(atributos)) {
    // La política de seguridad (CSP) bloquea el atributo style; por CSSOM sí se permite
    if (nombre === 'style') elemento.style.cssText = valor;
    else elemento.setAttribute(nombre, valor);
  }
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
  // El aviso va después de la lista: así, cuando llegan los datos, la lista ya está en su lugar y no
  // salta hacia arriba al ocultarse el aviso (Lighthouse: estabilidad visual, CLS)
  const lista = estado.nextElementSibling;
  if (lista?.classList.contains('lista')) lista.after(estado);
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

export function prepararVentana(dialogo) {
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

// =====================================================================
//  Ventanas de confirmación con el estilo de StockPot (reemplazan confirm() y prompt())
// =====================================================================

let ventanaPregunta;

/**
 * Abre una ventana con título, texto y los botones Cancelar / Aceptar.
 * Con `campo` agrega una caja de texto. Devuelve una promesa con:
 * - confirmar: true o false;
 * - con campo: el texto escrito ('' si lo deja vacío) o null si cancela.
 */
function preguntar({ titulo, texto = '', aceptar = 'Aceptar', cancelar = 'Cancelar', peligro = false,
  icono = 'help', campo = null }) {
  if (!ventanaPregunta) {
    ventanaPregunta = crear('dialog', { className: 'ventana-pregunta', 'aria-labelledby': 'pregunta-titulo' });
    document.body.appendChild(ventanaPregunta);
    prepararVentana(ventanaPregunta);
  }
  const d = ventanaPregunta;
  const entrada = campo ? crear('input', { id: 'pregunta-campo', autocomplete: 'off', maxlength: '200',
    placeholder: campo }) : null;
  const botonCancelar = crear('button', { type: 'button', className: 'boton-texto', texto: cancelar });
  const botonAceptar = crear('button', { type: 'submit', className: `boton-principal${peligro ? ' peligro' : ''}`,
    texto: aceptar });
  const formulario = crear('form', { method: 'dialog' }, [
    crear('span', { className: `icono pregunta-icono${peligro ? ' peligro' : ''}`, texto: icono, 'aria-hidden': 'true' }),
    crear('h2', { id: 'pregunta-titulo', texto: titulo }),
    ...(texto ? [crear('p', { className: 'pregunta-texto', texto })] : []),
    ...(entrada ? [crear('div', { className: 'campo' }, [entrada])] : []),
    crear('div', { className: 'acciones' }, [botonCancelar, botonAceptar]),
  ]);
  d.replaceChildren(formulario);

  return new Promise((responder) => {
    let respuesta = campo ? null : false;
    botonCancelar.addEventListener('click', () => d.close());
    formulario.addEventListener('submit', (evento) => {
      evento.preventDefault();
      respuesta = campo ? entrada.value.trim() : true;
      d.close();
    });
    d.addEventListener('close', () => responder(respuesta), { once: true });
    d.showModal();
    (entrada || botonAceptar).focus();
  });
}

/** Pregunta sí o no. Ejemplo: if (!await confirmar('¿Anular el pago?', {peligro: true})) return; */
export function confirmar(titulo, opciones = {}) {
  return preguntar({ titulo, ...opciones });
}

/** Pide un texto opcional (por ejemplo el motivo). Devuelve el texto, o null si cancela. */
export function pedirTexto(titulo, opciones = {}) {
  return preguntar({ titulo, campo: 'Escribe aquí (opcional)', ...opciones });
}

// =====================================================================
//  Sonidos: se generan en el navegador (sin archivos de audio) y se pueden silenciar
// =====================================================================

const CLAVE_SONIDO = 'stockpot_sonido';
let audio = null;

function sonidoActivo() {
  try { return localStorage.getItem(CLAVE_SONIDO) !== 'no'; } catch { return true; }
}

/** El navegador no deja sonar hasta que la persona toca la página: el primer toque lo habilita. */
function contexto() {
  if (!audio) {
    try { audio = new AudioContext(); } catch { return null; }
  }
  if (audio.state === 'suspended') audio.resume().catch(() => {});
  return audio;
}
['pointerdown', 'keydown'].forEach((evento) => document.addEventListener(evento, contexto, { once: true, capture: true }));

/** Una nota: frecuencia (Hz), cuándo empieza (s), cuánto dura (s), volumen y forma de onda. */
function nota(ctx, frecuencia, inicio, duracion, volumen = 0.15, forma = 'sine') {
  const osc = ctx.createOscillator();
  const ganancia = ctx.createGain();
  const t = ctx.currentTime + inicio;
  osc.type = forma;
  osc.frequency.setValueAtTime(frecuencia, t);
  ganancia.gain.setValueAtTime(0.0001, t);
  ganancia.gain.exponentialRampToValueAtTime(volumen, t + 0.01);
  ganancia.gain.exponentialRampToValueAtTime(0.0001, t + duracion);
  osc.connect(ganancia).connect(ctx.destination);
  osc.start(t);
  osc.stop(t + duracion + 0.02);
}

const SONIDOS = {
  // Cocina: llegó un pedido nuevo (el timbre de siempre, dos notas)
  pedido: (ctx) => { nota(ctx, 880, 0, 0.3); nota(ctx, 1320, 0.18, 0.3); },
  // Mesero: el pedido está listo para llevar (tres notas que suben, se oye en el salón)
  listo: (ctx) => { nota(ctx, 784, 0, 0.25, 0.18); nota(ctx, 988, 0.12, 0.25, 0.18); nota(ctx, 1319, 0.24, 0.5, 0.2); },
  // Caja: pago registrado (campanita brillante de dos golpes)
  pago: (ctx) => {
    nota(ctx, 1568, 0, 0.12, 0.12, 'triangle');
    nota(ctx, 2093, 0.09, 0.6, 0.16);
    nota(ctx, 4186, 0.09, 0.25, 0.03);
  },
  // Algo salió mal: dos tonos graves cortos
  error: (ctx) => { nota(ctx, 220, 0, 0.16, 0.14, 'triangle'); nota(ctx, 165, 0.14, 0.24, 0.14, 'triangle'); },
  // Guardado con éxito: un clic suave
  exito: (ctx) => { nota(ctx, 1046, 0, 0.12, 0.08); nota(ctx, 1568, 0.05, 0.14, 0.05); },
};

/** Suena 'pedido', 'listo', 'pago', 'error' o 'exito' (si el sonido no está silenciado). */
export function sonar(tipo) {
  if (!sonidoActivo() || !SONIDOS[tipo]) return;
  const ctx = contexto();
  if (!ctx) return;
  try { SONIDOS[tipo](ctx); } catch { /* sin audio: queda solo el aviso en pantalla */ }
}

/** Botón de la barra para silenciar o activar los sonidos (la preferencia se recuerda en este equipo). */
function prepararBotonSonido() {
  const barra = document.querySelector('header.barra');
  if (!barra) return;
  let boton = document.getElementById('sonido');
  if (!boton) {
    boton = crear('button', { type: 'button', className: 'boton-icono', id: 'sonido' },
      [crear('span', { className: 'icono', 'aria-hidden': 'true' })]);
    const antesDe = barra.querySelector('#mi-pin, #cerrar-sesion');
    if (antesDe) barra.insertBefore(boton, antesDe); else barra.appendChild(boton);
  }
  const pintar = () => {
    const activo = sonidoActivo();
    boton.setAttribute('aria-pressed', String(activo));
    boton.title = `Sonidos: ${activo ? 'activados' : 'silenciados'}`;
    boton.querySelector('.icono').textContent = activo ? 'volume_up' : 'volume_off';
  };
  boton.addEventListener('click', () => {
    const activar = !sonidoActivo();
    try { localStorage.setItem(CLAVE_SONIDO, activar ? 'si' : 'no'); } catch { /* sin almacenamiento */ }
    pintar();
    if (activar) sonar('exito'); // para que se note que volvió el sonido
  });
  pintar();
}
prepararBotonSonido();

// =====================================================================
//  Piezas que se repiten en varias pantallas
// =====================================================================

/** Tarjeta de resumen: ícono, número grande y título (por ejemplo «12 · Pedidos activos»). */
export function tarjetaResumen(icono, titulo, valor, clase = '') {
  return crear('div', { className: `tarjeta-resumen ${clase}`.trim() }, [
    crear('span', { className: 'icono', texto: icono, 'aria-hidden': 'true' }),
    crear('div', { className: 'valor', texto: valor }),
    crear('div', { texto: titulo }),
  ]);
}

/** "2026-11-18T22:10:00" -> "18 nov, 10:10 p. m." ('—' si no hay fecha). */
export function fechaHora(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
}

/** Muestra (o borra, con mensaje vacío) el error de un campo: #error-<nombre> y borde rojo en #campo-<nombre>. */
export function marcarCampo(nombre, mensaje) {
  document.getElementById(`error-${nombre}`).textContent = mensaje;
  document.getElementById(`campo-${nombre}`)?.classList.toggle('invalido', Boolean(mensaje));
}

/** «Buenas noches, Ángel» y la fecha de hoy («Miércoles, 18 de noviembre»), con un texto opcional al final. */
export function pintarSaludo(contenedor, nombre, extra = '') {
  const ahora = new Date();
  const saludo = ahora.getHours() < 12 ? 'Buenos días' : ahora.getHours() < 19 ? 'Buenas tardes' : 'Buenas noches';
  const fecha = ahora.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
  contenedor.replaceChildren(crear('div', {}, [
    crear('h2', { texto: `${saludo}, ${nombre}` }),
    crear('p', { className: 'nota', texto: fecha.charAt(0).toUpperCase() + fecha.slice(1) + (extra ? ` · ${extra}` : '') }),
  ]));
}
