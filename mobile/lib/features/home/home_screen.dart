import 'package:flutter/material.dart';

import '../auth/auth_service.dart';

/// Un módulo del menú principal.
class Modulo {
  const Modulo(this.titulo, this.icono, this.permiso);

  final String titulo;
  final IconData icono;
  final String permiso; // permiso mínimo para ver el módulo
}

/// Los 11 módulos de StockPot, en el orden de las iteraciones.
const modulos = <Modulo>[
  Modulo('Usuarios', Icons.people, 'usuarios.ver'),
  Modulo('Proveedores', Icons.local_shipping, 'proveedores.ver'),
  Modulo('Inventario', Icons.inventory_2, 'inventario.ver'),
  Modulo('Menú', Icons.restaurant_menu, 'productos.ver'),
  Modulo('Pedidos', Icons.receipt_long, 'pedidos.ver'),
  Modulo('Cocina', Icons.soup_kitchen, 'cocina.ver'),
  Modulo('Reservas', Icons.event_seat, 'reservas.ver'),
  Modulo('Domicilios', Icons.delivery_dining, 'domicilios.ver'),
  Modulo('Pagos', Icons.payments, 'pagos.ver'),
  Modulo('Ventas', Icons.point_of_sale, 'ventas.ver'),
  Modulo('Reportes', Icons.bar_chart, 'reportes.ver'),
];

/// Menú principal: muestra solo los módulos que el rol del usuario puede ver.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.usuario, required this.alCerrarSesion});

  final Usuario usuario;
  final VoidCallback alCerrarSesion;

  @override
  Widget build(BuildContext context) {
    final visibles = modulos.where((m) => usuario.puede(m.permiso)).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('StockPot'),
        actions: [
          Center(child: Text('${usuario.nombre} · ${usuario.rol}')),
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: alCerrarSesion,
          ),
        ],
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 180, // ancho máximo de cada tarjeta
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
        ),
        itemCount: visibles.length,
        itemBuilder: (context, i) => _TarjetaModulo(modulo: visibles[i]),
      ),
    );
  }
}

/// Tarjeta de un módulo. Por ahora todos avisan que están en construcción.
class _TarjetaModulo extends StatelessWidget {
  const _TarjetaModulo({required this.modulo});

  final Modulo modulo;

  @override
  Widget build(BuildContext context) {
    final colores = Theme.of(context).colorScheme;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('El módulo ${modulo.titulo} está en construcción')),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(modulo.icono, size: 44, color: colores.primary),
            const SizedBox(height: 8),
            Text(modulo.titulo, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}