import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import 'auth_service.dart';

/// RF-01.4 Pantalla de inicio de sesión.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.auth, required this.alIniciarSesion});

  final AuthService auth;
  final void Function(Usuario usuario) alIniciarSesion;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formulario = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();

  bool _cargando = false;
  bool _ocultarClave = true;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _ingresar() async {
    if (!_formulario.currentState!.validate()) return; // revisa los campos antes de enviar

    setState(() {
      _cargando = true;
      _error = null;
    });

    try {
      final usuario = await widget.auth.login(_email.text.trim(), _password.text);
      widget.alIniciarSesion(usuario);
    } on ApiException catch (e) {
      setState(() => _error = e.mensaje); // mensaje que envía la API, en español
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colores = Theme.of(context).colorScheme;

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380), // no se estira en pantallas grandes
            child: Form(
              key: _formulario,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(Icons.soup_kitchen, size: 80, color: colores.primary),
                  const SizedBox(height: 8),
                  Text('StockPot',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.headlineMedium),
                  Text('Gestión para restaurantes',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: colores.onSurfaceVariant)),
                  const SizedBox(height: 32),
                  TextFormField(
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    decoration: const InputDecoration(
                      labelText: 'Correo',
                      prefixIcon: Icon(Icons.email_outlined),
                      border: OutlineInputBorder(),
                    ),
                    validator: (valor) => (valor == null || !valor.contains('@'))
                        ? 'Escribe un correo válido'
                        : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _password,
                    obscureText: _ocultarClave,
                    autofillHints: const [AutofillHints.password],
                    decoration: InputDecoration(
                      labelText: 'Contraseña',
                      prefixIcon: const Icon(Icons.lock_outline),
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        tooltip: _ocultarClave ? 'Mostrar contraseña' : 'Ocultar contraseña',
                        icon: Icon(_ocultarClave ? Icons.visibility : Icons.visibility_off),
                        onPressed: () => setState(() => _ocultarClave = !_ocultarClave),
                      ),
                    ),
                    validator: (valor) =>
                        (valor == null || valor.isEmpty) ? 'Escribe tu contraseña' : null,
                    onFieldSubmitted: (_) => _ingresar(), // Enter también inicia sesión
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: colores.errorContainer,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(_error!, style: TextStyle(color: colores.onErrorContainer)),
                    ),
                  ],
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _cargando ? null : _ingresar,
                    style: FilledButton.styleFrom(padding: const EdgeInsets.all(16)),
                    child: _cargando
                        ? const SizedBox(
                            height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Ingresar'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
