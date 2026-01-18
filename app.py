from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'barber_secret'

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect('database.db')

# ---------------- CREAR TABLAS ----------------
with get_db() as db:
    db.execute("""
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            fecha TEXT,
            hora TEXT,
            precio INTEGER,
            estado TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servicio TEXT,
            valor INTEGER
        )
    """)
    db.commit()

# Insertar precios iniciales si no existen
with get_db() as db:
    cantidad = db.execute("SELECT COUNT(*) FROM precios").fetchone()[0]
    if cantidad == 0:
        db.execute("INSERT INTO precios (servicio, valor) VALUES ('Corte', 20000)")
        db.execute("INSERT INTO precios (servicio, valor) VALUES ('Barba', 15000)")
        db.execute("INSERT INTO precios (servicio, valor) VALUES ('Corte + Barba', 30000)")
        db.commit()

# ---------------- FORMATO FECHA / HORA ----------------
def fecha_bonita(fecha):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    f = datetime.strptime(fecha, "%Y-%m-%d")
    return f"{f.day} de {meses[f.month - 1]} de {f.year}"

def hora_bonita(hora):
    try:
        return datetime.strptime(hora, "%H:%M").strftime("%I:%M %p")
    except:
        return hora

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form.get('password')

        session.clear()

        if usuario == 'barbero':
            if password == '1234':
                session['rol'] = 'barbero'
                return redirect('/barbero')
            else:
                return "Contraseña incorrecta"
        else:
            session['rol'] = 'cliente'
            session['cliente'] = usuario
            return redirect('/cliente')

    return render_template('login.html')

# ---------------- CLIENTE ----------------
@app.route('/cliente')
def cliente():
    if session.get('rol') != 'cliente':
        return redirect('/')

    db = get_db()
    rows = db.execute(
        "SELECT * FROM citas WHERE cliente=?",
        (session['cliente'],)
    ).fetchall()

    citas = []
    for c in rows:
        citas.append({
            "id": c[0],
            "fecha": fecha_bonita(c[2]),
            "hora": hora_bonita(c[3]),
            "precio": c[4],
            "estado": c[5]
        })

    return render_template('cliente.html', citas=citas)

# ---------------- AGENDAR ----------------
@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    if session.get('rol') != 'cliente':
        return redirect('/')

    db = get_db()
    servicios = db.execute("SELECT * FROM precios").fetchall()

    if request.method == 'POST':
        fecha = request.form['fecha']
        hora = request.form['hora']
        precio = int(request.form['precio'])

        db.execute(
            "INSERT INTO citas (cliente, fecha, hora, precio, estado) VALUES (?,?,?,?,?)",
            (session['cliente'], fecha, hora, precio, 'Pendiente')
        )
        db.commit()
        return redirect('/cliente')

    return render_template('agendar.html', servicios=servicios)

# ---------------- BARBERO ----------------
@app.route('/barbero')
def barbero():
    if session.get('rol') != 'barbero':
        return redirect('/')

    db = get_db()
    rows = db.execute("SELECT * FROM citas").fetchall()
    precios = db.execute("SELECT * FROM precios").fetchall()

    citas = []
    total = 0

    for c in rows:
        citas.append({
            "id": c[0],
            "cliente": c[1],
            "fecha": fecha_bonita(c[2]),
            "hora": hora_bonita(c[3]),
            "precio": c[4],
            "estado": c[5]
        })

        if c[5] == 'Aceptada':
            total += c[4]

    return render_template(
        'barbero.html',
        citas=citas,
        precios=precios,
        total=total
    )

@app.route('/precios', methods=['GET', 'POST'])
def precios():
    if session.get('rol') != 'barbero':
        return redirect('/')

    db = get_db()

    if request.method == 'POST':
        for servicio in request.form:
            valor = int(request.form[servicio])
            db.execute(
                "UPDATE precios SET valor=? WHERE servicio=?",
                (valor, servicio)
            )
        db.commit()
        return redirect('/barbero')

    precios = db.execute("SELECT servicio, valor FROM precios").fetchall()
    return render_template('precios.html', precios=precios)


# ---------------- CAMBIAR ESTADO ----------------
@app.route('/estado/<int:id>/<estado>')
def estado(id, estado):
    if session.get('rol') != 'barbero':
        return redirect('/')

    db = get_db()
    db.execute("UPDATE citas SET estado=? WHERE id=?", (estado, id))
    db.commit()
    return redirect('/barbero')

# ---------------- ELIMINAR CITA ----------------
@app.route('/eliminar/<int:id>')
def eliminar(id):
    if 'rol' not in session:
        return redirect('/')

    db = get_db()

    if session['rol'] == 'cliente':
        db.execute(
            "DELETE FROM citas WHERE id=? AND cliente=?",
            (id, session['cliente'])
        )
        destino = '/cliente'
    else:
        db.execute("DELETE FROM citas WHERE id=?", (id,))
        destino = '/barbero'

    db.commit()
    return redirect(destino)

# ---------------- EDITAR PRECIOS ----------------
@app.route('/editar_precio/<int:id>', methods=['POST'])
def editar_precio(id):
    if session.get('rol') != 'barbero':
        return redirect('/')

    nuevo = int(request.form['valor'])
    db = get_db()
    db.execute("UPDATE precios SET valor=? WHERE id=?", (nuevo, id))
    db.commit()
    return redirect('/barbero')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
