from flask import Flask, jsonify, request
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data dummy untuk simulasi
orders = {}

# Consumer endpoints
def get_user_data(user_id):
    response = requests.get(f'http://localhost:5001/api/users/{user_id}')
    return response.json()

def get_product_data(product_id):
    response = requests.get(f'http://localhost:5002/api/products/{product_id}')
    return response.json()

# Provider & Consumer endpoints
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    # Mengambil data user dan produk
    user = get_user_data(user_id)
    product = get_product_data(product_id)

    if 'error' in user or 'error' in product:
        return jsonify({"error": "Invalid user or product"}), 400

    new_id = max(orders.keys()) + 1 if orders else 1
    orders[new_id] = {
        "id": new_id,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "total_price": product['price'] * quantity,
        "status": "pending"
    }

    return jsonify(orders[new_id]), 201

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = orders.get(order_id)
    if order:
        # Memperkaya data order dengan informasi user dan produk
        user = get_user_data(order['user_id'])
        product = get_product_data(order['product_id'])
        
        enriched_order = {**order, 'user': user, 'product': product}
        return jsonify(enriched_order)
    return jsonify({"error": "Order not found"}), 404

@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify(list(orders.values()))

if __name__ == '__main__':
    app.run(port=5003) 