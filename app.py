from flask import Flask, render_template_string, request, redirect, url_for
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import json

app = Flask(__name__)

# Conexión a PostgreSQL desde variable de entorno de Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    import os
    print("=== DEBUG: Verificando DATABASE_URL ===")
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print(f"✅ DATABASE_URL encontrada: {db_url[:30]}...")  # Muestra solo inicio
    else:
        print("❌ DATABASE_URL NO está configurada")
        # Usar URL directa como respaldo temporal
        db_url = "postgresql://postgres:BKAhDzmBtJxPquRcicvZAHHATiTDcfrX@caboose.proxy.rlwy.net:58358/railway"
        print(f"🔧 Usando URL de respaldo: {db_url[:30]}...")
    
    conn = psycopg2.connect(db_url)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Crear tablas si no existen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER REFERENCES clientes(id),
            cliente TEXT NOT NULL,
            telefono TEXT,
            monto FLOAT,
            interes FLOAT,
            plazo INTEGER,
            fecha TEXT,
            fecha_vence TEXT,
            capital_actual FLOAT,
            ultima_fecha_pago TEXT,
            total_pagado FLOAT DEFAULT 0,
            total_interes_pagado FLOAT DEFAULT 0,
            estado TEXT DEFAULT 'activo'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            prestamo_id INTEGER REFERENCES prestamos(id),
            fecha TEXT,
            pago_total FLOAT,
            interes FLOAT,
            abono_capital FLOAT,
            capital_tras_pago FLOAT
        )
    """)
    cur.close()
    conn.close()

def cargar():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Cargar clientes
    cur.execute("SELECT * FROM clientes")
    clientes = cur.fetchall()
    
    # Cargar prestamos con sus pagos
    cur.execute("SELECT * FROM prestamos")
    prestamos = cur.fetchall()
    
    for p in prestamos:
        cur.execute("SELECT * FROM pagos WHERE prestamo_id = %s", (p['id'],))
        p['pagos'] = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {"clientes": clientes, "prestamos": prestamos}

def guardar(datos):
    # Esta función ya no se usa con PostgreSQL
    pass

def interes_mes(capital, tasa):
    return round(capital * (tasa / 100), 2)

BASE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sistema de Prestamos</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}
body{background:#F0F4F8;min-height:100vh}
nav{background:#1E3A5F;padding:12px 20px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
nav span{color:white;font-size:18px;font-weight:bold;margin-right:16px}
nav a{color:#AAD4F5;text-decoration:none;padding:8px 14px;border-radius:6px;font-size:14px}
nav a:hover{background:#2A4F7F;color:white}
.container{padding:20px;max-width:1100px;margin:0 auto}
h2{color:#2C3E50;margin-bottom:16px;font-size:22px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.card{background:white;border-radius:10px;padding:20px;text-align:center;border:1px solid #D1DCE8}
.card .val{font-size:26px;font-weight:bold;margin-bottom:4px}
.card .lbl{color:#7F8C8D;font-size:13px}
.green{color:#2ECC71}.blue{color:#3498DB}.orange{color:#F39C12}.red{color:#E74C3C}
table{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;border:1px solid #D1DCE8;margin-bottom:24px}
th{background:#1E3A5F;color:white;padding:10px;font-size:13px;text-align:center}
td{padding:10px;font-size:13px;text-align:center;border-bottom:1px solid #F0F4F8}
tr:hover td{background:#EBF5FB}
.form-box{background:white;border-radius:10px;padding:24px;border:1px solid #D1DCE8;max-width:500px;margin-bottom:24px}
.form-box label{display:block;font-weight:bold;color:#2C3E50;margin-bottom:4px;font-size:13px}
.form-box input,.form-box select{width:100%;padding:10px;border:1px solid #D1DCE8;border-radius:6px;margin-bottom:14px;font-size:14px}
.btn{background:#2ECC71;color:white;border:none;padding:12px 24px;border-radius:6px;font-size:15px;font-weight:bold;cursor:pointer;width:100%}
.btn:hover{background:#27AE60}
.info-box{background:#EBF5FB;border-radius:8px;padding:14px;margin-bottom:14px;font-size:13px;color:#2C3E50;line-height:1.6}
.msg{background:#D5F5E3;border:1px solid #2ECC71;color:#1E8449;padding:12px;border-radius:6px;margin-bottom:16px;font-size:14px}
.warn{background:#FEF9E7;border:1px solid #F39C12;color:#9A7D0A;padding:10px;border-radius:6px;margin-bottom:10px;font-size:13px}
.ok{background:#D5F5E3;border:1px solid #2ECC71;color:#1E8449;padding:10px;border-radius:6px;margin-bottom:10px;font-size:13px}
</style>
</head>
<body>
<nav>
  <span>💰 Prestamos</span>
  <a href="/">🏠 Inicio</a>
  <a href="/nuevo">➕ Nuevo Prestamo</a>
  <a href="/clientes">👥 Clientes</a>
  <a href="/pagos">💳 Pagos</a>
  <a href="/reportes">📊 Reportes</a>
</nav>
<div class="container">{% block content %}{% endblock %}</div>
</body></html>
"""

