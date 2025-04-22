import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Ganti dengan secret key yang kuat, bisa dari environment variable
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'ganti-dengan-kunci-rahasia-yang-kuat-dan-unik')

# Tambahkan context processor untuk menyediakan fungsi now() ke semua template
@app.context_processor
def utility_processor():
    return dict(now=datetime.now)

# --- Data Dummy (Gantilah dengan database di aplikasi nyata) ---
# TODO: Implementasi database (SQLAlchemy, dll.) untuk persistensi data
users = {
    'admin': {'password': 'adminpass', 'role': 'admin', 'name': 'Admin Utama'},
    'manager': {'password': 'managerpass', 'role': 'manajer', 'name': 'Manajer Gudang'},
    'operator': {'password': 'operatorpass', 'role': 'operator', 'name': 'Operator Stok'}
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
    def role_decorator(f):  # Renamed from 'decorator' to 'role_decorator'
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session: # Harus login dulu
                flash('Akses ditolak. Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('login'))

            user_role = session['user'].get('role')
            if user_role not in allowed_roles:
                flash(f'Akses ditolak. Role "{user_role}" tidak diizinkan mengakses halaman ini.', 'danger')
                # Redirect ke halaman yang sesuai, misal dashboard atau unauthorized
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return role_decorator

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
        
        user_data = users.get(username)
        
        # Debug print untuk memeriksa user data
        print(f"User data found: {user_data}")

        if user_data and user_data['password'] == password:
            session['user'] = {
                'username': username,
                'role': user_data['role'],
                'name': user_data['name']
            }
            flash(f"Login berhasil! Selamat datang, {user_data['name']}.", 'success')
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
@role_required(['admin', 'manajer', 'operator']) # Semua role boleh lihat inventory
def inventory_view():
    """Menampilkan halaman daftar inventaris."""
    # Data akan di-fetch oleh inventory.js via API
    user_role = session.get('user', {}).get('role')
    return render_template('inventory.html', user_role=user_role)

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
    # Data user akan di-fetch oleh manage_users.js (jika dibuat) via API
    user_role = session.get('user', {}).get('role')
    # Mungkin perlu mengirim daftar user langsung jika tidak pakai API untuk view ini
    # user_list = [{'username': u, 'role': d['role'], 'name': d['name']} for u, d in users.items()]
    # return render_template('manajemen_akun.html', user_role=user_role, users=user_list)
    return render_template('manajemen_akun.html', user_role=user_role)


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
        total_items = len(inventory_items)
        total_quantity = sum(item.get('quantity', 0) for item in inventory_items.values())
        # Ambil 5 transaksi terbaru (berdasarkan ID atau timestamp jika konsisten)
        recent_transactions = sorted(transactions, key=lambda x: x['id'], reverse=True)[:5]

        summary_data = {
            'total_unique_items': total_items,
            'total_stock_quantity': total_quantity,
            'recent_transactions_count': len(transactions), # Contoh data tambahan
            'recent_transactions': recent_transactions # Kirim 5 terakhir
        }
        return jsonify(summary_data), 200
    except Exception as e:
        # Log error e
        return jsonify({"error": "Gagal mengambil data summary", "details": str(e)}), 500

# --- API Inventory ---

@app.route('/api/inventory', methods=['GET'])
@login_required
@role_required(['admin', 'manajer', 'operator']) # Semua role boleh lihat
def api_get_inventory():
    """API Endpoint untuk mendapatkan semua item inventaris."""
    try:
        # Ubah format dari dict ke list of dict agar lebih mudah diproses JSON/frontend
        inventory_list = [{'id': key, **value} for key, value in inventory_items.items()]
        return jsonify(inventory_list), 200
    except Exception as e:
        # Log error e
        return jsonify({"error": "Gagal mengambil data inventaris", "details": str(e)}), 500

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

        if item_id in inventory_items:
            return jsonify({'error': f'Item ID "{item_id}" sudah ada'}), 409

        try:
            quantity = int(data['quantity'])
            if quantity < 0:
                return jsonify({'error': 'Jumlah awal tidak boleh negatif'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Jumlah harus berupa angka bilangan bulat non-negatif'}), 400

        current_user = session.get('user', {}).get('username', 'unknown')
        current_time = get_current_timestamp()

        new_item = {
            'name': name,
            'quantity': quantity,
            'category': category,
            'added_by': current_user,
            'last_update': current_time
        }

        inventory_items[item_id] = new_item
        response_data = {'id': item_id, **new_item}
        return jsonify(response_data), 201

    except Exception as e:
        return jsonify({"error": f"Gagal menyimpan item baru: {str(e)}"}), 500

@app.route('/api/inventory/<item_id>', methods=['GET'])
@login_required
@role_required(['admin', 'manajer', 'operator'])
def api_get_inventory_item(item_id):
    """API Endpoint untuk mendapatkan detail item inventaris."""
    item_id = item_id.strip().upper()
    if item_id not in inventory_items:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    # Return item dengan ID-nya
    return jsonify({'id': item_id, **inventory_items[item_id]}), 200

@app.route('/api/inventory/<item_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def api_update_inventory_item(item_id):
    """API Endpoint untuk mengupdate item inventaris."""
    item_id = item_id.strip().upper()
    if item_id not in inventory_items:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    try:
        data = request.get_json()
        current_item = inventory_items[item_id]
        
        # Update fields yang diberikan
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({"error": "Nama item tidak boleh kosong"}), 400
            current_item['name'] = name
            
        if 'category' in data:
            category = data['category'].strip()
            if not category:
                return jsonify({"error": "Kategori tidak boleh kosong"}), 400
            current_item['category'] = category
            
        if 'quantity' in data:
            try:
                quantity = int(data['quantity'])
                if quantity < 0:
                    return jsonify({"error": "Jumlah tidak boleh negatif"}), 400
                current_item['quantity'] = quantity
            except ValueError:
                return jsonify({"error": "Jumlah harus berupa angka bulat"}), 400
                
        # Update timestamp dan user
        current_item['last_update'] = get_current_timestamp()
        current_item['updated_by'] = session.get('user', {}).get('username', 'unknown')
        
        # Return item yang sudah diupdate
        return jsonify({'id': item_id, **current_item}), 200
        
    except Exception as e:
        return jsonify({"error": f"Gagal mengupdate item: {str(e)}"}), 500

@app.route('/api/inventory/<item_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_inventory_item(item_id):
    """API Endpoint untuk menghapus item inventaris."""
    item_id = item_id.strip().upper()
    if item_id not in inventory_items:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    try:
        # Cek apakah item masih memiliki stok
        if inventory_items[item_id]['quantity'] > 0:
            return jsonify({
                "error": f"Tidak dapat menghapus item yang masih memiliki stok ({inventory_items[item_id]['quantity']} unit)"
            }), 400
            
        # Cek apakah item memiliki history transaksi
        item_transactions = [t for t in transactions if t['item_id'] == item_id]
        if item_transactions:
            return jsonify({
                "error": "Tidak dapat menghapus item yang memiliki history transaksi"
            }), 400
            
        # Hapus item
        deleted_item = inventory_items.pop(item_id)
        return jsonify({
            "message": f"Item {item_id} ({deleted_item['name']}) berhasil dihapus"
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
        filtered_transactions = transactions
        if transaction_type:
            filtered_transactions = [t for t in transactions if t['type'] == transaction_type]
            
        # Urutkan transaksi berdasarkan ID (terbaru dulu)
        sorted_transactions = sorted(filtered_transactions, key=lambda x: x['id'], reverse=True)
        
        return jsonify(sorted_transactions), 200
    except Exception as e:
        return jsonify({"error": "Gagal mengambil data transaksi", "details": str(e)}), 500

@app.route('/api/transactions/incoming', methods=['POST'])
@login_required
@role_required(['admin', 'operator'])
def api_add_incoming_transaction():
    """API Endpoint untuk menambah transaksi barang masuk."""
    global next_transaction_id
    
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    data = request.get_json()
    required_fields = ['item_id', 'quantity']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Data tidak lengkap. Dibutuhkan: {', '.join(required_fields)}"}), 400
        
    item_id = data['item_id'].strip().upper()
    if item_id not in inventory_items:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    try:
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({"error": "Jumlah harus lebih dari 0"}), 400
    except ValueError:
        return jsonify({"error": "Jumlah harus berupa angka bulat positif"}), 400
        
    # Update stok di inventory
    inventory_items[item_id]['quantity'] += quantity
    inventory_items[item_id]['last_update'] = get_current_timestamp()
    
    # Buat transaksi baru
    new_transaction = {
        'id': next_transaction_id,
        'type': 'masuk',
        'item_id': item_id,
        'quantity': quantity,
        'user': session.get('user', {}).get('username', 'unknown'),
        'timestamp': get_current_timestamp(),
        'notes': data.get('notes', '')
    }
    
    transactions.append(new_transaction)
    next_transaction_id += 1
    
    return jsonify(new_transaction), 201

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
    if item_id not in inventory_items:
        return jsonify({"error": f"Item dengan ID {item_id} tidak ditemukan"}), 404
        
    try:
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({"error": "Jumlah harus lebih dari 0"}), 400
            
        # Cek stok mencukupi
        current_stock = inventory_items[item_id]['quantity']
        if quantity > current_stock:
            return jsonify({"error": f"Stok tidak mencukupi. Stok saat ini: {current_stock}"}), 400
            
    except ValueError:
        return jsonify({"error": "Jumlah harus berupa angka bulat positif"}), 400
        
    # Update stok di inventory
    inventory_items[item_id]['quantity'] -= quantity
    inventory_items[item_id]['last_update'] = get_current_timestamp()
    
    # Buat transaksi baru
    new_transaction = {
        'id': next_transaction_id,
        'type': 'keluar',
        'item_id': item_id,
        'quantity': quantity,
        'user': session.get('user', {}).get('username', 'unknown'),
        'timestamp': get_current_timestamp(),
        'notes': data.get('notes', '')
    }
    
    transactions.append(new_transaction)
    next_transaction_id += 1
    
    return jsonify(new_transaction), 201

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
        if username in users:
            return jsonify({"error": f"Username '{username}' sudah digunakan"}), 409
            
        if data['role'] not in ['admin', 'manajer', 'operator']:
            return jsonify({"error": "Role tidak valid"}), 400
            
        # Hash password sebelum disimpan
        hashed_password = hash_password(data['password'])
            
        # Simpan user baru dengan password yang sudah di-hash
        users[username] = {
            'password': hashed_password,
            'name': data['name'].strip(),
            'role': data['role']
        }
        
        # Return data user tanpa password
        return jsonify({
            'username': username,
            'name': users[username]['name'],
            'role': users[username]['role']
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Gagal menambahkan pengguna: {str(e)}"}), 500

@app.route('/api/users/<username>', methods=['PUT'])
@login_required
@role_required(['admin'])
def api_update_user(username):
    """API Endpoint untuk mengupdate data pengguna."""
    if username not in users:
        return jsonify({"error": f"Pengguna '{username}' tidak ditemukan"}), 404
        
    if not request.is_json:
        return jsonify({"error": "Request harus dalam format JSON"}), 400
        
    try:
        data = request.get_json()
        
        # Update name jika ada
        if 'name' in data:
            users[username]['name'] = data['name'].strip()
            
        # Update role jika ada dan valid
        if 'role' in data:
            if data['role'] not in ['admin', 'manajer', 'operator']:
                return jsonify({"error": "Role tidak valid"}), 400
            users[username]['role'] = data['role']
            
        # Update password jika ada
        if 'password' in data and data['password']:
            users[username]['password'] = data['password']  # TODO: Hash password
            
        # Return data user yang diupdate (tanpa password)
        return jsonify({
            'username': username,
            'name': users[username]['name'],
            'role': users[username]['role']
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Gagal mengupdate pengguna: {str(e)}"}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_user(username):
    """API Endpoint untuk menghapus pengguna."""
    if username not in users:
        return jsonify({"error": f"Pengguna '{username}' tidak ditemukan"}), 404
        
    # Cek apakah user mencoba menghapus dirinya sendiri
    if username == session.get('user', {}).get('username'):
        return jsonify({"error": "Tidak dapat menghapus akun yang sedang digunakan"}), 400
        
    try:
        del users[username]
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)