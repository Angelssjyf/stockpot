"""Pruebas unitarias: cada prueba ejercita UNA unidad (una función o un método) de forma aislada.

pytest hace de "driver": llama a la unidad con los datos del caso y compara el resultado
obtenido con el esperado. Cuando la unidad depende de algo externo (la base de datos, una
orden con sus pagos, una consulta SQL), se reemplaza por un "stub" en memoria para que la
prueba no dependa de nada más que de la unidad.

Diferencia con el resto de archivos de tests/: aquellos prueban los requisitos de punta a
punta a través de la API (funcionales y de integración); estos prueban las reglas de negocio
sueltas, sin HTTP ni base de datos. IDs: CPU-XX.X-n (Caso de Prueba Unitaria).
"""

import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models import Insumo, Pago, Producto, Receta, Usuario
from app.modules.compras.routes import TRANSICIONES as TRANSICIONES_COMPRA
from app.modules.domicilios.routes import TRANSICIONES as TRANSICIONES_DOMICILIO
from app.services import inventario as servicio_inventario
from app.services.inventario import StockInsuficiente, numero, registrar_movimiento
from app.services.ventas import PagoRechazado, estado_pago, pagado, registrar_pago
from app.utils.fechas import filtrar_por_fechas


def _insumo(stock, minimo=0, costo=0, nombre="Arroz", unidad="KG"):
    """Insumo en memoria (no se guarda en ninguna base)."""
    return Insumo(codigo="INS-001", nombre=nombre, unidad_medida=unidad, stock_actual=Decimal(str(stock)),
                  stock_minimo=Decimal(str(minimo)), costo_unitario=Decimal(str(costo)))


@pytest.fixture()
def sesion_falsa(monkeypatch):
    """Stub de db.session: guarda lo que se le agrega en una lista, sin tocar la base."""
    agregados = []
    monkeypatch.setattr(servicio_inventario.db, "session", SimpleNamespace(add=agregados.append))
    return agregados


# ------------------------------------------------------- Insumo.estado_stock (RF-03.8)


@pytest.mark.parametrize("stock, minimo, esperado", [
    (0, 5, "AGOTADO"),     # sin stock
    (-1, 5, "AGOTADO"),    # valor límite por debajo de cero
    (5, 5, "BAJO"),        # justo en el mínimo
    (4.5, 5, "BAJO"),      # por debajo del mínimo
    (5.001, 5, "OK"),      # apenas por encima del mínimo
    (10, 0, "OK"),         # sin mínimo definido
])
def test_cpu_03_8_1_estado_stock(stock, minimo, esperado):
    """CPU-03.8-1 | RF-03.8 | Insumo.estado_stock clasifica AGOTADO / BAJO / OK en los valores límite."""
    assert _insumo(stock, minimo).estado_stock == esperado


# ------------------------------------------------------- registrar_movimiento (RF-03.4 y RF-03.5)


def test_cpu_03_4_1_entrada_suma_stock(sesion_falsa):
    """CPU-03.4-1 | RF-03.4 | Una ENTRADA suma al stock y deja el movimiento con el stock resultante."""
    arroz = _insumo(10)
    movimiento = registrar_movimiento(arroz, "ENTRADA", "COMPRA", 2.5, usuario_id=1)
    assert arroz.stock_actual == Decimal("12.5")
    assert movimiento.stock_resultante == Decimal("12.5")
    assert sesion_falsa == [movimiento]


def test_cpu_03_5_1_salida_hasta_cero(sesion_falsa):
    """CPU-03.5-1 | RF-03.5 | Una SALIDA puede dejar el stock exactamente en cero (valor límite)."""
    arroz = _insumo(3)
    registrar_movimiento(arroz, "SALIDA", "CONSUMO", 3, usuario_id=1)
    assert arroz.stock_actual == 0


def test_cpu_03_5_2_salida_sin_stock(sesion_falsa):
    """CPU-03.5-2 | RF-03.5 | Una SALIDA mayor al stock lanza StockInsuficiente y no cambia nada."""
    arroz = _insumo(3)
    with pytest.raises(StockInsuficiente, match="hay 3 KG y se necesitan 3.5"):
        registrar_movimiento(arroz, "SALIDA", "CONSUMO", 3.5, usuario_id=1)
    assert arroz.stock_actual == 3
    assert sesion_falsa == []


def test_cpu_03_5_3_decimales_exactos(sesion_falsa):
    """CPU-03.5-3 | RF-03.5 | Las cantidades usan Decimal: 0,1 + 0,2 da 0,3 exacto (sin error de float)."""
    sal = _insumo(0)
    registrar_movimiento(sal, "ENTRADA", "AJUSTE", 0.1, usuario_id=1)
    registrar_movimiento(sal, "ENTRADA", "AJUSTE", 0.2, usuario_id=1)
    assert sal.stock_actual == Decimal("0.3")


