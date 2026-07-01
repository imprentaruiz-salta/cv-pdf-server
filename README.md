# CV PDF Generator — Imprenta Ruiz

Servidor Flask que recibe datos de CV en JSON, genera el PDF con WeasyPrint y lo devuelve para descarga.

## Deploy en Render.com (gratis)

1. Subir esta carpeta a GitHub
2. Crear nuevo Web Service en render.com → conectar repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`

## Variables de entorno opcionales (para envío automático por WhatsApp)

- `WPP_API_URL` — URL de la API de WhatsApp
- `WPP_TOKEN` — Token de autenticación
- `IMPRENTA_JID` — JID de WhatsApp destino (default: 5493876328815@s.whatsapp.net)

## Endpoint

`POST /generar-cv` con JSON:
```json
{
  "nombre": "Juan Pérez",
  "profesion": "Contador",
  "color": "azulmarino",
  "combo": "Diseño + 1 Color ($3.900)",
  "sobre_mi": "...",
  "fecha_nac": "01/01/1995",
  "nacionalidad": "Argentina",
  "estado_civil": "Soltero",
  "cuil": "20-12345678-9",
  "ciudad": "Salta",
  "telefono": "387-000-0000",
  "email": "juan@email.com",
  "licencia": "B",
  "exp1_empresa": "Empresa SA",
  "exp1_cargo": "Gerente",
  "exp1_ciudad": "Salta",
  "exp1_periodo": "2020 - Actual",
  "exp1_desc": "...",
  "edu1_inst": "UNSa",
  "edu1_titulo": "Lic. Contabilidad",
  "edu1_ciudad": "Salta",
  "edu1_periodo": "2015-2020",
  "idioma1": "Español",
  "idioma2": "Inglés",
  "skill1": "Excel",
  "skill2": "Contabilidad"
}
```
Devuelve el PDF listo para descargar.
