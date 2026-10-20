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