INICIO = BASE.replace("{% block content %}{% endblock %}", """
<h2>Panel Principal</h2>
<div class="cards">
  <div class="card"><div class="val green">${{ "{:,.0f}".format(resumen.total_prestado) }}</div><div class="lbl">Total Prestado</div></div>
  <div class="card"><div class="val blue">{{ resumen.activos }}</div><div class="lbl">Prestamos Activos</div></div>
  <div class="card"><div class="val orange">${{ "{:,.0f}".format(resumen.capital_cobrar) }}</div><div class="lbl">Capital por Cobrar</div></div>
  <div class="card"><div class="val red">{{ resumen.vencidos }}</div><div class="lbl">Vencidos</div></div>
</div>
<h2>Prestamos Activos</h2>
<table>
  <tr><th>ID</th><th>Cliente</th><th>Capital Actual</th><th>Tasa %</th><th>Interes Este Mes</th><th>Vence</th><th>Estado</th></tr>
  {% for p in activos %}
  <tr>
    <td>{{ p.id }}</td><td>{{ p.cliente }}</td>
    <td>${{ "{:,.0f}".format(p.capital_actual) }}</td>
    <td>{{ p.interes }}%</td>
    <td>${{ "{:,.0f}".format(p.interes_mes) }}</td>
    <td>{{ p.fecha_vence }}</td>
    <td>{% if p.fecha_vence < hoy %}<span class="red">Vencido</span>{% else %}<span class="blue">Activo</span>{% endif %}</td>
  </tr>
  {% endfor %}
</table>
""")

NUEVO = BASE.replace("{% block content %}{% endblock %}", """
<h2>Registrar Nuevo Prestamo</h2>
<div class="form-box">
  <div class="info-box">El interes se calcula cada mes sobre el capital que queda.<br>Si el cliente paga mas del interes, el excedente baja el capital.</div>
  <form method="POST">
    <label>Nombre del cliente</label><input name="cliente" placeholder="Ej: Maria Garcia" required>
    <label>Telefono</label><input name="telefono" placeholder="Ej: 300-123-4567">
    <label>Monto prestado ($)</label><input name="monto" type="number" step="0.01" placeholder="Ej: 500000" required>
    <label>Interes mensual (%)</label><input name="interes" type="number" step="0.01" placeholder="Ej: 5" required>
    <label>Plazo estimado (meses)</label><input name="plazo" type="number" placeholder="Ej: 6" required>
    <label>Fecha</label><input name="fecha" type="date" value="{{ hoy }}" required>
    <button class="btn" type="submit">💾 Guardar Prestamo</button>
  </form>
</div>
""")

CLIENTES = BASE.replace("{% block content %}{% endblock %}", """
<h2>Clientes</h2>
<table>
  <tr><th>ID</th><th>Nombre</th><th>Telefono</th><th>Prestamos</th><th>Capital Pendiente</th></tr>
  {% for c in clientes %}
  <tr><td>{{ c.id }}</td><td>{{ c.nombre }}</td><td>{{ c.telefono }}</td><td>{{ c.num_prestamos }}</td><td>${{ "{:,.0f}".format(c.capital) }}</td></tr>
  {% endfor %}
</table>
""")

PAGOS = BASE.replace("{% block content %}{% endblock %}", """
<h2>Registrar Pago</h2>
{% if mensaje %}<div class="msg">{{ mensaje }}</div>{% endif %}
<div class="form-box">
  <form method="POST">
    <label>Seleccionar prestamo</label>
    <select name="prestamo_id" onchange="this.form.submit()" id="sel">
      {% for p in activos %}
      <option value="{{ p.id }}" {% if sel == p.id %}selected{% endif %}>#{{ p.id }} - {{ p.cliente }} | Capital: ${{ "{:,.0f}".format(p.capital_actual) }}</option>
      {% endfor %}
    </select>
    {% if activo %}
    <div class="info-box">
      Capital actual: <b>${{ "{:,.2f}".format(activo.capital_actual) }}</b><br>
      Interes este mes: <b>${{ "{:,.2f}".format(activo.interes_mes) }}</b><br>
      Pago minimo (solo interes): <b>${{ "{:,.2f}".format(activo.interes_mes) }}</b><br>
      Si pagas mas, el excedente baja el capital y el proximo mes pagas menos interes.
    </div>
    <label>Monto del pago ($)</label>
    <input name="monto" type="number" step="0.01" placeholder="Ej: 50000" required>
    <button class="btn" type="submit" name="registrar" value="1">💳 Registrar Pago</button>
    {% endif %}
  </form>
</div>
<h2>Historial de Pagos</h2>
<table>
  <tr><th>Prestamo</th><th>Cliente</th><th>Fecha</th><th>Pago Total</th><th>Interes</th><th>Capital</th><th>Capital Restante</th></tr>
  {% for h in historial %}
  <tr>
    <td>#{{ h.pid }}</td><td>{{ h.cliente }}</td><td>{{ h.fecha }}</td>
    <td>${{ "{:,.0f}".format(h.pago_total) }}</td>
    <td>${{ "{:,.0f}".format(h.interes) }}</td>
    <td>${{ "{:,.0f}".format(h.abono_capital) }}</td>
    <td>${{ "{:,.0f}".format(h.capital_tras_pago) }}</td>
  </tr>
  {% endfor %}
</table>
""")

