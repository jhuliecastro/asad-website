from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__, static_folder='.')
app.secret_key = 'asad-hvac-secret-2026-change-this'
ADMIN_PASSWORD = 'asad2026'
DATABASE = 'asad_inquiries.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Run auto-delete on startup
    delete_old_files()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            phone            TEXT NOT NULL,
            email            TEXT NOT NULL,
            service          TEXT,
            message          TEXT,
            attachment_link  TEXT,
            attachment_file  TEXT,
            submitted        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status           TEXT DEFAULT 'new'
        )
    ''')

    try:
        cursor.execute('ALTER TABLE inquiries ADD COLUMN attachment_link TEXT')
    except:
        pass

    try:
        cursor.execute('ALTER TABLE inquiries ADD COLUMN attachment_file TEXT')
    except:
        pass

    conn.commit()
    conn.close()
    print("Database ready!")


@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/submit-inquiry', methods=['POST'])
def submit_inquiry():
    name            = request.form.get('name', '').strip()
    phone           = request.form.get('phone', '').strip()
    email           = request.form.get('email', '').strip()
    service         = request.form.get('service', '').strip()
    message         = request.form.get('message', '').strip()
    attachment_link = request.form.get('attachment_link', '').strip()
    attachment_file = None

    print(f"New inquiry from: {name} | {email} | {phone}")

    if not name or not phone or not email:
        return jsonify({'success': False, 'error': 'Name, phone and email are required.'}), 400

    if 'attachment_file' in request.files:
    file = request.files['attachment_file']
    if file and file.filename != '' and allowed_file(file.filename):

        # Check file size before saving
        file.seek(0, 2)  # Seek to end of file
        file_size = file.tell()  # Get file size in bytes
        file.seek(0)  # Reset back to beginning

        if file_size > MAX_FILE_SIZE_BYTES:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size is {MAX_FILE_SIZE_MB}MB. Please use the link field instead.'
            }), 400

        safe_filename = f"{name.replace(' ', '_')}_{file.filename.replace(' ', '_')}"
        file.save(os.path.join(UPLOAD_FOLDER, safe_filename))
        attachment_file = safe_filename
        print(f"File saved: {safe_filename}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inquiries (name, phone, email, service, message, attachment_link, attachment_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, phone, email, service, message, attachment_link or None, attachment_file))
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
        td{padding:12px;border-bottom:1px solid #1a2f4a;vertical-align:top;max-width:180px;word-wrap:break-word}
        tr:hover td{background:#0b1526}
        .badge-new{background:#f07c1e;color:#070e1a;padding:3px 10px;border-radius:3px;font-size:11px;font-weight:bold}
        .badge-resolved{background:#2ecc71;color:#070e1a;padding:3px 10px;border-radius:3px;font-size:11px}
        .empty{color:#7a97bb;text-align:center;padding:48px;font-size:15px}
        .file-link{color:#f07c1e;text-decoration:none;font-size:12px}
        .file-link:hover{text-decoration:underline}
        .no-attach{color:#3a5070;font-size:12px}
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
          <th>Service</th><th>Message</th><th>Attachment</th>
          <th>Date Submitted</th><th>Status</th>
        </tr>
    '''

    if len(rows) == 0:
        html += '<tr><td colspan="9" class="empty">No inquiries yet.</td></tr>'
    else:
        for row in rows:
            badge = 'badge-new' if row['status'] == 'new' else 'badge-resolved'

            attachment_html = ''
            if row['attachment_file']:
                attachment_html += f'<a href="/uploads/{row["attachment_file"]}" class="file-link" target="_blank">📎 {row["attachment_file"]}</a><br>'
            if row['attachment_link']:
                attachment_html += f'<a href="{row["attachment_link"]}" class="file-link" target="_blank">🔗 View Link</a>'
            if not attachment_html:
                attachment_html = '<span class="no-attach">None</span>'

            html += f'''
            <tr>
              <td>{row['id']}</td>
              <td><strong>{row['name']}</strong></td>
              <td>{row['phone']}</td>
              <td>{row['email']}</td>
              <td>{row['service'] or '—'}</td>
              <td>{(row['message'] or '')[:60]}{'…' if len(row['message'] or '') > 60 else ''}</td>
              <td>{attachment_html}</td>
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
def delete_old_files():
    """
    Deletes uploaded files older than 30 days.
    
    HOW IT WORKS:
    - Looks at every file in the uploads folder
    - Checks when it was last modified (os.path.getmtime)
    - If older than 30 days, deletes the file AND removes
      the filename from the database so the link disappears
      from the admin panel too
    
    WHEN DOES THIS RUN?
    - Every time the app starts (when Flask starts)
    - You can also call it manually from the admin panel
    """
    if not os.path.exists(UPLOAD_FOLDER):
        return

    import time
    now = time.time()
    days_30 = 30 * 24 * 60 * 60  # 30 days in seconds
    deleted_count = 0

    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Check how old the file is
        file_age = now - os.path.getmtime(filepath)

        if file_age > days_30:
            # Delete the physical file
            os.remove(filepath)

            # Also clear it from the database
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE inquiries SET attachment_file = NULL WHERE attachment_file = ?',
                (filename,)
            )
            conn.commit()
            conn.close()

            deleted_count += 1
            print(f"Auto-deleted old file: {filename}")

    if deleted_count > 0:
        print(f"Auto-delete complete: {deleted_count} file(s) removed")

if __name__ == '__main__':
    init_db()
    print("\nASAD Website running!")
    print("  Website  ->  http://127.0.0.1:5000")
    print("  Admin    ->  http://127.0.0.1:5000/admin/login\n")
    app.run(debug=True, port=5000)
