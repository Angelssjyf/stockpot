import 'package:flutter/material.dart';

import 'core/api_client.dart';
import 'features/auth/auth_service.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';

void main() {
  runApp(StockPotApp(auth: AuthService(ApiClient())));
}

class StockPotApp extends StatefulWidget {
  const StockPotApp({super.key, required this.auth});

  final AuthService auth;

  @override
  State<StockPotApp> createState() => _StockPotAppState();
}

class _StockPotAppState extends State<StockPotApp> {
  Usuario? _usuario;
  bool _revisandoSesion = true;

  @override
  void initState() {
    super.initState();
    _revisarSesionGuardada();
  }

  Future<void> _revisarSesionGuardada() async {
    final usuario = await widget.auth.restaurarSesion();
    setState(() {
      _usuario = usuario;
      _revisandoSesion = false;
    });
  }

  Future<void> _cerrarSesion() async {
    await widget.auth.logout();
    setState(() => _usuario = null);
  }

  @override
  Widget build(BuildContext context) {
    final Widget pantalla;
    if (_revisandoSesion) {
      pantalla = const Scaffold(body: Center(child: CircularProgressIndicator()));
    } else if (_usuario == null) {
      pantalla = LoginScreen(
        auth: widget.auth,
        alIniciarSesion: (usuario) => setState(() => _usuario = usuario),
      );
    } else {
      pantalla = HomeScreen(usuario: _usuario!, alCerrarSesion: _cerrarSesion);
    }

    return MaterialApp(
      title: 'StockPot',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFFE65100), useMaterial3: true),
      home: pantalla,
    );
  }
}
