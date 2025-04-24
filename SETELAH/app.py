import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from models import db, User, InventoryItem, Transaction, Category, NotificationSetting
from api import api

app = Flask(__name__)
# Ganti dengan secret key yang kuat, bisa dari environment variable
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'ganti-dengan-kunci-rahasia-yang-kuat-dan-unik')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(api, url_prefix='/api')

# Tambahkan context processor untuk menyediakan fungsi now() ke semua template
@app.context_processor
def utility_processor():
    return dict(now=datetime.now)

# --- Data Dummy (Gantilah dengan database di aplikasi nyata) ---
# TODO: Implementasi database (SQLAlchemy, dll.) untuk persistensi data
users = {
    'admin': {
        'password': 'adminpass',
        'role': 'admin',
        'name': 'Admin Utama',
        'permissions': ['read_all', 'write_all', 'delete_all', 'manage_users']
    },
    'manager': {
        'password': 'managerpass',
        'role': 'manajer',
        'name': 'Manajer Gudang',
        'permissions': [
            'read_all',
            'read_inventory',
            'approve_transactions',
            'generate_reports',
            'manage_inventory_levels',
            'set_item_priority',
            'manage_categories',
            'export_reports',
            'view_analytics',
            'manage_thresholds',
            'manage_notifications'
        ]
    },
    'operator': {
        'password': 'operatorpass',
        'role': 'operator',
        'name': 'Operator Stok',
        'permissions': ['read_inventory', 'create_transaction']
    }
}
inventory_items = {
    'ITEM001': {'name': 'Laptop ThinkPad X1', 'quantity': 15, 'category': 'Elektronik', 'added_by': 'admin', 'last_update': '2024-05-10 09:00:00'},
    'ITEM002': {'name': 'Keyboard Logitech MX', 'quantity': 25, 'category': 'Aksesoris', 'added_by': 'admin', 'last_update': '2024-05-10 09:05:00'},
    'ITEM003': {'name': 'Mouse Logitech MX Master 3', 'quantity': 30, 'category': 'Aksesoris', 'added_by': 'operator', 'last_update': '2024-05-11 14:30:00'}
}
transactions = [
    {'id': 1, 'type': 'masuk', 'item_id': 'ITEM001', 'quantity': 5, 'user': 'admin', 'timestamp': '2024-05-15 10:00:00', 'notes': 'Stok awal'},
    {'id': 2, 'type': 'keluar', 'item_id': 'ITEM002', 'quantity': 2, 'user': 'operator', 'timestamp': '2024-05-16 11:00:00', 'notes': 'Untuk Dept IT'},
    {'id': 3, 'type': 'masuk', 'item_id': 'ITEM003', 'quantity': 10, 'user': 'operator', 'timestamp': '2024-05-17 14:30:00', 'notes': 'Pembelian baru'},
]
next_transaction_id = 4
# --- End Data Dummy ---

