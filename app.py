import os, io, json, requests, base64, time, uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from collections import deque
import threading

# Cola de CVs pendientes de notificación
# Estructura: {"id": ..., "ts": ..., "datos": ..., "pdf_b64": ..., "notificado": False}
_cv_lock  = threading.Lock()
_cv_queue = deque(maxlen=50)   # últimos 50 CVs

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

WPP_API   = os.environ.get("WPP_API_URL", "")
WPP_TOKEN = os.environ.get("WPP_TOKEN", "")
IMPRENTA_JID = os.environ.get("IMPRENTA_JID", "5493876328815@s.whatsapp.net")

COLOR_MAP = {
    "negro":        (0.17, 0.17, 0.17),
    "azulmarino":   (0.10, 0.14, 0.49),
    "azul":         (0.08, 0.39, 0.75),
    "verdepetroleo":(0.00, 0.38, 0.39),
    "verde":        (0.18, 0.49, 0.20),
    "violeta":      (0.42, 0.11, 0.60),
    "rosa":         (0.68, 0.08, 0.34),
    "rojo":         (0.72, 0.11, 0.11),
    "naranja":      (0.90, 0.32, 0.00),
    "marron":       (0.31, 0.20, 0.18),
    "gris":         (0.22, 0.28, 0.31),
}

def val(d, k):
    return str(d.get(k, "") or "").strip()

def rgb(t):
    return colors.Color(t[0], t[1], t[2])

