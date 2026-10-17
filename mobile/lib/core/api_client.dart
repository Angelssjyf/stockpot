import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

/// Error que devuelve la API, por ejemplo {"error": "Correo o contraseña incorrectos"}.
class ApiException implements Exception {
  ApiException(this.codigo, this.mensaje);

  final int codigo; // código HTTP: 401, 403, 422...
  final String mensaje;

  @override
  String toString() => mensaje;
}

/// Única pieza de la app que habla con la API Flask.
/// Agrega el token a cada petición y convierte los errores en [ApiException].
class ApiClient {
  String? token;

  Map<String, String> get _encabezados => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<dynamic> get(String ruta) async {
    final respuesta = await _enviar(() => http.get(_url(ruta), headers: _encabezados));
    return _procesar(respuesta);
  }

  Future<dynamic> post(String ruta, Map<String, dynamic> datos) async {
    final respuesta = await _enviar(
      () => http.post(_url(ruta), headers: _encabezados, body: jsonEncode(datos)),
    );
    return _procesar(respuesta);
  }

  Uri _url(String ruta) => Uri.parse('${AppConfig.apiUrl}$ruta');

  /// Si el servidor no responde (apagado, sin red), da un mensaje claro.
  Future<http.Response> _enviar(Future<http.Response> Function() peticion) async {
    try {
      return await peticion().timeout(const Duration(seconds: 15));
    } catch (_) {
      throw ApiException(0, 'No se pudo conectar con el servidor');
    }
  }

  dynamic _procesar(http.Response respuesta) {
    final cuerpo = respuesta.body.isEmpty ? null : jsonDecode(utf8.decode(respuesta.bodyBytes));
    if (respuesta.statusCode >= 200 && respuesta.statusCode < 300) return cuerpo;

    final mensaje = (cuerpo is Map && cuerpo['error'] is String)
        ? cuerpo['error'] as String
        : 'Error ${respuesta.statusCode}';
    throw ApiException(respuesta.statusCode, mensaje);
  }
}
