"""Cabeceras de seguridad HTTP en todas las respuestas (recomendaciones de OWASP).

- Content-Security-Policy: el navegador solo ejecuta scripts y estilos de StockPot (más la
  fuente de íconos de Google Fonts). Si alguien lograra inyectar un <script>, no corre.
- X-Frame-Options y frame-ancestors: nadie puede meter StockPot en un <iframe> de otra
  página para engañar al usuario con clics (clickjacking).
- X-Content-Type-Options: el navegador no "adivina" el tipo de un archivo.
- Referrer-Policy: las direcciones internas no se envían a otros sitios.
- Permissions-Policy: StockPot no usa cámara, micrófono ni ubicación.
- Cache-Control en /api: los datos del restaurante no se guardan en caché.
- Strict-Transport-Security: cuando se entra por HTTPS (el enlace de ngrok), el navegador
  ya no acepta HTTP para ese dominio.
"""

from flask import request

POLITICA = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

CABECERAS = {
    "Content-Security-Policy": POLITICA,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def register_cabeceras(app):
    @app.after_request
    def agregar_cabeceras(respuesta):
        for nombre, valor in CABECERAS.items():
            respuesta.headers.setdefault(nombre, valor)
        if request.path.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            respuesta.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return respuesta
