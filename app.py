from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import sqlite3

app = Flask(__name__, static_folder='.')
app.secret_key = 'asad-hvac-secret-2026-change-this'
ADMIN_PASSWORD = 'asad2026'
DATABASE = 'asad_inquiries.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            phone     TEXT NOT NULL,
            email     TEXT NOT NULL,
            service   TEXT,
            message   TEXT,
            submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status    TEXT DEFAULT 'new'
        )
    ''')
    conn.commit()
    conn.close()
    print("Database ready!")


@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


@app.route('/submit-inquiry', methods=['POST'])
def submit_inquiry():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data received.'}), 400

    name    = data.get('name', '').strip()
    phone   = data.get('phone', '').strip()
    email   = data.get('email', '').strip()
    service = data.get('service', '').strip()
    message = data.get('message', '').strip()

    print(f"New inquiry from: {name} | {email} | {phone}")

    if not name or not phone or not email:
        return jsonify({'success': False, 'error': 'Name, phone and email are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inquiries (name, phone, email, service, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, phone, email, service, message))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"Saved as inquiry #{new_id}")

    return jsonify({
        'success': True,
        'message': f'Thank you {name}! We will contact you within 24 hours.',
        'id': new_id
    })


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('view_inquiries'))
        else:
            error = 'Incorrect password. Please try again.'

    return '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>ASAD Admin Login</title>
      <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{background:#070e1a;display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:Arial,sans-serif}
        .box{background:#111f38;border:1px solid rgba(240,124,30,0.3);padding:48px;width:100%;max-width:400px;text-align:center}
        .snowflake{font-size:40px;margin-bottom:16px}
        h1{color:#f07c1e;font-size:22px;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
        p{color:#7a97bb;font-size:13px;margin-bottom:32px}
        input[type=password]{width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-bottom:2px solid #f07c1e;padding:14px 16px;color:white;font-size:14px;outline:none;margin-bottom:16px;text-align:center;letter-spacing:4px}
        button{width:100%;background:#f07c1e;color:#070e1a;border:none;padding:14px;font-size:13px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;cursor:pointer}
        button:hover{background:#e8920a}
        .error{color:#e74c3c;font-size:13px;margin-top:16px}
      </style>
    </head>
    <body>
      <div class="box">
        <div class="snowflake">❄️</div>
        <h1>Admin Access</h1>
        <p>AL SHUROOQ AL DHABI — Inquiries Dashboard</p>
        <form method="POST">
          <input type="password" name="password" placeholder="Enter password" autofocus>
          <button type="submit">Login →</button>
        </form>
        <p class="error">''' + error + '''</p>
      </div>
    </body>
    </html>
    '''


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/inquiries')
def view_inquiries():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inquiries ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>ASAD Admin — Inquiries</title>
      <style>
        body{font-family:Arial;padding:32px;background:#070e1a;color:#c8daf0}
        .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
        h1{color:#f07c1e}
        .logout{color:#7a97bb;font-size:13px;text-decoration:none;border:1px solid #7a97bb;padding:6px 14px}
        .logout:hover{border-color:#f07c1e;color:#f07c1e}
        .sub{color:#7a97bb;font-size:13px;margin-bottom:24px}
        table{width:100%;border-collapse:collapse;font-size:13px}
        th{background:#111f38;padding:12px;text-align:left;color:#f07c1e;border-bottom:2px solid #f07c1e}
        td{padding:12px;border-bottom:1px solid #1a2f4a;vertical-align:top}
        tr:hover td{background:#0b1526}
        .badge-new{background:#f07c1e;color:#070e1a;padding:3px 10px;border-radius:3px;font-size:11px;font-weight:bold}
        .badge-resolved{background:#2ecc71;color:#070e1a;padding:3px 10px;border-radius:3px;font-size:11px}
        .empty{color:#7a97bb;text-align:center;padding:48px;font-size:15px}
      </style>
    </head>
    <body>
      <div class="header">
        <h1>Inquiries Dashboard</h1>
        <a href="/admin/logout" class="logout">Logout</a>
      </div>
      <p class="sub">Total submissions: ''' + str(len(rows)) + ''' &nbsp;|&nbsp;
        <a href="/admin/inquiries/export" style="color:#f07c1e;">Export JSON</a>
      </p>
      <table>
        <tr>
          <th>#</th><th>Name</th><th>Phone</th><th>Email</th>
          <th>Service</th><th>Message</th><th>Date Submitted</th><th>Status</th>
        </tr>
    '''

    if len(rows) == 0:
        html += '<tr><td colspan="8" class="empty">No inquiries yet.</td></tr>'
    else:
        for row in rows:
            badge = 'badge-new' if row['status'] == 'new' else 'badge-resolved'
            html += f'''
            <tr>
              <td>{row['id']}</td>
              <td><strong>{row['name']}</strong></td>
              <td>{row['phone']}</td>
              <td>{row['email']}</td>
              <td>{row['service'] or '—'}</td>
              <td>{(row['message'] or '')[:80]}{'…' if len(row['message'] or '') > 80 else ''}</td>
              <td>{row['submitted']}</td>
              <td><span class="{badge}">{row['status']}</span></td>
            </tr>
            '''

    html += '</table></body></html>'
    return html


@app.route('/admin/inquiries/export')
def export_inquiries():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inquiries ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route('/export/inquiries')
def public_export():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inquiries ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == '__main__':
    init_db()
    print("\nASAD Website running!")
    print("  Website  ->  http://127.0.0.1:5000")
    print("  Admin    ->  http://127.0.0.1:5000/admin/login")
    print("  Logout   ->  http://127.0.0.1:5000/admin/logout\n")
    app.run(debug=True, port=5000)
