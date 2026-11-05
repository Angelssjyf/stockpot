// RF-12.2 Reportar un error (incidencia) sobre un movimiento, una venta o una orden de compra.
// La ventana se arma una sola vez y la comparten inventario, ventas y compras.
import { api } from './api.js';
import { crear, formato, mostrarAviso, prepararVentana } from './ui.js';

const $ = (id) => document.getElementById(id);
let dialogo = null;
let contexto = null; // lo que se está reportando (ver reportarIncidencia)
let codigos = [];

function armarVentana() {
  dialogo = crear('dialog', { id: 'dialogo-incidencia' }, [
    crear('form', { id: 'form-incidencia', novalidate: '' }, [
      crear('h2', { id: 'inc-titulo', texto: 'Reportar un error' }),
      crear('p', { className: 'nota', id: 'inc-registro' }),
      crear('label', { className: 'etiqueta', for: 'inc-codigo', texto: 'Tipo de error *' }),
      crear('div', { className: 'campo' }, [crear('select', { id: 'inc-codigo' })]),
      // RF-12.3 Solo para «cantidad de más / de menos»: la cantidad real y el ajuste que hará el sistema
      crear('div', { id: 'inc-correccion', hidden: '' }, [
        crear('label', { className: 'etiqueta', for: 'inc-real', texto: 'Cantidad real *' }),
        crear('div', { className: 'campo' }, [crear('input', { id: 'inc-real', type: 'number', min: '0', step: 'any' })]),
        crear('small', { className: 'ayuda-campo', id: 'inc-ayuda' }),
      ]),
      crear('label', { className: 'etiqueta', for: 'inc-observacion', texto: 'Observación *' }),
      crear('div', { className: 'campo campo-texto' }, [
        crear('textarea', { id: 'inc-observacion', rows: '3', maxlength: '500',
          placeholder: 'Ej.: registré por equivocación más kilos de los que eran' }),
      ]),
      crear('div', { className: 'alerta-error', id: 'inc-error', role: 'alert', hidden: '' }),
      crear('div', { className: 'acciones' }, [
        crear('button', { type: 'button', className: 'boton-texto', id: 'inc-cancelar', texto: 'Cancelar' }),
        crear('button', { type: 'submit', className: 'boton-principal', id: 'inc-enviar' }, [
          crear('span', { className: 'icono', texto: 'report', 'aria-hidden': 'true' }),
          document.createTextNode(' Reportar'),
        ]),
      ]),
    ]),
  ]);
  document.body.appendChild(dialogo);
  prepararVentana(dialogo);

  $('inc-cancelar').addEventListener('click', () => dialogo.close());
  $('inc-codigo').addEventListener('change', mostrarCorreccion);
  $('inc-real').addEventListener('input', explicarAjuste);
  $('form-incidencia').addEventListener('submit', enviar);
}

function codigoElegido() {
  return codigos.find((c) => String(c.id) === $('inc-codigo').value);
}

function mostrarCorreccion() {
  const corrige = Boolean(codigoElegido()?.corrige_stock);
  $('inc-correccion').hidden = !corrige;
  if (corrige) explicarAjuste();
}

/** Explica qué movimiento de ajuste va a crear el sistema con la cantidad escrita. */
function explicarAjuste() {
  const { cantidad, unidad, tipo } = contexto;
  const real = $('inc-real').value === '' ? null : Number($('inc-real').value);
  const registrado = `Se registró ${formato.cantidad(cantidad)} ${unidad}.`;
  if (real === null || real < 0 || real === cantidad) {
    $('inc-ayuda').textContent = `${registrado} Escribe lo que de verdad era.`;
    return;
  }
  const diferencia = real - cantidad;
  const opuesto = tipo === 'ENTRADA' ? 'salida' : 'entrada';
  const tipoAjuste = diferencia > 0 ? tipo.toLowerCase() : opuesto;
  $('inc-ayuda').textContent = `${registrado} El sistema hará una ${tipoAjuste} de ajuste de ${formato.cantidad(Math.abs(diferencia))} ${unidad}.`;
}

/**
 * Abre la ventana para reportar un error.
 * modulo: 'INVENTARIO' | 'VENTAS' | 'COMPRAS' | 'DOMICILIOS'
 * referencia: { movimiento_id } | { venta_id } | { orden_compra_id } | { domicilio_id }
 * descripcion: texto corto del registro (se muestra arriba)
 * cantidad, unidad, tipo: solo para movimientos que se pueden corregir (RF-12.3)
 * alGuardar(incidencia): se llama después de registrarla
 */
export async function reportarIncidencia({ modulo, referencia, descripcion, cantidad = null, unidad = '', tipo = '', alGuardar }) {
  if (!dialogo) armarVentana();
  contexto = { modulo, referencia, cantidad, unidad, tipo, alGuardar };
  $('form-incidencia').reset();
  $('inc-error').hidden = true;
  $('inc-titulo').textContent = modulo === 'DOMICILIOS' ? 'Reportar un inconveniente' : 'Reportar un error';
  $('inc-registro').textContent = descripcion;
  $('inc-correccion').hidden = true;
  try {
    codigos = (await api('GET', `/codigos-incidencia?modulo=${modulo}`))
      .filter((c) => !c.corrige_stock || cantidad !== null); // un consumo de venta no se corrige aquí
  } catch (error) {
    mostrarAviso(error.message, 'error');
    return;
  }
  $('inc-codigo').replaceChildren(
    crear('option', { value: '', texto: 'Elige el tipo de error…' }),
    ...codigos.map((c) => crear('option', { value: c.id, texto: `${c.codigo} · ${c.nombre}${c.causa_externa ? ' (causa externa)' : ''}` })),
  );
  dialogo.showModal();
}

async function enviar(evento) {
  evento.preventDefault();
  const tipo = codigoElegido();
  const observacion = $('inc-observacion').value.trim();
  const falta = !tipo ? 'Elige el tipo de error'
    : tipo.corrige_stock && $('inc-real').value === '' ? 'Escribe la cantidad real'
      : observacion.length < 5 ? 'Describe el error en la observación (mínimo 5 caracteres)' : '';
  if (falta) {
    $('inc-error').textContent = falta;
    $('inc-error').hidden = false;
    return;
  }
  $('inc-enviar').disabled = true;
  try {
    const incidencia = await api('POST', '/incidencias', {
      codigo_id: tipo.id,
      observacion,
      ...contexto.referencia,
      ...(tipo.corrige_stock ? { cantidad_real: Number($('inc-real').value) } : {}),
    });
    dialogo.close();
    mostrarAviso(`Incidencia ${incidencia.codigo} registrada`
      + (incidencia.ajuste ? ' y el inventario quedó corregido' : ''), 'exito');
    contexto.alGuardar?.(incidencia);
  } catch (error) {
    $('inc-error').textContent = error.message;
    $('inc-error').hidden = false;
  } finally {
    $('inc-enviar').disabled = false;
  }
}