REPORTES = BASE.replace("{% block content %}{% endblock %}", """
<h2>Reportes</h2>
<div class="cards">
  <div class="card"><div class="val blue">{{ resumen.total }}</div><div class="lbl">Total Prestamos</div></div>
  <div class="card"><div class="val green">{{ resumen.activos }}</div><div class="lbl">Activos</div></div>
  <div class="card"><div class="val orange">{{ resumen.pagados }}</div><div class="lbl">Pagados</div></div>
  <div class="card"><div class="val red">{{ resumen.vencidos }}</div><div class="lbl">Vencidos</div></div>
  <div class="card"><div class="val green">${{ "{:,.0f}".format(resumen.capital_prestado) }}</div><div class="lbl">Capital Prestado</div></div>
  <div class="card"><div class="val orange">${{ "{:,.0f}".format(resumen.capital_cobrar) }}</div><div class="lbl">Por Cobrar</div></div>
  <div class="card"><div class="val blue">${{ "{:,.0f}".format(resumen.total_recaudado) }}</div><div class="lbl">Total Recaudado</div></div>
  <div class="card"><div class="val green">${{ "{:,.0f}".format(resumen.intereses_cobrados) }}</div><div class="lbl">Intereses Cobrados</div></div>
</div>
<h2>Todos los Prestamos</h2>
<table>
  <tr><th>ID</th><th>Cliente</th><th>Monto Inicial</th><th>Capital Actual</th><th>Tasa</th><th>Interes/Mes</th><th>Vence</th><th>Estado</th></tr>
  {% for p in prestamos %}
  <tr>
    <td>{{ p.id }}</td><td>{{ p.cliente }}</td>
    <td>${{ "{:,.0f}".format(p.monto) }}</td>
    <td>${{ "{:,.0f}".format(p.capital_actual) }}</td>
    <td>{{ p.interes }}%</td>
    <td>${{ "{:,.0f}".format(p.interes_mes) if p.estado == "activo" else "--" }}</td>
    <td>{{ p.fecha_vence }}</td>
    <td>{% if p.estado == "pagado" %}<span class="green">Pagado</span>{% elif p.fecha_vence < hoy %}<span class="red">Vencido</span>{% else %}<span class="blue">Activo</span>{% endif %}</td>
  </tr>
  {% endfor %}
</table>
""")

@app.route("/")
def inicio():
    datos = cargar()
    ps = datos["prestamos"]
    activos = [p for p in ps if p["estado"] == "activo"]
    vencidos = [p for p in activos if p.get("fecha_vence","9999-12-31") < date.today().isoformat()]
    for p in activos:
        p["interes_mes"] = interes_mes(p["capital_actual"], p["interes"])
    resumen = {
        "total_prestado": sum(p["monto"] for p in ps),
        "activos": len(activos),
        "capital_cobrar": sum(p["capital_actual"] for p in activos),
        "vencidos": len(vencidos),
    }
    return render_template_string(INICIO, activos=activos, resumen=resumen, hoy=date.today().isoformat())

