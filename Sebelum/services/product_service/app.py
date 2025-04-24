from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data dummy untuk simulasi
products = {
    1: {"id": 1, "name": "Laptop", "price": 1000, "stock": 10},
    2: {"id": 2, "name": "Smartphone", "price": 500, "stock": 20}
}

# Provider endpoints
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(list(products.values()))

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = products.get(product_id)
    if product:
        return jsonify(product)
    return jsonify({"error": "Product not found"}), 404

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()
    new_id = max(products.keys()) + 1 if products else 1
    products[new_id] = {
        "id": new_id,
        "name": data.get("name"),
        "price": data.get("price"),
        "stock": data.get("stock", 0)
    }
    return jsonify(products[new_id]), 201

# Consumer endpoint untuk user
@app.route('/api/products/<int:product_id>/user', methods=['GET'])
def get_product_user(product_id):
    # Ini akan mengambil data user dari UserService
    # Implementasi sebenarnya akan memanggil UserService
    return jsonify({"message": "This will fetch user data from UserService"})

if __name__ == '__main__':
    app.run(port=5002) 