def make_cv_pdf(d: dict) -> bytes:
    buf = io.BytesIO()
    W, H = A4  # 595 x 842 pts

    col_color = COLOR_MAP.get(d.get("color", "negro"), COLOR_MAP["negro"])
    accent    = rgb(col_color)

    c = canvas.Canvas(buf, pagesize=A4)

    LEFT_W  = 160   # ancho columna izquierda
    PAD     = 12    # padding general
    RIGHT_X = LEFT_W + PAD

    # ── Fondo columna izquierda ──────────────────────────────
    c.setFillColor(accent)
    c.rect(0, 0, LEFT_W, H, fill=1, stroke=0)

    # ── Fondo columna derecha ─────────────────────────────────
    c.setFillColor(colors.white)
    c.rect(LEFT_W, 0, W - LEFT_W, H, fill=1, stroke=0)

    # ── Footer strip ──────────────────────────────────────────
    FOOTER_H = 18
    c.setFillColor(colors.Color(0.97, 0.97, 0.97))
    c.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)
    c.setFillColor(colors.Color(0.6, 0.6, 0.6))
    c.setFont("Helvetica", 7)
    c.drawCentredString(W/2, 6, "🖨  Imprenta Ruiz · Chacabuco 470, Salta · WhatsApp: 387-632-8815")

    # ─── COLUMNA IZQUIERDA ────────────────────────────────────
    y = H - 20

    # Icono persona
    c.setFillColor(colors.Color(1,1,1,0.15))
    c.circle(LEFT_W/2, y - 40, 38, fill=1, stroke=0)
    c.setFillColor(colors.Color(1,1,1,0.5))
    c.setFont("Helvetica", 22)
    c.drawCentredString(LEFT_W/2, y - 45, "👤")

    y -= 95

    def left_section(title, cur_y):
        cur_y -= 8
        c.setFillColor(colors.Color(1,1,1,0.25))
        c.rect(PAD, cur_y - 2, LEFT_W - 2*PAD, 0.5, fill=1, stroke=0)
        cur_y -= 10
        c.setFillColor(colors.Color(1,1,1,0.55))
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(PAD, cur_y, title.upper())
        return cur_y - 8

    def left_field(label, value, cur_y):
        if not value:
            return cur_y
        c.setFillColor(colors.Color(1,1,1,0.45))
        c.setFont("Helvetica", 6)
        c.drawString(PAD, cur_y, label.upper())
        cur_y -= 9
        c.setFillColor(colors.Color(0.9,0.9,0.9))
        c.setFont("Helvetica", 8)
        # wrap largo
        if len(value) > 26:
            value = value[:26] + "…"
        c.drawString(PAD, cur_y, value)
        return cur_y - 11

    # Sobre mí
    sobre = val(d, "sobre_mi")
    if sobre:
        y = left_section("Sobre mí", y)
        c.setFillColor(colors.Color(0.85, 0.85, 0.85))
        c.setFont("Helvetica", 7.5)
        words = sobre.split()
        line, lines = "", []
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 7.5) < LEFT_W - 2*PAD:
                line = test
            else:
                lines.append(line); line = w
        if line: lines.append(line)
        for ln in lines[:4]:
            c.drawString(PAD, y, ln); y -= 10

    # Datos personales
    y = left_section("Datos personales", y)
    y = left_field("Fecha de nacimiento", val(d, "fecha_nac"), y)
    y = left_field("Nacionalidad",        val(d, "nacionalidad"), y)
    y = left_field("Estado civil",        val(d, "estado_civil"), y)
    y = left_field("CUIL",                val(d, "cuil"), y)

    # Idiomas
    langs = [val(d, f"idioma{i}") for i in range(1,4) if val(d, f"idioma{i}")]
    if langs:
        y = left_section("Idiomas", y)
        BAR_WIDTHS = [LEFT_W - 2*PAD, int((LEFT_W-2*PAD)*0.5), int((LEFT_W-2*PAD)*0.25)]
        for i, lang in enumerate(langs[:3]):
            c.setFillColor(colors.Color(0.85,0.85,0.85))
            c.setFont("Helvetica", 8)
            c.drawString(PAD, y, lang)
            y -= 8
            bw = BAR_WIDTHS[i] if i < len(BAR_WIDTHS) else BAR_WIDTHS[-1]
            c.setFillColor(colors.Color(1,1,1,0.2))
            c.rect(PAD, y, LEFT_W - 2*PAD, 3, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.rect(PAD, y, bw, 3, fill=1, stroke=0)
            y -= 9

    # Licencia
    lic = val(d, "licencia")
    if lic:
        y = left_section("Licencia de conducir", y)
        y = left_field("Categoría", lic, y)

    # ─── COLUMNA DERECHA ──────────────────────────────────────
    y_r = H - 28
    RX  = RIGHT_X + LEFT_W  # x real en página = LEFT_W + PAD + LEFT_W??? No
    # La columna derecha empieza en x = LEFT_W + PAD  (=172 pts ~60.7mm)
    RX  = LEFT_W + PAD
    RW  = W - RX - PAD      # ancho útil derecha

    # Nombre y profesión
    nombre = val(d, "nombre") or "Tu Nombre"
    prof   = val(d, "profesion")

    c.setFillColor(colors.Color(0.13,0.13,0.13))
    font_size = 24 if len(nombre) < 20 else 18
    c.setFont("Helvetica-Bold", font_size)
    c.drawString(RX, y_r, nombre)
    y_r -= font_size + 4

    if prof:
        c.setFillColor(colors.Color(0.45,0.45,0.45))
        c.setFont("Helvetica", 11)
        c.drawString(RX, y_r, prof)
        y_r -= 14

    # Contacto
    contact_items = []
    ciudad   = val(d, "ciudad") or "Salta, Argentina"
    telefono = val(d, "telefono")
    email    = val(d, "email")
    if ciudad:   contact_items.append(f"📍 {ciudad}")
    if telefono: contact_items.append(f"📞 {telefono}")
    if email:    contact_items.append(f"✉  {email}")

    c.setFillColor(colors.Color(0.4,0.4,0.4))
    c.setFont("Helvetica", 8)
    cx = RX
    for item in contact_items:
        iw = c.stringWidth(item, "Helvetica", 8)
        if cx + iw > W - PAD:
            break
        c.drawString(cx, y_r, item)
        cx += iw + 16
    y_r -= 16

    # Línea separadora
    c.setStrokeColor(colors.Color(0.88,0.88,0.88))
    c.line(RX, y_r, W - PAD, y_r)
    y_r -= 12

    def right_section(title, cur_y):
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(RX, cur_y, title.upper())
        cur_y -= 3
        c.setStrokeColor(accent)
        c.setLineWidth(1.5)
        c.line(RX, cur_y, W - PAD, cur_y)
        c.setLineWidth(0.5)
        return cur_y - 10

    def right_entry(empresa, cargo, ciudad_e, periodo, desc, cur_y):
        if cur_y < FOOTER_H + 20:
            return cur_y
        # Bullet
        c.setFillColor(accent)
        c.circle(RX + 4, cur_y + 3, 3, fill=1, stroke=0)
        # Cargo
        c.setFillColor(colors.Color(0.13,0.13,0.13))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(RX + 12, cur_y, cargo or "—")
        cur_y -= 11
        # Empresa / periodo
        meta = " · ".join(filter(None, [empresa, ciudad_e, periodo]))
        if meta:
            c.setFillColor(colors.Color(0.5,0.5,0.5))
            c.setFont("Helvetica", 7.5)
            c.drawString(RX + 12, cur_y, meta[:70])
            cur_y -= 10
        # Descripción
        if desc:
            c.setFillColor(colors.Color(0.4,0.4,0.4))
            c.setFont("Helvetica", 7.5)
            words = desc.split()
            line, lines = "", []
            for w in words:
                test = (line + " " + w).strip()
                if c.stringWidth(test, "Helvetica", 7.5) < RW - 16:
                    line = test
                else:
                    lines.append(line); line = w
            if line: lines.append(line)
            for ln in lines[:3]:
                c.drawString(RX + 12, cur_y, ln); cur_y -= 9
        return cur_y - 6

    # Experiencia
    exps = [(val(d,f"exp{i}_empresa"), val(d,f"exp{i}_cargo"),
             val(d,f"exp{i}_ciudad"),  val(d,f"exp{i}_periodo"),
             val(d,f"exp{i}_desc"))    for i in range(1,4)
            if val(d,f"exp{i}_empresa") or val(d,f"exp{i}_cargo")]
    if exps:
        y_r = right_section("Experiencia Laboral", y_r)
        for emp, cargo, ciu, per, desc in exps:
            y_r = right_entry(emp, cargo, ciu, per, desc, y_r)
        y_r -= 4

    # Educación
    edus = [(val(d,f"edu{i}_inst"),   val(d,f"edu{i}_titulo"),
             val(d,f"edu{i}_ciudad"), val(d,f"edu{i}_periodo"),
             val(d,f"edu{i}_desc"))   for i in range(1,3)
            if val(d,f"edu{i}_inst") or val(d,f"edu{i}_titulo")]
    if edus:
        y_r = right_section("Educación", y_r)
        for inst, titulo, ciu, per, desc in edus:
            y_r = right_entry(inst, titulo, ciu, per, desc, y_r)
        y_r -= 4

    # Habilidades
    skills = [val(d, f"skill{i}") for i in range(1,7) if val(d, f"skill{i}")]
    if skills:
        y_r = right_section("Habilidades", y_r)
        SKILL_PCTS = [0.9, 0.8, 0.7, 0.6, 1.0, 0.75]
        col_w = (RW - 8) / 2
        for idx, sk in enumerate(skills):
            col_x = RX + (col_w + 8) * (idx % 2)
            row_y = y_r - (idx // 2) * 20
            c.setFillColor(colors.Color(0.35,0.35,0.35))
            c.setFont("Helvetica", 7.5)
            c.drawString(col_x, row_y, sk.upper()[:22])
            row_y -= 7
            # barra fondo
            c.setFillColor(colors.Color(0.9,0.9,0.9))
            c.rect(col_x, row_y, col_w - 8, 3, fill=1, stroke=0)
            # barra relleno
            c.setFillColor(accent)
            pct = SKILL_PCTS[idx % len(SKILL_PCTS)]
            c.rect(col_x, row_y, (col_w - 8) * pct, 3, fill=1, stroke=0)
        rows = (len(skills) + 1) // 2
        y_r -= rows * 20 + 4

    c.save()
    buf.seek(0)
    return buf.read()


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

    try:
        pdf_bytes = make_cv_pdf(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    nombre   = (data.get("nombre") or "cv").strip().replace(" ", "_")
    filename = f"CV_{nombre}.pdf"

    # Guardar en cola para notificacion WhatsApp
    pdf_b64 = base64.b64encode(pdf_bytes).decode()
    entry = {
        "id":        str(uuid.uuid4())[:8],
        "ts":        int(time.time()),
        "nombre":    data.get("nombre", "\u2014"),
        "profesion": data.get("profesion", "\u2014"),
        "telefono":  data.get("telefono", "\u2014"),
        "color":     data.get("color", "negro"),
        "combo":     data.get("combo", "Sin especificar"),
        "pdf_b64":   pdf_b64,
        "filename":  filename,
        "notificado": False,
    }
    with _cv_lock:
        _cv_queue.append(entry)
    print(f"CV en cola: id={entry['id']} nombre={entry['nombre']}")

    pdf_io = io.BytesIO(pdf_bytes)
    pdf_io.seek(0)
    response = send_file(
        pdf_io,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
    response.headers["X-CV-ID"] = entry["id"]
    response.headers["X-WPP-Enviado"] = "pendiente"
    return response


@app.route("/cv-pendientes", methods=["GET"])
def cv_pendientes():
    secret = os.environ.get("POLL_SECRET", "ruiz2024")
    if request.args.get("secret") != secret:
        return jsonify({"error": "unauthorized"}), 401
    with _cv_lock:
        pendientes = [
            {"id":e["id"],"ts":e["ts"],"nombre":e["nombre"],"profesion":e["profesion"],
             "telefono":e["telefono"],"color":e["color"],"combo":e["combo"],"filename":e["filename"]}
            for e in _cv_queue if not e["notificado"]
        ]
    return jsonify({"pendientes": pendientes})


@app.route("/cv-pdf/<cv_id>", methods=["GET"])
def cv_pdf_by_id(cv_id):
    secret = os.environ.get("POLL_SECRET", "ruiz2024")
    if request.args.get("secret") != secret:
        return jsonify({"error": "unauthorized"}), 401
    with _cv_lock:
        entry = next((e for e in _cv_queue if e["id"] == cv_id), None)
    if not entry:
        return jsonify({"error": "not found"}), 404
    pdf_io = io.BytesIO(base64.b64decode(entry["pdf_b64"]))
    return send_file(pdf_io, mimetype="application/pdf",
                     as_attachment=True, download_name=entry["filename"])


@app.route("/cv-marcar/<cv_id>", methods=["POST"])
def cv_marcar_notificado(cv_id):
    secret = os.environ.get("POLL_SECRET", "ruiz2024")
    if request.args.get("secret") != secret:
        return jsonify({"error": "unauthorized"}), 401
    with _cv_lock:
        for e in _cv_queue:
            if e["id"] == cv_id:
                e["notificado"] = True
                return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
