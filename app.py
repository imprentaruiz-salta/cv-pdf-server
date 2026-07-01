import os, io, json, requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from weasyprint import HTML, CSS

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

WPP_API   = os.environ.get("WPP_API_URL", "")
WPP_TOKEN = os.environ.get("WPP_TOKEN", "")
IMPRENTA_JID = os.environ.get("IMPRENTA_JID", "5493876328815@s.whatsapp.net")

COLOR_MAP = {
    "negro":        "#2c2c2c",
    "azulmarino":   "#1a237e",
    "azul":         "#1565c0",
    "verdepetroleo":"#006064",
    "verde":        "#2e7d32",
    "violeta":      "#6a1b9a",
    "rosa":         "#ad1457",
    "rojo":         "#b71c1c",
    "naranja":      "#e65100",
    "marron":       "#4e342e",
    "gris":         "#37474f",
}

def build_cv_html(d: dict) -> str:
    color = COLOR_MAP.get(d.get("color", "negro"), "#2c2c2c")

    def val(k, default=""):
        return str(d.get(k, default) or "").strip()

    # Experiencias (hasta 3)
    exp_html = ""
    for i in range(1, 4):
        empresa = val(f"exp{i}_empresa")
        if not empresa:
            continue
        exp_html += f"""
        <div class="cv-entry">
          <div class="cv-entry-left">
            <div class="co">{empresa}</div>
            <div class="ci">{val(f'exp{i}_ciudad')}</div>
            <div class="pe">{val(f'exp{i}_periodo')}</div>
          </div>
          <div class="cv-entry-right">
            <div class="title-row"><div class="cargo">{val(f'exp{i}_cargo')}</div></div>
            <div class="desc">{val(f'exp{i}_desc')}</div>
          </div>
        </div>"""

    # Educación (hasta 2)
    edu_html = ""
    for i in range(1, 3):
        inst = val(f"edu{i}_inst")
        if not inst:
            continue
        edu_html += f"""
        <div class="cv-entry">
          <div class="cv-entry-left">
            <div class="co">{inst}</div>
            <div class="ci">{val(f'edu{i}_ciudad')}</div>
            <div class="pe">{val(f'edu{i}_periodo')}</div>
          </div>
          <div class="cv-entry-right">
            <div class="title-row"><div class="cargo">{val(f'edu{i}_titulo')}</div></div>
            <div class="desc">{val(f'edu{i}_desc')}</div>
          </div>
        </div>"""

    # Habilidades (hasta 6)
    skills_html = ""
    skill_pcts = [90, 80, 70, 60, 100, 75]
    for i in range(1, 7):
        sk = val(f"skill{i}")
        if not sk:
            continue
        pct = skill_pcts[i-1]
        skills_html += f"""
        <div class="skill-item">
          <div class="sk-name">{sk}</div>
          <div class="skill-bar-wrap"><div class="skill-bar" style="width:{pct}%"></div></div>
        </div>"""

    # Idiomas (hasta 3)
    idiomas_html = ""
    lang_pcts = [100, 50, 25]
    for i in range(1, 4):
        lang = val(f"idioma{i}")
        if not lang:
            continue
        pct = lang_pcts[i-1]
        idiomas_html += f"""
        <div class="lang-item">
          <div class="lang-name">{lang}</div>
          <div class="lang-bar-wrap"><div class="lang-bar" style="width:{pct}%"></div></div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: Arial, sans-serif; background:#fff; color:#222; }}
.cv-container {{
  width: 794px; min-height: 1060px;
  background:#fff;
  display: grid; grid-template-columns: 220px 1fr;
}}
.cv-left {{ background:{color}; color:#fff; padding:28px 18px; }}
.photo-circle {{
  width:90px; height:90px; border-radius:50%;
  background:rgba(255,255,255,0.15);
  border:3px solid rgba(255,255,255,0.3);
  margin:0 auto 18px;
  display:flex; align-items:center; justify-content:center;
  font-size:11px; color:rgba(255,255,255,0.6); text-align:center;
}}
.cv-left h2 {{
  font-size:9px; letter-spacing:2px; color:rgba(255,255,255,0.6);
  text-transform:uppercase; border-bottom:1px solid rgba(255,255,255,0.25);
  padding-bottom:4px; margin:16px 0 8px;
}}
.field-label {{ font-size:9px; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:1px; margin-top:8px; }}
.field-value {{ font-size:11px; color:#ddd; margin-top:2px; padding-bottom:3px; border-bottom:1px dotted rgba(255,255,255,0.2); min-height:16px; }}
.lang-item {{ margin-bottom:8px; }}
.lang-name {{ font-size:10px; color:#ccc; text-transform:uppercase; letter-spacing:1px; padding-bottom:2px; }}
.lang-bar-wrap {{ background:rgba(255,255,255,0.2); height:3px; border-radius:2px; margin-top:4px; }}
.lang-bar {{ background:#fff; height:3px; border-radius:2px; }}
.sobre-mi {{ font-size:11px; color:#ddd; line-height:1.5; }}

.cv-right {{ padding:28px 26px; }}
.cv-name {{ font-size:32px; font-weight:900; color:#222; line-height:1.1; margin-bottom:4px; }}
.cv-role {{ font-size:13px; color:#666; margin-bottom:14px; }}
.contact-row {{ display:flex; gap:16px; margin-bottom:18px; flex-wrap:wrap; }}
.contact-item {{ display:flex; align-items:center; gap:5px; font-size:11px; color:#555; }}

.cv-section {{ margin-bottom:18px; }}
.cv-section-title {{
  font-size:10px; font-weight:800; letter-spacing:2px;
  text-transform:uppercase; color:{color};
  border-bottom:2px solid {color}; padding-bottom:4px; margin-bottom:12px;
}}
.cv-entry {{ display:grid; grid-template-columns:150px 1fr; gap:8px; margin-bottom:12px; }}
.cv-entry-left {{ font-size:10px; color:#888; }}
.co {{ font-weight:700; color:#444; font-size:11px; margin-bottom:2px; }}
.ci, .pe {{ color:#888; font-size:10px; margin-bottom:1px; }}
.title-row {{ display:flex; align-items:center; gap:6px; margin-bottom:4px; }}
.title-row::before {{ content:''; width:7px; height:7px; border-radius:50%; background:{color}; flex-shrink:0; }}
.cargo {{ font-size:12px; font-weight:700; color:#222; }}
.desc {{ font-size:10px; color:#666; line-height:1.5; margin-left:13px; }}

.skills-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:6px 16px; }}
.sk-name {{ font-size:10px; color:#555; text-transform:uppercase; letter-spacing:1px; margin-bottom:3px; }}
.skill-bar-wrap {{ background:#eee; height:3px; border-radius:2px; }}
.skill-bar {{ background:{color}; height:3px; border-radius:2px; }}

.cv-footer-strip {{
  grid-column:1/-1; background:#f8f8f8;
  text-align:center; padding:6px;
  font-size:9px; color:#aaa; border-top:1px solid #eee;
}}
</style>
</head>
<body>
<div class="cv-container">
  <div class="cv-left">
    <div class="photo-circle">📷</div>

    <h2>Sobre mí</h2>
    <div class="sobre-mi">{val('sobre_mi')}</div>

    <h2>Datos Personales</h2>
    <div class="field-label">Fecha de nacimiento</div>
    <div class="field-value">{val('fecha_nac')}</div>
    <div class="field-label">Nacionalidad</div>
    <div class="field-value">{val('nacionalidad')}</div>
    <div class="field-label">Estado Civil</div>
    <div class="field-value">{val('estado_civil')}</div>
    <div class="field-label">CUIL</div>
    <div class="field-value">{val('cuil')}</div>

    <h2>Idiomas</h2>
    {idiomas_html if idiomas_html else '<div class="field-value" style="font-style:italic;color:rgba(255,255,255,0.4)">—</div>'}

    <h2>Permiso de Conducir</h2>
    <div class="field-label">Categoría</div>
    <div class="field-value">{val('licencia')}</div>
  </div>

  <div class="cv-right">
    <div class="cv-name">{val('nombre')}</div>
    <div class="cv-role">{val('profesion')}</div>
    <div class="contact-row">
      <div class="contact-item">📍 {val('ciudad', 'Salta, Argentina')}</div>
      <div class="contact-item">📞 {val('telefono')}</div>
      <div class="contact-item">✉️ {val('email')}</div>
    </div>

    <div class="cv-section">
      <div class="cv-section-title">Experiencia Laboral</div>
      {exp_html if exp_html else '<p style="font-size:11px;color:#aaa;font-style:italic;">—</p>'}
    </div>

    <div class="cv-section">
      <div class="cv-section-title">Educación</div>
      {edu_html if edu_html else '<p style="font-size:11px;color:#aaa;font-style:italic;">—</p>'}
    </div>

    <div class="cv-section">
      <div class="cv-section-title">Habilidades</div>
      <div class="skills-grid">
        {skills_html if skills_html else '<p style="font-size:11px;color:#aaa;font-style:italic;">—</p>'}
      </div>
    </div>
  </div>

  <div class="cv-footer-strip">
    🖨️ Imprenta Ruiz · Chacabuco 470, Salta · WhatsApp: 387-632-8815
  </div>
</div>
</body>
</html>"""