# --- Helper Function ---
def get_current_timestamp():
    """Mendapatkan timestamp string format Tahun-Bulan-Tanggal Jam:Menit:Detik"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# --- Decorators untuk Otentikasi & Otorisasi ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Akses ditolak. Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """Decorator untuk membatasi akses berdasarkan role."""
    def role_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Akses ditolak. Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('login'))

            user_role = session['user'].get('role')
            if user_role not in allowed_roles:
                flash(f'Akses ditolak. Role "{user_role}" tidak diizinkan mengakses halaman ini.', 'danger')
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return role_decorator

def permission_required(required_permissions):
    """Decorator untuk memeriksa permission user."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('login'))
            
            user_permissions = session['user'].get('permissions', [])
            
            # Periksa apakah user memiliki semua permission yang diperlukan
            if not all(perm in user_permissions for perm in required_permissions):
                flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
                return redirect(url_for('dashboard_view'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes untuk Halaman Web (View Rendering) ---

@app.route('/')
def home():
    """Halaman utama, redirect ke login jika belum login, atau dashboard jika sudah."""
    if 'user' in session:
        return redirect(url_for('dashboard_view'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman Login"""
    if 'user' in session:
        return redirect(url_for('dashboard_view'))  # Jika sudah login, ke dashboard

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Debug print untuk memeriksa input
        print(f"Login attempt - Username: {username}, Password: {password}")
        
        user = User.query.filter_by(username=username).first()
        
        # Debug print untuk memeriksa user data
        print(f"User data found: {user}")

        if user and check_password_hash(user.password, password):
            session['user'] = {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'permissions': get_role_permissions(user.role)
            }
            flash(f"Login berhasil! Selamat datang, {user.name}.", 'success')
            return redirect(url_for('dashboard_view'))
        else:
            flash('Username atau password salah.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Halaman Registrasi untuk user baru."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Set default role sebagai operator untuk user baru
        role = 'operator'  # User baru selalu menjadi operator

        if not all([username, password, name]):
            flash('Semua field (username, password, nama) harus diisi.', 'warning')
        elif username in users:
            flash(f'Username "{username}" sudah digunakan.', 'warning')
        else:
            users[username] = {
                'password': password,  # TODO: Hash password
                'role': role,
                'name': name
            }
            flash(f'Registrasi berhasil! Anda terdaftar sebagai {role}.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    user_name = session.get('user', {}).get('name', 'User')
    session.pop('user', None)
    flash(f'Anda ({user_name}) telah berhasil logout.', 'info')
    return redirect(url_for('login'))

@app.route('/unauthorized')
@login_required # Pastikan user login untuk melihat halaman ini
def unauthorized():
    """Halaman pemberitahuan akses tidak diizinkan."""
    return render_template('unauthorized.html'), 403


# --- View Routes (Hanya Render Template Kosong, Data diambil via JS API Call) ---
# View routes ini bertindak sebagai "consumer" dari API internal aplikasi ini

@app.route('/dashboard')
@login_required
def dashboard_view():
    """Menampilkan halaman dashboard."""
    # Data akan di-fetch oleh dashboard.js via API
    # Kirim role ke template untuk conditional rendering di frontend jika perlu
    user_role = session.get('user', {}).get('role')
    return render_template('dashboard.html', user_role=user_role)

@app.route('/inventory')
@login_required
@permission_required(['read_inventory'])
def inventory_view():
    """Menampilkan halaman daftar inventaris."""
    user_role = session.get('user', {}).get('role')
    items = InventoryItem.query.all()
    return render_template('inventory.html', user_role=user_role, items=items)

# >>> PERIKSA BARIS-BARIS BERIKUT DENGAN SANGAT TELITI <<<
@app.route('/input-barang')
@login_required
@role_required(['admin', 'operator']) # Hanya admin & operator bisa input barang masuk
def barang_masuk_view(): # Mengubah nama fungsi dari proses_barang_masuk menjadi barang_masuk_view
    """Menampilkan halaman input barang masuk."""
    user_role = session.get('user', {}).get('role')
    return render_template('barang_masuk.html', user_role=user_role)

@app.route('/barang-keluar')
@login_required
@role_required(['admin', 'operator']) # Hanya admin & operator bisa input barang keluar
def barang_keluar_view():
    """Menampilkan halaman input barang keluar."""
    # Form dan list transaksi akan dihandle oleh barang_keluar.js via API
    user_role = session.get('user', {}).get('role')
    return render_template('barang_keluar.html', user_role=user_role)

@app.route('/manage-users')
@login_required
@role_required(['admin']) # Hanya admin yang bisa manajemen akun
def manage_users_view():
    """Menampilkan halaman manajemen akun."""
    user_role = session.get('user', {}).get('role')
    return render_template('manajemen_akun.html', user_role=user_role)

# --- Manager View Routes ---
@app.route('/approvals')
@login_required
@permission_required(['approve_transactions'])
def approvals_view():
    """Menampilkan halaman persetujuan transaksi."""
    user_role = session.get('user', {}).get('role')
    pending = Transaction.query.filter_by(status='pending').all()
    return render_template('approvals.html', user_role=user_role, transactions=pending)

@app.route('/reports')
@login_required
@permission_required(['generate_reports'])
def reports_view():
    """Menampilkan halaman laporan."""
    user_role = session.get('user', {}).get('role')
    return render_template('reports.html', user_role=user_role)

@app.route('/analytics')
@login_required
@permission_required(['view_analytics'])
def analytics_view():
    """Menampilkan halaman analytics."""
    user_role = session.get('user', {}).get('role')
    return render_template('analytics.html', user_role=user_role)

@app.route('/inventory-settings')
@login_required
@permission_required(['manage_inventory_levels', 'manage_categories'])
def inventory_settings_view():
    """Menampilkan halaman pengaturan inventaris."""
    user_role = session.get('user', {}).get('role')
    return render_template('inventory_settings.html', user_role=user_role)

@app.route('/notifications')
@login_required
@permission_required(['manage_notifications'])
def notifications_view():
    """Menampilkan halaman pengaturan notifikasi."""
    user_role = session.get('user', {}).get('role')
    return render_template('notifications.html', user_role=user_role)

# ==============================================================
# ==================== API Endpoints (Provider) ================
# ==============================================================
# API endpoints ini bertindak sebagai "provider" data/layanan

# --- API Dashboard ---
@app.route('/api/dashboard/summary', methods=['GET'])
@login_required
@role_required(['admin', 'manajer']) # Hanya admin & manajer boleh lihat summary
def api_dashboard_summary():
    """API Endpoint untuk mendapatkan data summary dashboard."""
    try:
        total_items = InventoryItem.query.count()
        total_quantity = sum(item.quantity for item in InventoryItem.query.all())
        # Ambil 5 transaksi terbaru (berdasarkan ID atau timestamp jika konsisten)
        recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(5).all()

        summary_data = {
            'total_unique_items': total_items,
            'total_stock_quantity': total_quantity,
            'recent_transactions_count': Transaction.query.count(), # Contoh data tambahan
            'recent_transactions': [t.to_dict() for t in recent_transactions] # Kirim 5 terakhir
        }
        return jsonify(summary_data), 200
    except Exception as e:
        # Log error e
        return jsonify({"error": "Gagal mengambil data summary", "details": str(e)}), 500

# --- API Inventory ---

@app.route('/api/inventory', methods=['GET'])
@login_required
@permission_required(['read_inventory'])
def api_get_inventory():
    """Mendapatkan daftar inventory."""
    try:
        # Ubah format dari dict ke list dan tambahkan ID sebagai bagian dari item
        inventory_list = []
        for item in InventoryItem.query.all():
            inventory_list.append(item.to_dict())
        return jsonify(inventory_list), 200
    except Exception as e:
        return jsonify({"error": f"Gagal mengambil data inventaris: {str(e)}"}), 500

@app.route('/api/inventory', methods=['POST'])
@login_required
@role_required(['admin', 'operator'])
def api_add_inventory_item():
    """API Endpoint untuk menambahkan item inventaris baru."""
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400

    try:
        data = request.get_json()
        required_fields = ['item_id', 'name', 'quantity', 'category']
        if not all(k in data for k in required_fields):
            return jsonify({'error': f'Data tidak lengkap. Membutuhkan: {", ".join(required_fields)}'}), 400

        item_id = data['item_id'].strip().upper()
        name = data['name'].strip()
        category = data['category'].strip()

        if not item_id or not name or not category:
            return jsonify({'error': 'ID, Nama, dan Kategori tidak boleh kosong'}), 400

        if InventoryItem.query.filter_by(item_id=item_id).first():
            return jsonify({'error': f'Item ID "{item_id}" sudah ada'}), 409

        try:
            quantity = int(data['quantity'])
            if quantity < 0:
                return jsonify({'error': 'Jumlah awal tidak boleh negatif'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Jumlah harus berupa angka bilangan bulat non-negatif'}), 400

        current_user = session.get('user', {}).get('username', 'unknown')
        current_time = get_current_timestamp()

        new_item = InventoryItem(
            item_id=item_id,
            name=name,
            quantity=quantity,
            category=category,
            added_by=current_user,
            last_update=current_time
        )

        db.session.add(new_item)
        db.session.commit()
        response_data = new_item.to_dict()
        return jsonify(response_data), 201

    except Exception as e:
        return jsonify({"error": f"Gagal menyimpan item baru: {str(e)}"}), 500

@app.route('/api/inventory/<item_id>', methods=['GET'])
@login_required
@role_required(['admin', 'manajer', 'operator'])
def api_get_inventory_item(item_id):
    """API Endpoint untuk mendapatkan detail item inventaris."""
    item_id = item_id.strip().upper()
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    # Return item dengan ID-nya
    return jsonify(item.to_dict()), 200

@app.route('/api/inventory/<item_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def api_update_inventory_item(item_id):
    """API Endpoint untuk mengupdate item inventaris."""
    item_id = item_id.strip().upper()
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    try:
        data = request.get_json()
        
        # Update fields yang diberikan
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({"error": "Nama item tidak boleh kosong"}), 400
            item.name = name
            
        if 'category' in data:
            category = data['category'].strip()
            if not category:
                return jsonify({"error": "Kategori tidak boleh kosong"}), 400
            item.category = category
            
        if 'quantity' in data:
            try:
                quantity = int(data['quantity'])
                if quantity < 0:
                    return jsonify({"error": "Jumlah tidak boleh negatif"}), 400
                item.quantity = quantity
            except ValueError:
                return jsonify({"error": "Jumlah harus berupa angka bulat"}), 400
                
        # Update timestamp dan user
        item.last_update = get_current_timestamp()
        item.updated_by = session.get('user', {}).get('username', 'unknown')
        
        # Return item yang sudah diupdate
        return jsonify(item.to_dict()), 200
        
    except Exception as e:
        return jsonify({"error": f"Gagal mengupdate item: {str(e)}"}), 500

@app.route('/api/inventory/<item_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_inventory_item(item_id):
    """API Endpoint untuk menghapus item inventaris."""
    item_id = item_id.strip().upper()
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    try:
        # Cek apakah item masih memiliki stok
        if item.quantity > 0:
            return jsonify({
                "error": f"Tidak dapat menghapus item yang masih memiliki stok ({item.quantity} unit)"
            }), 400
            
        # Cek apakah item memiliki history transaksi
        item_transactions = Transaction.query.filter_by(item_id=item_id).all()
        if item_transactions:
            return jsonify({
                "error": "Tidak dapat menghapus item yang memiliki history transaksi"
            }), 400
            
        # Hapus item
        db.session.delete(item)
        db.session.commit()
        return jsonify({
            "message": f"Item {item_id} ({item.name}) berhasil dihapus"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Gagal menghapus item: {str(e)}"}), 500

# --- API Transactions ---
@app.route('/api/transactions', methods=['GET'])
@login_required
@role_required(['admin', 'manajer', 'operator'])
def api_get_transactions():
    """API Endpoint untuk mendapatkan daftar transaksi."""
    try:
        transaction_type = request.args.get('type')  # 'masuk' atau 'keluar'
        
        # Filter transaksi berdasarkan tipe jika parameter type ada
        filtered_transactions = Transaction.query.filter(Transaction.type == transaction_type).all()
            
        # Urutkan transaksi berdasarkan ID (terbaru dulu)
        sorted_transactions = sorted(filtered_transactions, key=lambda x: x.id, reverse=True)
        
        return jsonify([t.to_dict() for t in sorted_transactions]), 200
    except Exception as e:
        return jsonify({"error": "Gagal mengambil data transaksi", "details": str(e)}), 500

@app.route('/api/transactions/incoming', methods=['POST'])
@login_required
@permission_required(['create_transaction'])
def api_add_incoming_transaction():
    """Menambahkan transaksi barang masuk."""
    global next_transaction_id
    
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    data = request.get_json()
    required_fields = ['item_id', 'quantity']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Data tidak lengkap. Dibutuhkan: {', '.join(required_fields)}"}), 400
        
    item_id = data['item_id'].strip().upper()
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    try:
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({"error": "Jumlah harus lebih dari 0"}), 400
    except ValueError:
        return jsonify({"error": "Jumlah harus berupa angka bulat positif"}), 400
        
    # Update stok di inventory
    item.quantity += quantity
    item.last_update = get_current_timestamp()
    
    # Buat transaksi baru
    new_transaction = Transaction(
        id=next_transaction_id,
        type='masuk',
        item_id=item_id,
        quantity=quantity,
        user=session.get('user', {}).get('username', 'unknown'),
        timestamp=get_current_timestamp(),
        notes=data.get('notes', ''),
        status='pending_approval' if session['user']['role'] == 'operator' else 'approved'
    )
    
    db.session.add(new_transaction)
    db.session.commit()
    next_transaction_id += 1
    
    return jsonify(new_transaction.to_dict()), 201

@app.route('/api/transactions/outgoing', methods=['POST'])
@login_required
@role_required(['admin', 'operator'])
def api_add_outgoing_transaction():
    """API Endpoint untuk menambah transaksi barang keluar."""
    global next_transaction_id
    
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    data = request.get_json()
    required_fields = ['item_id', 'quantity']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Data tidak lengkap. Dibutuhkan: {', '.join(required_fields)}"}), 400
        
    item_id = data['item_id'].strip().upper()
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    try:
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({"error": "Jumlah harus lebih dari 0"}), 400
            
        # Cek stok mencukupi
        current_stock = item.quantity
        if quantity > current_stock:
            return jsonify({"error": f"Stok tidak mencukupi. Stok saat ini: {current_stock}"}), 400
            
    except ValueError:
        return jsonify({"error": "Jumlah harus berupa angka bulat positif"}), 400
        
    # Update stok di inventory
    item.quantity -= quantity
    item.last_update = get_current_timestamp()
    
    # Buat transaksi baru
    new_transaction = Transaction(
        id=next_transaction_id,
        type='keluar',
        item_id=item_id,
        quantity=quantity,
        user=session.get('user', {}).get('username', 'unknown'),
        timestamp=get_current_timestamp(),
        notes=data.get('notes', '')
    )
    
    db.session.add(new_transaction)
    db.session.commit()
    next_transaction_id += 1
    
    return jsonify(new_transaction.to_dict()), 201

# --- API Users ---
@app.route('/api/users', methods=['GET'])
@login_required
@role_required(['admin'])
def api_get_users():
    """API Endpoint untuk mendapatkan daftar pengguna."""
    try:
        # Konversi dict users ke list dan hapus password dari response
        users_list = [{'username': username, 'name': data['name'], 'role': data['role']} 
                     for username, data in users.items()]
        return jsonify(users_list), 200
    except Exception as e:
        return jsonify({"error": f"Gagal mengambil data pengguna: {str(e)}"}), 500

@app.route('/api/users', methods=['POST'])
@login_required
@role_required(['admin'])
def api_add_user():
    """API Endpoint untuk menambah pengguna baru dengan password hashing."""
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    try:
        data = request.get_json()
        required_fields = ['username', 'password', 'name', 'role']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Data tidak lengkap. Dibutuhkan: {', '.join(required_fields)}"}), 400
            
        username = data['username'].strip()
        if User.query.filter_by(username=username).first():
            return jsonify({"error": f"Username '{username}' sudah digunakan"}), 409
            
        if data['role'] not in ['admin', 'manajer', 'operator']:
            return jsonify({"error": "Role tidak valid"}), 400
            
        # Hash password sebelum disimpan
        hashed_password = generate_password_hash(data['password'])
            
        # Simpan user baru dengan password yang sudah di-hash
        new_user = User(
            username=username,
            password=hashed_password,
            name=data['name'].strip(),
            role=data['role']
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Return data user tanpa password
        return jsonify({
            'username': username,
            'name': new_user.name,
            'role': new_user.role
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Gagal menambahkan pengguna: {str(e)}"}), 500

@app.route('/api/users/<username>', methods=['PUT'])
@login_required
@role_required(['admin'])
def api_update_user(username):
    """API Endpoint untuk mengupdate data pengguna."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": f"Pengguna '{username}' tidak ditemukan"}), 404
        
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    try:
        data = request.get_json()
        
        # Update name jika ada
        if 'name' in data:
            user.name = data['name'].strip()
            
        # Update role jika ada dan valid
        if 'role' in data:
            if data['role'] not in ['admin', 'manajer', 'operator']:
                return jsonify({"error": "Role tidak valid"}), 400
            user.role = data['role']
            
        # Update password jika ada
        if 'password' in data and data['password']:
            user.password = generate_password_hash(data['password'])
            
        # Return data user yang diupdate (tanpa password)
        return jsonify({
            'username': username,
            'name': user.name,
            'role': user.role
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Gagal mengupdate pengguna: {str(e)}"}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_user(username):
    """API Endpoint untuk menghapus pengguna."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": f"Pengguna '{username}' tidak ditemukan"}), 404
        
    # Cek apakah user mencoba menghapus dirinya sendiri
    if username == session.get('user', {}).get('username'):
        return jsonify({"error": "Tidak dapat menghapus akun yang sedang digunakan"}), 400
        
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"Pengguna '{username}' berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menghapus pengguna: {str(e)}"}), 500

# Tambahkan fungsi helper untuk password hashing
def hash_password(password):
    """Helper function untuk menghasilkan password hash."""
    return generate_password_hash(password)

def verify_password(hash_value, password):
    """Helper function untuk memverifikasi password."""
    return check_password_hash(hash_value, password)

# --- Routes untuk Fitur Manajerial ---
@app.route('/api/inventory/approval-requests', methods=['GET'])
@login_required
@permission_required(['approve_transactions'])
def get_approval_requests():
    """Mendapatkan daftar permintaan persetujuan untuk transaksi."""
    # Implementasi dummy untuk contoh
    pending_transactions = Transaction.query.filter_by(status='pending').all()
    return jsonify([t.to_dict() for t in pending_transactions])

@app.route('/api/inventory/approve-transaction/<int:transaction_id>', methods=['POST'])
@login_required
@permission_required(['approve_transactions'])
def approve_transaction(transaction_id):
    """Menyetujui transaksi inventory."""
    transaction = Transaction.query.filter_by(id=transaction_id).first()
    if not transaction:
        return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
    
    transaction.status = 'approved'
    transaction.approved_by = session['user']['username']
    transaction.approved_at = get_current_timestamp()
    
    db.session.commit()
    return jsonify(transaction.to_dict())

@app.route('/api/reports/inventory-levels', methods=['GET'])
@login_required
@permission_required(['generate_reports'])
def get_inventory_levels_report():
    """Menghasilkan laporan level inventory."""
    report = {
        'timestamp': get_current_timestamp(),
        'generated_by': session['user']['username'],
        'inventory_levels': InventoryItem.query.all(),
        'low_stock_items': InventoryItem.query.filter(InventoryItem.quantity < 10).all(),
        'total_items': InventoryItem.query.count()
    }
    return jsonify(report)

@app.route('/api/reports/transaction-history', methods=['GET'])
@login_required
@permission_required(['generate_reports'])
def get_transaction_history_report():
    """Menghasilkan laporan riwayat transaksi."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filtered_transactions = Transaction.query.filter(Transaction.timestamp.between(start_date, end_date)).all()
    
    report = {
        'timestamp': get_current_timestamp(),
        'generated_by': session['user']['username'],
        'period': {
            'start': start_date,
            'end': end_date
        },
        'transactions': [t.to_dict() for t in filtered_transactions],
        'total_transactions': len(filtered_transactions)
    }
    return jsonify(report)

@app.route('/api/inventory/set-threshold/<item_id>', methods=['POST'])
@login_required
@permission_required(['manage_inventory_levels'])
def set_inventory_threshold(item_id):
    """Mengatur batas minimum stok untuk item."""
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({'error': 'Item tidak ditemukan'}), 404
    
    data = request.get_json()
    threshold = data.get('threshold')
    
    if threshold is None or not isinstance(threshold, int) or threshold < 0:
        return jsonify({'error': 'Threshold harus berupa angka positif'}), 400
    
    item.min_threshold = threshold
    db.session.commit()
    return jsonify(item.to_dict())

# Tambahkan route baru untuk fitur manajer
@app.route('/api/inventory/categories', methods=['GET', 'POST'])
@login_required
@permission_required(['manage_categories'])
def manage_categories():
    """Mengelola kategori inventory."""
    if request.method == 'POST':
        data = request.get_json()
        # Implementasi penambahan/edit kategori
        return jsonify({"message": "Kategori berhasil diperbarui"})
    else:
        # Return daftar kategori
        categories = list(set(item.category for item in InventoryItem.query.all()))
        return jsonify(categories)

@app.route('/api/inventory/priority/<item_id>', methods=['POST'])
@login_required
@permission_required(['set_item_priority'])
def set_item_priority(item_id):
    """Mengatur prioritas item inventory."""
    item = InventoryItem.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({'error': 'Item tidak ditemukan'}), 404
    
    data = request.get_json()
    priority = data.get('priority')
    
    item.priority = priority
    db.session.commit()
    return jsonify(item.to_dict())

@app.route('/api/reports/export', methods=['GET'])
@login_required
@permission_required(['export_reports'])
def export_report():
    """Mengekspor laporan dalam format CSV/Excel."""
    report_type = request.args.get('type', 'inventory')
    # Implementasi ekspor laporan
    return jsonify({"message": "Laporan berhasil diekspor"})

@app.route('/api/analytics/dashboard', methods=['GET'])
@login_required
@permission_required(['view_analytics'])
def get_analytics():
    """Mendapatkan data analitik untuk dashboard manajer."""
    analytics = {
        'stock_trends': calculate_stock_trends(),
        'transaction_summary': get_transaction_summary(),
        'category_distribution': get_category_distribution(),
        'low_stock_alerts': get_low_stock_alerts()
    }
    return jsonify(analytics)

@app.route('/api/notifications/settings', methods=['GET', 'POST'])
@login_required
@permission_required(['manage_notifications'])
def manage_notification_settings():
    """Mengelola pengaturan notifikasi."""
    if request.method == 'POST':
        data = request.get_json()
        # Implementasi update pengaturan notifikasi
        return jsonify({"message": "Pengaturan notifikasi berhasil diperbarui"})
    else:
        # Return pengaturan notifikasi saat ini
        return jsonify({
            "low_stock_threshold": 10,
            "email_notifications": True,
            "notification_frequency": "daily"
        })

# Helper functions untuk analytics
def calculate_stock_trends():
    """Menghitung tren stok berdasarkan data historis."""
    return {
        'increasing': [],
        'decreasing': [],
        'stable': []
    }

def get_transaction_summary():
    """Mendapatkan ringkasan transaksi."""
    return {
        'total_in': sum(t.quantity for t in Transaction.query.filter_by(type='masuk').all()),
        'total_out': sum(t.quantity for t in Transaction.query.filter_by(type='keluar').all()),
        'most_active_items': []
    }

def get_category_distribution():
    """Mendapatkan distribusi item per kategori."""
    distribution = {}
    for item in InventoryItem.query.all():
        category = item.category
        if category in distribution:
            distribution[category] += 1
        else:
            distribution[category] = 1
    return distribution

def get_low_stock_alerts():
    """Mendapatkan alert untuk item dengan stok rendah."""
    return [
        {'item_id': item.item_id, 'name': item.name, 'quantity': item.quantity}
        for item in InventoryItem.query.filter(InventoryItem.quantity <= 10).all()
    ]

def init_db():
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

@app.before_first_request
def create_tables():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)