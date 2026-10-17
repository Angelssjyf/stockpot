import 'package:flutter/foundation.dart';

/// Dirección de la API Flask.
///
/// - Web publicada (Flask sirve la app): la API está en la misma dirección que la página,
///   así funciona igual en http://127.0.0.1:5000 que en el enlace de ngrok.
/// - Web en desarrollo (flutter run -d chrome): la API está en 127.0.0.1:5000.
/// - Emulador de Android: ve el "localhost" del PC como 10.0.2.2.
///
/// Se puede forzar otra dirección al compilar o ejecutar:
///   flutter run --dart-define=API_URL=https://tu-dominio.ngrok-free.app/api
class AppConfig {
  static const _apiUrlManual = String.fromEnvironment('API_URL');

  static String get apiUrl {
    if (_apiUrlManual.isNotEmpty) return _apiUrlManual;
    if (kIsWeb) {
      return kReleaseMode ? '${Uri.base.origin}/api' : 'http://127.0.0.1:5000/api';
    }
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:5000/api';
    return 'http://127.0.0.1:5000/api';
  }
}
