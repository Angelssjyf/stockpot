import 'package:flutter/material.dart';

import '../auth/auth_service.dart';

/// Pantalla de inicio provisional: muestra quién inició sesión.
/// Aquí irá el menú de módulos según los permisos del rol.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.usuario, required this.alCerrarSesion});

  final Usuario usuario;
  final VoidCallback alCerrarSesion;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('StockPot'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: alCerrarSesion,
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.waving_hand, size: 56),
              const SizedBox(height: 16),
              Text('¡Hola, ${usuario.nombreCompleto}!',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              Chip(label: Text(usuario.rol)),
              const SizedBox(height: 8),
              Text('${usuario.permisos.length} permisos · ${usuario.email}'),
            ],
          ),
        ),
      ),
    );
  }
}
