// Pruebas del menú principal: cada rol ve solo sus módulos.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:stockpot/features/auth/auth_service.dart';
import 'package:stockpot/features/home/home_screen.dart';

Usuario _usuarioCon(String rol, List<String> permisos) => Usuario.fromJson({
      'id': 1,
      'nombre': 'Prueba',
      'apellido': 'Test',
      'email': 'prueba@stockpot.test',
      'rol': rol,
      'permisos': permisos,
    });

Future<void> _abrirMenu(WidgetTester tester, Usuario usuario) =>
    tester.pumpWidget(MaterialApp(home: HomeScreen(usuario: usuario, alCerrarSesion: () {})));

void main() {
  testWidgets('CP-MENU-1 | RF-01.6 | El MESERO solo ve Menú, Pedidos y Reservas', (tester) async {
    await _abrirMenu(tester, _usuarioCon('MESERO',
        ['productos.ver', 'pedidos.ver', 'pedidos.gestionar', 'reservas.ver', 'reservas.gestionar']));

    expect(find.text('Menú'), findsOneWidget);
    expect(find.text('Pedidos'), findsOneWidget);
    expect(find.text('Reservas'), findsOneWidget);
    expect(find.text('Usuarios'), findsNothing);
    expect(find.text('Pagos'), findsNothing);
  });

  testWidgets('CP-MENU-2 | RF-01.6 | El ADMINISTRADOR ve los 11 módulos', (tester) async {
    final todos = modulos.map((m) => m.permiso).toList();
    await _abrirMenu(tester, _usuarioCon('ADMINISTRADOR', todos));

    expect(find.byType(Card), findsNWidgets(11));
  });

  testWidgets('CP-MENU-3 | Tocar un módulo avisa que está en construcción', (tester) async {
    await _abrirMenu(tester, _usuarioCon('DOMICILIARIO', ['domicilios.ver']));

    await tester.tap(find.text('Domicilios'));
    await tester.pump();

    expect(find.text('El módulo Domicilios está en construcción'), findsOneWidget);
  });
}