@pytest.mark.parametrize("valor, texto", [(Decimal("25.000"), "25"), (Decimal("40.500"), "40.5"),
                                          (Decimal("0.125"), "0.125")])
def test_cpu_03_5_4_numero_para_mensajes(valor, texto):
    """CPU-03.5-4 | RF-03.5 | numero() quita los ceros sobrantes de las cantidades en los mensajes."""
    assert numero(valor) == texto


# ------------------------------------------------------- Producto: costo y porciones (RF-04.4)


def _bandeja(stock_pollo=5, stock_arroz=10):
    pollo = _insumo(stock_pollo, costo=13000, nombre="Pollo")
    arroz = _insumo(stock_arroz, costo=4200)
    producto = Producto(codigo="PRD-001", nombre="Bandeja", categoria="PLATO_FUERTE",
                        precio_venta=Decimal("22000"))
    producto.receta = [Receta(insumo=pollo, cantidad=Decimal("0.25")),
                       Receta(insumo=arroz, cantidad=Decimal("0.15"))]
    return producto


def test_cpu_04_4_1_costo_de_la_receta():
    """CPU-04.4-1 | RF-04.4 | Producto.costo suma cantidad × costo unitario de cada insumo."""
    assert _bandeja().costo == Decimal("3880")  # 0,25 × 13.000 + 0,15 × 4.200


@pytest.mark.parametrize("pollo, arroz, porciones", [
    (5, 10, 20),     # el pollo limita: 5 / 0,25 = 20 (el arroz alcanzaría para 66)
    (5, 1.5, 10),    # ahora limita el arroz: 1,5 / 0,15 = 10
    (0.2, 10, 0),    # no alcanza ni para una porción
])
def test_cpu_04_4_2_porciones_posibles(pollo, arroz, porciones):
    """CPU-04.4-2 | RF-04.4 | porciones_posibles la limita el insumo que primero se acaba."""
    assert _bandeja(pollo, arroz).porciones_posibles == porciones


def test_cpu_04_4_3_sin_receta():
    """CPU-04.4-3 | RF-04.4 | Un producto sin receta no calcula porciones (None) y cuesta 0."""
    gaseosa = Producto(codigo="PRD-006", nombre="Gaseosa", categoria="BEBIDA", precio_venta=Decimal("4500"))
    assert gaseosa.porciones_posibles is None
    assert gaseosa.costo == 0


# ------------------------------------------------------- Pagos: estado y validaciones (RF-09)


def _orden(total, pagos=(), estado="ABIERTA"):
    """Stub de una orden: solo los atributos que leen las funciones de pago."""
    return SimpleNamespace(codigo="VTA-0001", estado=estado, total=Decimal(str(total)),
                           pagos=[SimpleNamespace(monto=Decimal(str(m)), estado=e) for m, e in pagos])


@pytest.mark.parametrize("pagos, esperado", [
    ([], "PENDIENTE"),
    ([(10000, "APROBADO")], "PARCIAL"),
    ([(10000, "APROBADO"), (12000, "APROBADO")], "PAGADO"),
    ([(22000, "ANULADO")], "PENDIENTE"),        # los pagos anulados no cuentan
    ([(25000, "APROBADO")], "PAGADO"),          # pagar de más también deja la orden pagada
])
def test_cpu_09_4_1_estado_pago(pagos, esperado):
    """CPU-09.4-1 | RF-09.4 | estado_pago: PENDIENTE, PARCIAL o PAGADO según lo abonado."""
    assert estado_pago(_orden(22000, pagos)) == esperado


def test_cpu_09_4_2_solo_suma_aprobados():
    """CPU-09.4-2 | RF-09.4 | pagado() suma únicamente los pagos APROBADOS."""
    assert pagado(_orden(22000, [(5000, "APROBADO"), (7000, "ANULADO"), (3000, "APROBADO")])) == 8000


@pytest.mark.parametrize("orden, metodo, monto, mensaje, codigo", [
    (_orden(22000, estado="CERRADA"), "EFECTIVO", Decimal("1000"), "está CERRADA", 409),
    (_orden(22000), "CHEQUE", Decimal("1000"), "Método de pago inválido", 422),
    (_orden(22000), "EFECTIVO", Decimal("0"), "mayor que cero", 422),
    (_orden(22000, [(20000, "APROBADO")]), "TARJETA", Decimal("2001"), "supera el saldo pendiente ($2.000)", 422),
])
def test_cpu_09_1_1_pago_rechazado(orden, metodo, monto, mensaje, codigo):
    """CPU-09.1-1 | RF-09.1, RF-09.2 | registrar_pago rechaza orden cerrada, método, monto y saldo inválidos."""
    with pytest.raises(PagoRechazado, match=re.escape(mensaje)) as error:
        registrar_pago(orden, metodo, monto, usuario=None)
    assert error.value.codigo == codigo