@app.route("/nuevo", methods=["GET","POST"])
def nuevo():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        
        nombre = request.form["cliente"].strip()
        tel = request.form["telefono"].strip()
        monto = float(request.form["monto"])
        tasa = float(request.form["interes"])
        plazo = int(request.form["plazo"])
        fecha = request.form["fecha"]
        
        # Buscar o crear cliente
        cur.execute("SELECT id FROM clientes WHERE nombre = %s", (nombre,))
        cliente = cur.fetchone()
        
        if cliente:
            cid = cliente[0]
        else:
            cur.execute("INSERT INTO clientes (nombre, telefono) VALUES (%s, %s) RETURNING id", (nombre, tel))
            cid = cur.fetchone()[0]
        
        fecha_vence = (datetime.strptime(fecha, "%Y-%m-%d") + relativedelta(months=plazo)).strftime("%Y-%m-%d")
        
        cur.execute("""
            INSERT INTO prestamos 
            (cliente_id, cliente, telefono, monto, interes, plazo, fecha, fecha_vence, capital_actual, total_pagado, total_interes_pagado, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (cid, nombre, tel, monto, tasa, plazo, fecha, fecha_vence, monto, 0, 0, 'activo'))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for("inicio"))
    return render_template_string(NUEVO, hoy=date.today().isoformat())

@app.route("/clientes")
def clientes():
    datos = cargar()
    lista = []
    for c in datos["clientes"]:
        ps = [p for p in datos["prestamos"] if p["cliente_id"] == c["id"]]
        cap = sum(p["capital_actual"] for p in ps if p["estado"] == "activo")
        lista.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "telefono": c.get("telefono", ""),
            "num_prestamos": len(ps),
            "capital": cap
        })
    return render_template_string(CLIENTES, clientes=lista)

@app.route("/pagos", methods=["GET","POST"])
def pagos():
    datos = cargar()
    activos = [p for p in datos["prestamos"] if p["estado"] == "activo"]
    for p in activos:
        p["interes_mes"] = interes_mes(p["capital_actual"], p["interes"])
    
    sel = None
    if activos:
        sel = int(request.form.get("prestamo_id", activos[0]["id"]))
    
    activo = next((p for p in activos if p["id"] == sel), None)
    
    if request.method == "POST" and "registrar" in request.form:
        conn = get_db()
        cur = conn.cursor()
        
        pago = float(request.form["monto"])
        i = interes_mes(activo["capital_actual"], activo["interes"])
        
        if pago >= i:
            abono = round(pago - i, 2)
            int_pag = i
            nuevo_capital = round(max(activo["capital_actual"] - abono, 0), 2)
        else:
            abono = 0
            int_pag = pago
            nuevo_capital = activo["capital_actual"]
        
        total_pagado = activo["total_pagado"] + pago
        total_interes = activo["total_interes_pagado"] + int_pag
        estado = 'pagado' if nuevo_capital <= 0 else 'activo'
        
        # Actualizar préstamo
        cur.execute("""
            UPDATE prestamos SET 
                capital_actual = %s,
                total_pagado = %s,
                total_interes_pagado = %s,
                ultima_fecha_pago = %s,
                estado = %s
            WHERE id = %s
        """, (nuevo_capital, total_pagado, total_interes, date.today().isoformat(), estado, sel))
        
        # Registrar pago
        cur.execute("""
            INSERT INTO pagos 
            (prestamo_id, fecha, pago_total, interes, abono_capital, capital_tras_pago)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (sel, date.today().isoformat(), pago, int_pag, abono, nuevo_capital))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for("pagos"))
    
    historial = []
    for p in datos["prestamos"]:
        for pg in p.get("pagos", []):
            historial.append({
                "pid": p["id"],
                "cliente": p["cliente"],
                "fecha": pg["fecha"],
                "pago_total": pg["pago_total"],
                "interes": pg["interes"],
                "abono_capital": pg["abono_capital"],
                "capital_tras_pago": pg["capital_tras_pago"]
            })
    historial.sort(key=lambda x: x["fecha"], reverse=True)
    
    return render_template_string(PAGOS, activos=activos, activo=activo, historial=historial, sel=sel)

@app.route("/reportes")
def reportes():
    datos = cargar()
    ps = datos["prestamos"]
    activos = [p for p in ps if p["estado"] == "activo"]
    pagados = [p for p in ps if p["estado"] == "pagado"]
    vencidos = [p for p in activos if p.get("fecha_vence","9999-12-31") < date.today().isoformat()]
    
    for p in ps:
        p["interes_mes"] = interes_mes(p["capital_actual"], p["interes"]) if p["estado"] == "activo" else 0
    
    resumen = {
        "total": len(ps),
        "activos": len(activos),
        "pagados": len(pagados),
        "vencidos": len(vencidos),
        "capital_prestado": sum(p["monto"] for p in ps),
        "capital_cobrar": sum(p["capital_actual"] for p in activos),
        "total_recaudado": sum(p["total_pagado"] for p in ps),
        "intereses_cobrados": sum(p["total_interes_pagado"] for p in ps),
    }
    return render_template_string(REPORTES, prestamos=ps, resumen=resumen, hoy=date.today().isoformat())

if __name__ == "__main__":
    # Inicializar base de datos
    print("🔄 Inicializando base de datos...")
    init_db()
    print("✅ Base de datos inicializada")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)