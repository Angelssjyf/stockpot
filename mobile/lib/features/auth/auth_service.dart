import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api_client.dart';

/// Datos del usuario que inició sesión.
class Usuario {
  Usuario.fromJson(Map<String, dynamic> json)
      : id = json['id'] as int,
        nombre = json['nombre'] as String,
        apellido = json['apellido'] as String,
        email = json['email'] as String,
        rol = json['rol'] as String,
        permisos = List<String>.from(json['permisos'] as List);

  final int id;
  final String nombre;
  final String apellido;
  final String email;
  final String rol;
  final List<String> permisos;

  String get nombreCompleto => '$nombre $apellido';

  bool puede(String permiso) => permisos.contains(permiso);
}

/// Inicia sesión, la recuerda en el dispositivo y la cierra.
class AuthService {
  AuthService(this.api);

  static const _claveToken = 'stockpot_token';

  final ApiClient api;
  Usuario? usuario;

  /// RF-01.4 Iniciar sesión.
  Future<Usuario> login(String email, String password) async {
    final respuesta = await api.post('/auth/login', {'email': email, 'password': password});
    api.token = respuesta['access_token'] as String;
    usuario = Usuario.fromJson(respuesta['usuario'] as Map<String, dynamic>);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_claveToken, api.token!);
    return usuario!;
  }

  /// Al abrir la app: si hay un token guardado y sigue vigente, recupera la sesión.
  Future<Usuario?> restaurarSesion() async {
    final prefs = await SharedPreferences.getInstance();
    api.token = prefs.getString(_claveToken);
    if (api.token == null) return null;

    try {
      final datos = await api.get('/auth/me');
      usuario = Usuario.fromJson(datos as Map<String, dynamic>);
      return usuario;
    } on ApiException catch (error) {
      // Token vencido o inválido: se borra. Si el servidor no respondió, se conserva.
      if (error.codigo == 401) await logout();
      return null;
    }
  }

  Future<void> logout() async {
    api.token = null;
    usuario = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_claveToken);
  }
}
