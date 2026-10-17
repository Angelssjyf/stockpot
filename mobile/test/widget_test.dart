// Pruebas de la pantalla de inicio de sesión (RF-01.4), sin conectarse a la API.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:stockpot/core/api_client.dart';
import 'package:stockpot/features/auth/auth_service.dart';
import 'package:stockpot/features/auth/login_screen.dart';

Widget _pantalla() => MaterialApp(
      home: LoginScreen(auth: AuthService(ApiClient()), alIniciarSesion: (_) {}),
    );

void main() {
  testWidgets('CP-01.4-F1 | RF-01.4 | La pantalla muestra correo, contraseña e Ingresar',
      (tester) async {
    await tester.pumpWidget(_pantalla());

    expect(find.text('StockPot'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Correo'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, 'Contraseña'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Ingresar'), findsOneWidget);
  });

  testWidgets('CP-01.4-F2 | RF-01.4 | Con los campos vacíos no se envía y se avisa',
      (tester) async {
    await tester.pumpWidget(_pantalla());

    await tester.tap(find.text('Ingresar'));
    await tester.pump();

    expect(find.text('Escribe un correo válido'), findsOneWidget);
    expect(find.text('Escribe tu contraseña'), findsOneWidget);
  });

  testWidgets('CP-01.4-F3 | RF-01.4 | El botón del ojo muestra y oculta la contraseña',
      (tester) async {
    await tester.pumpWidget(_pantalla());
    EditableText campoClave() => tester.widget<EditableText>(
          find.descendant(
            of: find.widgetWithText(TextFormField, 'Contraseña'),
            matching: find.byType(EditableText),
          ),
        );

    expect(campoClave().obscureText, isTrue);
    await tester.tap(find.byTooltip('Mostrar contraseña'));
    await tester.pump();
    expect(campoClave().obscureText, isFalse);
  });
}