def test_cpu_09_2_1_metodos_de_pago():
    """CPU-09.2-1 | RF-09.2 | Los métodos de pago aceptados son efectivo, tarjeta y transferencia."""
    assert Pago.METODOS == ("EFECTIVO", "TARJETA", "TRANSFERENCIA")


# ------------------------------------------------------- Máquinas de estado (RF-02.7 y RF-08.6)


@pytest.mark.parametrize("transiciones, finales", [
    (TRANSICIONES_COMPRA, {"RECIBIDA", "CANCELADA"}),
    (TRANSICIONES_DOMICILIO, {"ENTREGADO", "CANCELADO"}),
])
def test_cpu_08_6_1_estados_finales(transiciones, finales):
    """CPU-08.6-1 | RF-02.7, RF-08.6 | De un estado final no se puede pasar a ningún otro."""
    assert {estado for estado, siguientes in transiciones.items() if not siguientes} >= finales
    destinos = set().union(*transiciones.values())
    assert destinos <= set(transiciones)  # nunca se apunta a un estado que no existe


def test_cpu_08_6_2_no_se_retrocede():
    """CPU-08.6-2 | RF-08.6 | Un domicilio avanza en orden: no puede volver a RECIBIDO."""
    assert all("RECIBIDO" not in siguientes for siguientes in TRANSICIONES_DOMICILIO.values())


# ------------------------------------------------------- Contraseñas (RF-01.1 y RF-01.4)


def test_cpu_01_1_1_contrasena_cifrada():
    """CPU-01.1-1 | RF-01.1, RF-01.4 | La contraseña se guarda cifrada y solo valida la correcta."""
    usuario = Usuario(nombre="Ana", apellido="Ruiz", email="ana@stockpot.co")
    usuario.set_password("ClaveSegura123")
    assert "ClaveSegura123" not in usuario.password_hash
    assert usuario.check_password("ClaveSegura123")
    assert not usuario.check_password("clavesegura123")


def test_cpu_01_1_2_mismo_texto_distinto_hash():
    """CPU-01.1-2 | RF-01.1 | Dos usuarios con la misma contraseña tienen hashes distintos (sal aleatoria)."""
    a, b = Usuario(), Usuario()
    a.set_password("ClaveSegura123")
    b.set_password("ClaveSegura123")
    assert a.password_hash != b.password_hash


# ------------------------------------------------------- Filtro de fechas (RF-10 y RF-11)


class _ColumnaFalsa:
    """Stub de una columna SQL: en vez de armar SQL, devuelve la comparación como tupla."""

    def __ge__(self, otro):
        return (">=", otro)

    def __lt__(self, otro):
        return ("<", otro)


class _ConsultaFalsa:
    """Stub de una consulta: guarda los filtros que se le aplican."""

    def __init__(self):
        self.filtros = []

    def filter(self, condicion):
        self.filtros.append(condicion)
        return self


@pytest.mark.parametrize("args, filtros", [
    ({}, []),
    ({"desde": "2026-10-01"}, [(">=", date(2026, 10, 1))]),
    ({"hasta": "2026-10-31"}, [("<", date(2026, 11, 1))]),   # "hasta" incluye todo ese día
    ({"desde": "2026-10-01", "hasta": "2026-10-01"}, [(">=", date(2026, 10, 1)), ("<", date(2026, 10, 2))]),
])
def test_cpu_11_1_1_filtrar_por_fechas(args, filtros):
    """CPU-11.1-1 | RF-10.4, RF-11.2 | filtrar_por_fechas aplica ?desde y ?hasta, ambos incluidos."""
    assert filtrar_por_fechas(_ConsultaFalsa(), _ColumnaFalsa(), args).filtros == filtros


@pytest.mark.parametrize("fecha", ["19/10/2026", "2026-13-01", "ayer"])
def test_cpu_11_1_2_fecha_invalida(fecha):
    """CPU-11.1-2 | RF-11.2 | Una fecha que no es AAAA-MM-DD válida lanza ValueError."""
    with pytest.raises(ValueError):
        filtrar_por_fechas(_ConsultaFalsa(), _ColumnaFalsa(), {"desde": fecha})
