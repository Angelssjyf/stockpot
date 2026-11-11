// Auditoría Lighthouse de StockPot (guía de la docente): perfil limpio sin extensiones (equivale al
// modo incógnito), escritorio y celular, categorías Performance, Accessibility, Best Practices y SEO.
// Uso: node auditar.mjs   (con el servidor de demostración en http://127.0.0.1:5070)
import fs from 'node:fs';
import path from 'node:path';
import lighthouse from 'lighthouse';
import desktopConfig from 'lighthouse/core/config/desktop-config.js';
import puppeteer from 'puppeteer-core';

const BASE = 'http://127.0.0.1:5070';
const CARPETA = path.resolve('informes');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const { token } = JSON.parse(fs.readFileSync('token.json', 'utf8'));
const PANTALLAS = [
  ['Inicio de sesión (RF-01.4)', 'index.html', false],
  ['Menú principal', 'menu.html', true],
  ['Usuarios y roles (RF-01)', 'usuarios.html', true],
  ['Proveedores (RF-02)', 'proveedores.html', true],
  ['Órdenes de compra (RF-02)', 'compras.html', true],
  ['Inventario (RF-03)', 'insumos.html', true],
  ['Productos y menú (RF-04)', 'productos.html', true],
  ['Pedidos en mesa (RF-05)', 'pedidos.html', true],
  ['Cocina (RF-06)', 'cocina.html', true],
  ['Reservas (RF-07)', 'reservas.html', true],
  ['Domicilios (RF-08)', 'domicilios.html', true],
  ['Caja y pagos (RF-09)', 'caja.html', true],
  ['Ventas y consumo (RF-10)', 'ventas.html', true],
  ['Reportes (RF-11)', 'reportes.html', true],
];
const MODOS = { escritorio: desktopConfig, celular: undefined }; // celular = configuración por defecto (Moto G, 4G lenta)
const CATEGORIAS = ['performance', 'accessibility', 'best-practices', 'seo'];

fs.mkdirSync(CARPETA, { recursive: true });
const navegador = await puppeteer.launch({
  executablePath: CHROME, headless: true,
  args: ['--no-first-run', '--no-default-browser-check', '--disable-extensions'],
});
const puerto = Number(new URL(navegador.wsEndpoint()).port);
const pagina = await navegador.newPage();
await pagina.goto(`${BASE}/index.html`);

const SOLO = process.argv[2]; // node auditar.mjs productos  → solo esa pantalla (y conserva las demás)
const resultados = SOLO && fs.existsSync('resultados.json')
  ? JSON.parse(fs.readFileSync('resultados.json', 'utf8')).filter((f) => !f.archivo.startsWith(SOLO)) : [];
for (const [nombre, archivo, conSesion] of PANTALLAS.filter(([, a]) => !SOLO || a.startsWith(SOLO))) {
  // La sesión de prueba se guarda en el navegador antes de auditar las pantallas internas
  await pagina.goto(`${BASE}/index.html`);
  await pagina.evaluate((valor) => (valor ? localStorage.setItem('stockpot_token', valor) : localStorage.removeItem('stockpot_token')),
    conSesion ? token : null);
  for (const [modo, config] of Object.entries(MODOS)) {
    let resultado;
    for (let intento = 1; intento <= 3; intento++) { // si Lighthouse no alcanza a ver la página pintada (NO_FCP), se repite
      resultado = await lighthouse(`${BASE}/${archivo}`, {
        port: puerto, output: 'html', logLevel: 'error', disableStorageReset: true, onlyCategories: CATEGORIAS,
      }, config);
      if (!resultado.lhr.runtimeError) break;
      console.log(`  (reintento ${intento}: ${resultado.lhr.runtimeError.code})`);
    }
    const base = `${archivo.replace('.html', '')}-${modo}`;
    fs.writeFileSync(path.join(CARPETA, `${base}.html`), resultado.report);
    const c = resultado.lhr.categories;
    const fila = {
      pantalla: nombre, archivo, modo,
      performance: Math.round(c.performance.score * 100),
      accessibility: Math.round(c.accessibility.score * 100),
      bestPractices: Math.round(c['best-practices'].score * 100),
      seo: Math.round(c.seo.score * 100),
      urlFinal: resultado.lhr.finalDisplayedUrl,
      fallas: Object.values(resultado.lhr.audits)
        .filter((a) => a.score !== null && a.score < 0.9 && a.scoreDisplayMode !== 'informative' && a.scoreDisplayMode !== 'notApplicable')
        .map((a) => `${a.id} (${Math.round(a.score * 100)})`),
      metricas: {
        FCP: resultado.lhr.audits['first-contentful-paint'].displayValue,
        LCP: resultado.lhr.audits['largest-contentful-paint'].displayValue,
        TBT: resultado.lhr.audits['total-blocking-time'].displayValue,
        CLS: resultado.lhr.audits['cumulative-layout-shift'].displayValue,
      },
    };
    resultados.push(fila);
    console.log(`${nombre.padEnd(30)} ${modo.padEnd(10)} P ${fila.performance} A ${fila.accessibility} BP ${fila.bestPractices} SEO ${fila.seo} ${fila.urlFinal.endsWith(archivo) ? '' : '(redirigió a ' + fila.urlFinal + ')'}`);
  }
}
resultados.sort((x, y) => PANTALLAS.findIndex((p) => p[1] === x.archivo) - PANTALLAS.findIndex((p) => p[1] === y.archivo));
fs.writeFileSync('resultados.json', JSON.stringify(resultados, null, 2));
await navegador.close();
