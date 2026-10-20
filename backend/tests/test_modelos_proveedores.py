"""Casos de prueba de los modelos de proveedores, insumos y órdenes de compra.

Verifican que las clases de Python coinciden con las tablas y relaciones del script SQL.
"""

from decimal import Decimal

from app.extensions import db
from app.models import DetalleOrdenCompra, Insumo, OrdenCompra, Proveedor, ProveedorInsumo

from .conftest import crear_usuario


def _proveedor_con_insumos():
    arroz = Insumo(codigo="INS-001", nombre="Arroz", unidad_medida="KG")
    pollo = Insumo(codigo="INS-002", nombre="Pollo", unidad_medida="KG")
    proveedor = Proveedor(nit="900123456-7", razon_social="Distribuidora La Cosecha")
    proveedor.insumos = [
        ProveedorInsumo(insumo=arroz, precio_referencia=Decimal("4200")),
        ProveedorInsumo(insumo=pollo, precio_referencia=Decimal("13000")),
    ]
    db.session.add(proveedor)
    db.session.commit()
    return proveedor, arroz, pollo


def test_cp_mod_02_1_proveedor_con_insumos(app):
    """CP-MOD-02-1 | RF-02.1, RF-02.4 | Un proveedor guarda los insumos que vende con su precio."""
    proveedor, _, _ = _proveedor_con_insumos()

    guardado = db.session.get(Proveedor, proveedor.id)
    assert guardado.activo is True  # valor por defecto
    assert sorted(pi.insumo.nombre for pi in guardado.insumos) == ["Arroz", "Pollo"]
    assert guardado.insumos[0].to_dict()["precio_referencia"] in (4200.0, 13000.0)


def test_cp_mod_02_2_insumo_valores_por_defecto(app):
    """CP-MOD-02-2 | ILF04 | Un insumo nuevo empieza con stock 0 y activo."""
    insumo = Insumo(codigo="INS-010", nombre="Sal", unidad_medida="G")
    db.session.add(insumo)
    db.session.commit()

    datos = insumo.to_dict()
    assert datos["stock_actual"] == 0
    assert datos["activo"] is True


def test_cp_mod_02_3_orden_con_detalles(app):
    """CP-MOD-02-3 | RF-02.6 | Una orden de compra guarda sus líneas y empieza PENDIENTE."""
    proveedor, arroz, pollo = _proveedor_con_insumos()
    usuario = crear_usuario("BODEGUERO", "bodega@stockpot.test")

    orden = OrdenCompra(codigo="OC-000001", proveedor=proveedor, usuario=usuario,
                        total=Decimal("181500"))
    orden.detalles = [
        DetalleOrdenCompra(insumo=arroz, cantidad=Decimal("20"), precio_unitario=Decimal("4200"),
                           subtotal=Decimal("84000")),
        DetalleOrdenCompra(insumo=pollo, cantidad=Decimal("7.5"),
                           precio_unitario=Decimal("13000"), subtotal=Decimal("97500")),
    ]
    db.session.add(orden)
    db.session.commit()

    datos = db.session.get(OrdenCompra, orden.id).to_dict()
    assert datos["estado"] == "PENDIENTE"
    assert datos["proveedor"] == "Distribuidora La Cosecha"
    assert datos["total"] == 181500.0
    assert [d["cantidad"] for d in datos["detalles"]] == [20.0, 7.5]


def test_cp_mod_02_4_borrar_orden_borra_detalles(app):
    """CP-MOD-02-4 | RF-02.6 | Al borrar una orden también se borran sus líneas."""
    proveedor, arroz, _ = _proveedor_con_insumos()
    usuario = crear_usuario("BODEGUERO", "bodega@stockpot.test")
    orden = OrdenCompra(codigo="OC-000002", proveedor=proveedor, usuario=usuario)
    orden.detalles = [DetalleOrdenCompra(insumo=arroz, cantidad=1, precio_unitario=1, subtotal=1)]
    db.session.add(orden)
    db.session.commit()

    db.session.delete(orden)
    db.session.commit()
    assert DetalleOrdenCompra.query.count() == 0