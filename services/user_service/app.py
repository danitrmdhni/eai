from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data dummy untuk simulasi
users = {
    1: {"id": 1, "name": "John Doe", "email": "john@example.com"},
    2: {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
}

# Provider endpoints
@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(list(users.values()))

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = users.get(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_id = max(users.keys()) + 1 if users else 1
    users[new_id] = {
        "id": new_id,
        "name": data.get("name"),
        "email": data.get("email")
    }
    return jsonify(users[new_id]), 201

# Consumer endpoint untuk transaksi
@app.route('/api/users/<int:user_id>/transactions', methods=['GET'])
def get_user_transactions(user_id):
    # Ini akan mengambil data transaksi dari OrderService
    # Implementasi sebenarnya akan memanggil OrderService
    return jsonify({"message": "This will fetch transactions from OrderService"})

if __name__ == '__main__':
    app.run(port=5001) 