@app.route("/")
def index():
    return send_file("static/index.html")

@app.route("/cv")
def cv():
    return send_file("static/index.html")


@app.route("/ping")
def ping():
    return jsonify({"ok": True})


@app.route("/generar-cv", methods=["POST"])
def generar_cv():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "JSON inválido"}), 400

    html_str = build_cv_html(data)
    pdf_bytes = HTML(string=html_str).write_pdf()

    nombre = (data.get("nombre") or "cv").strip().replace(" ", "_")
    filename = f"CV_{nombre}.pdf"

    # Mandar por WhatsApp si hay credenciales configuradas
    wpp_enviado = False
    if WPP_API and WPP_TOKEN:
        try:
            import base64
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            combo = data.get("combo", "Sin especificar")
            caption = (f"📄 *CV nuevo recibido*\n"
                       f"👤 {data.get('nombre','—')}\n"
                       f"💼 {data.get('profesion','—')}\n"
                       f"📲 {data.get('telefono','—')}\n"
                       f"🎨 Color: {data.get('color','negro')}\n"
                       f"📦 Combo: {combo}")
            payload = {
                "jid": IMPRENTA_JID,
                "type": "document",
                "data": pdf_b64,
                "filename": filename,
                "caption": caption,
            }
            r = requests.post(
                f"{WPP_API}/send-document",
                json=payload,
                headers={"Authorization": f"Bearer {WPP_TOKEN}"},
                timeout=30,
            )
            wpp_enviado = r.status_code == 200
        except Exception as e:
            print(f"Error WPP: {e}")

    # Devolver el PDF al cliente también
    pdf_io = io.BytesIO(pdf_bytes)
    pdf_io.seek(0)
    response = send_file(
        pdf_io,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
    response.headers["X-WPP-Enviado"] = "si" if wpp_enviado else "no"
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
