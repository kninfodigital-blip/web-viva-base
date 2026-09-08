// Formulario de contacto → email del CLIENTE (Gmail del cliente con contraseña de aplicación).
// Receta: skill «formulario-web-a-gmail». Variables de entorno en Vercel (nunca en el repo):
//   GMAIL_USER      cuenta Gmail que envía (la del cliente o una del negocio)
//   GMAIL_APP_PASS  contraseña de aplicación de esa cuenta (16 letras)
//   TO_EMAIL        (opcional) destinatario si es distinto de GMAIL_USER
//   SUBJECT_PREFIX  (opcional) prefijo del asunto, p. ej. "[Web Clínica]"
import nodemailer from 'nodemailer';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const limpio = (v, n) => String(v ?? '').trim().slice(0, n);

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Método no permitido' });
  const { GMAIL_USER, GMAIL_APP_PASS, TO_EMAIL, SUBJECT_PREFIX } = process.env;
  if (!GMAIL_USER || !GMAIL_APP_PASS) return res.status(503).json({ error: 'Formulario no configurado: faltan GMAIL_USER y GMAIL_APP_PASS en Vercel' });

  let b = req.body;
  if (typeof b === 'string') { try { b = JSON.parse(b); } catch { return res.status(400).json({ error: 'JSON inválido' }); } }
  b = b || {};
  if (b.web) return res.status(200).json({ ok: true }); // honeypot: los bots lo rellenan, las personas no
  const nombre = limpio(b.nombre, 120), telefono = limpio(b.telefono, 40), email = limpio(b.email, 254), mensaje = limpio(b.mensaje, 3000), pagina = limpio(b.pagina, 200);
  const telOk = telefono.replace(/\D/g, '').length >= 7;
  const emailOk = !email || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
  if (nombre.length < 2 || !telOk || mensaje.length < 5 || !emailOk) return res.status(400).json({ error: 'Faltan datos: nombre, teléfono válido y mensaje' });

  const transporter = nodemailer.createTransport({ service: 'Gmail', auth: { user: GMAIL_USER, pass: GMAIL_APP_PASS } });
  const fila = (k, v) => `<tr><td style="padding:8px 0;border-bottom:1px solid #e5e7eb;font-weight:700;width:120px;vertical-align:top">${k}</td><td style="padding:8px 0;border-bottom:1px solid #e5e7eb">${v}</td></tr>`;
  const html = `<div style="font-family:Arial,sans-serif;max-width:600px"><h2 style="margin:0 0 16px">Nuevo mensaje desde la web</h2><table style="width:100%;border-collapse:collapse">${fila('Nombre', esc(nombre))}${fila('Teléfono', `<a href="tel:${esc(telefono)}">${esc(telefono)}</a>`)}${email ? fila('Email', `<a href="mailto:${esc(email)}">${esc(email)}</a>`) : ''}${fila('Mensaje', esc(mensaje).replace(/\n/g, '<br>'))}${pagina ? fila('Página', esc(pagina)) : ''}</table></div>`;
  try {
    await transporter.sendMail({ from: `"Web" <${GMAIL_USER}>`, to: TO_EMAIL || GMAIL_USER, replyTo: email || undefined, subject: `${SUBJECT_PREFIX ? SUBJECT_PREFIX + ' ' : ''}Nuevo mensaje de ${nombre} (${telefono})`, html });
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error('send-email:', e && e.message);
    return res.status(500).json({ error: 'No se pudo enviar el email' });
  }
}
