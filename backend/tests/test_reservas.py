"""Casos de prueba: reservas (RF-07.1 a RF-07.8).

Formato del docstring:  ID del caso | requisito | qué se verifica
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Reserva

from .conftest import crear_usuario, iniciar_sesion
from .test_pedidos import mesas  # noqa: F401  (fixture: mesa 1 para 4 y mesa 2 para 2)

MANANA = (datetime.now() + timedelta(days=1)).replace(hour=19, minute=30, second=0, microsecond=0)


def _hora(base, **mas):
    return (base + timedelta(**mas)).strftime("%Y-%m-%dT%H:%M")


def _reservar(client, headers, mesa_id, **cambios):
    datos = {"cliente": "Ana Ruiz", "telefono": "3001234567", "personas": 4,
             "fecha_hora": _hora(MANANA), "mesa_id": mesa_id, "observaciones": "Aniversario"}
    return client.post("/api/reservas", headers=headers, json={**datos, **cambios})


@pytest.fixture()
def reserva(client, mesero_headers, mesas):
    r = _reservar(client, mesero_headers, mesas[1])
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def test_cp_07_1_1_registrar(client, reserva):
    """CP-07.1-1 | RF-07.1, RF-07.5, RF-07.6 | Se registra con cliente, personas, fecha y hora y mesa;
    queda PENDIENTE con su código y aparta la mesa 2 horas."""
    assert reserva["codigo"].startswith("RES-") and reserva["estado"] == "PENDIENTE"
    assert (reserva["mesa"], reserva["personas"], reserva["duracion_minutos"]) == (1, 4, 120)
    assert reserva["fecha_hora"] == MANANA.isoformat()
    assert reserva["fin"] == (MANANA + timedelta(hours=2)).isoformat()


@pytest.mark.parametrize("cambios, codigo, mensaje", [
    ({"cliente": ""}, 422, "nombre del cliente es obligatorio"),
    ({"telefono": " "}, 422, "teléfono es obligatorio"),
    ({"personas": 0}, 422, "mayor que cero"),
    ({"fecha_hora": "mañana"}, 422, "formato AAAA-MM-DDTHH:MM"),
    ({"fecha_hora": _hora(datetime.now(), hours=-1)}, 422, "fecha y hora futuras"),
    ({"duracion_minutos": 10}, 422, "entre 30 y 360"),
    ({"mesa_id": 999}, 422, "La mesa no existe"),
    ({"personas": 5}, 422, "es para 4 personas"),
])
def test_cp_07_1_2_datos_invalidos(client, mesero_headers, mesas, cambios, codigo, mensaje):
    """CP-07.1-2 | RF-07.1, RF-07.5, RF-07.6 | Datos obligatorios, fecha futura, duración razonable y
    personas que quepan en la mesa."""
    r = _reservar(client, mesero_headers, **{"mesa_id": mesas[1], **cambios})
    assert r.status_code == codigo and mensaje in r.get_json()["error"]


@pytest.mark.parametrize("inicio, cruza", [
    ({"hours": 1}, True),        # 8:30 p. m., dentro de la otra reserva
    ({"minutes": -90}, True),    # 6:00 p. m. hasta 8:00 p. m.: se cruza 30 min
    ({"hours": 2}, False),       # 9:30 p. m., justo cuando la otra termina
    ({"hours": -2}, False),      # 5:30 p. m. a 7:30 p. m., termina cuando la otra empieza
])
def test_cp_07_7_1_no_se_cruzan(client, mesero_headers, mesas, reserva, inicio, cruza):
    """CP-07.7-1 | RF-07.7 | Una mesa no se reserva dos veces en horarios que se cruzan (valores límite:
    terminar justo cuando empieza la otra sí se puede)."""
    r = _reservar(client, mesero_headers, mesas[1], fecha_hora=_hora(MANANA, **inicio), cliente="Luis")
    if cruza:
        assert r.status_code == 409 and "ya está reservada a esa hora" in r.get_json()["error"]
    else:
        assert r.status_code == 201, r.get_json()


def test_cp_07_7_2_disponibilidad(client, mesero_headers, mesas, reserva):
    """CP-07.7-2 | RF-07.7 | La disponibilidad muestra las mesas con cupo y libres en ese horario."""
    consulta = lambda **p: client.get("/api/reservas/disponibilidad", headers=mesero_headers,  # noqa: E731
                                      query_string=p).get_json()
    assert [m["numero"] for m in consulta(fecha_hora=_hora(MANANA), personas=2)["mesas"]] == [2]  # la 1 está reservada
    assert consulta(fecha_hora=_hora(MANANA), personas=3)["mesas"] == []  # la 2 es para 2
    assert [m["numero"] for m in consulta(fecha_hora=_hora(MANANA, hours=3), personas=2)["mesas"]] == [2, 1]
    al_modificar = consulta(fecha_hora=_hora(MANANA), personas=4, reserva_id=reserva["id"])["mesas"]
    assert [m["numero"] for m in al_modificar] == [1]
    r = client.get("/api/reservas/disponibilidad?personas=2", headers=mesero_headers)
    assert r.status_code == 422


def test_cp_07_2_1_consultar_por_dia(client, mesero_headers, mesas, reserva):
    """CP-07.2-1 | RF-07.2 | Se consultan las reservas de un día en orden de hora, con resumen y buscador."""
    _reservar(client, mesero_headers, mesas[2], personas=2, cliente="Luis Gil", fecha_hora=_hora(MANANA, hours=-6))
    dia = MANANA.date().isoformat()
    r = client.get(f"/api/reservas?fecha={dia}", headers=mesero_headers).get_json()
    assert [x["cliente"] for x in r["reservas"]] == ["Luis Gil", "Ana Ruiz"]
    assert r["resumen"] == {"reservas": 2, "activas": 2, "personas": 6, "confirmadas": 0}
    assert [x["cliente"] for x in client.get(f"/api/reservas?fecha={dia}&q=luis", headers=mesero_headers).get_json()["reservas"]] == ["Luis Gil"]
    assert client.get("/api/reservas", headers=mesero_headers).get_json()["reservas"] == []  # hoy no hay
    assert client.get("/api/reservas?fecha=20-11", headers=mesero_headers).status_code == 422


def test_cp_07_3_1_modificar(client, mesero_headers, mesas, reserva):
    """CP-07.3-1 | RF-07.3 | Se modifica la hora, las personas y la mesa revisando de nuevo la disponibilidad."""
    r = client.put(f"/api/reservas/{reserva['id']}", headers=mesero_headers,
                   json={"personas": 2, "mesa_id": mesas[2], "fecha_hora": _hora(MANANA, minutes=30)})
    assert r.status_code == 200 and (r.get_json()["mesa"], r.get_json()["personas"]) == (2, 2)
    otra = _reservar(client, mesero_headers, mesas[1], cliente="Luis").get_json()  # la mesa 1 quedó libre
    r = client.put(f"/api/reservas/{otra['id']}", headers=mesero_headers, json={"mesa_id": mesas[2], "personas": 2})
    assert r.status_code == 409
    assert db.session.get(Reserva, otra["id"]).mesa_id == mesas[1]  # no quedó a medias


def test_cp_07_4_1_cancelar(client, mesero_headers, mesas, reserva):
    """CP-07.4-1 | RF-07.4 | Al cancelar la mesa queda libre en ese horario; una cancelada no se modifica."""
    r = client.patch(f"/api/reservas/{reserva['id']}/cancelar", headers=mesero_headers, json={"motivo": "Llamó a cancelar"})
    assert r.status_code == 200 and r.get_json()["estado"] == "CANCELADA"
    assert "Cancelada: Llamó a cancelar" in r.get_json()["observaciones"]
    assert _reservar(client, mesero_headers, mesas[1], cliente="Luis").status_code == 201
    assert client.put(f"/api/reservas/{reserva['id']}", headers=mesero_headers, json={"personas": 2}).status_code == 409
    assert client.patch(f"/api/reservas/{reserva['id']}/cancelar", headers=mesero_headers).status_code == 409


def test_cp_07_8_1_estados(client, mesero_headers, mesas, reserva):
    """CP-07.8-1 | RF-07.8 | PENDIENTE -> CONFIRMADA -> CUMPLIDA; no se marca que llegó con más de una hora
    de anticipación ni se vuelve atrás."""
    estado = lambda e: client.patch(f"/api/reservas/{reserva['id']}/estado", headers=mesero_headers,  # noqa: E731
                                    json={"estado": e})
    assert estado("CONFIRMADA").get_json()["estado"] == "CONFIRMADA"
    r = estado("CUMPLIDA")
    assert r.status_code == 409 and "más de una hora" in r.get_json()["error"]
    db.session.get(Reserva, reserva["id"]).fecha_hora = datetime.now() + timedelta(minutes=20)
    db.session.commit()
    assert estado("CUMPLIDA").get_json()["estado"] == "CUMPLIDA"
    assert estado("CONFIRMADA").status_code == 409
    assert estado("CANCELADA").status_code == 422 and estado("PERDIDA").status_code == 422


def test_cp_07_6_1_mesa_avisa_reserva(client, mesero_headers, mesas):
    """CP-07.6-1 | RF-07.6 | En el salón la mesa muestra su próxima reserva de hoy."""
    hoy = datetime.now() + timedelta(minutes=5)
    if hoy.date() != datetime.now().date():
        pytest.skip("a medianoche no hay 'hoy' para probar")
    _reservar(client, mesero_headers, mesas[2], personas=2, fecha_hora=_hora(hoy))
    salon = {m["numero"]: m for m in client.get("/api/mesas", headers=mesero_headers).get_json()}
    assert salon[2]["reserva"]["cliente"] == "Ana Ruiz" and salon[1]["reserva"] is None


def test_cp_seg_29_permisos_de_reservas(client, mesas):
    """CP-SEG-29 | RF-07 | El cocinero no ve reservas; el bodeguero tampoco las registra."""
    crear_usuario("COCINERO", "cocina@stockpot.test")
    crear_usuario("BODEGUERO", "bodega@stockpot.test")
    cocina = iniciar_sesion(client, "cocina@stockpot.test")
    bodega = iniciar_sesion(client, "bodega@stockpot.test")
    assert client.get("/api/reservas", headers=cocina).status_code == 403
    assert _reservar(client, bodega, mesas[1]).status_code == 403
