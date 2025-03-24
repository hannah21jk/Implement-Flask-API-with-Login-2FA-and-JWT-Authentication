from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import mysql.connector

app = Flask(__name__)

# JWT configuration
app.config['JWT_SECRET_KEY'] = '6ea1abd4aba389631344fb9178577924-4496-ad8a-825691d3c700'
jwt = JWTManager(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'mydatabase'
}

# Function to create a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Function to check if product exists
def product_exists(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Products WHERE id=%s", (product_id,))
    exists = cursor.fetchone()
    cursor.close()
    conn.close()
    return exists is not None

# Endpoint to create a new product
@app.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.get_json()
    
    required_fields = ["name", "description", "price", "quantity"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Products (name, description, price, quantity) 
            VALUES (%s, %s, %s, %s)
        """, (data['name'], data['description'], data['price'], data['quantity']))
        
        conn.commit()
        return jsonify({'message': 'Product created successfully'}), 201
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# Endpoint to get all products
@app.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Products")
        products = cursor.fetchall()
        return jsonify(products), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# Endpoint to get a single product by ID
@app.route('/products/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Products WHERE id=%s", (product_id,))
        product = cursor.fetchone()

        if not product:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(product), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# Endpoint to update a product by ID
@app.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.get_json()
    required_fields = ["name", "description", "price", "quantity"]
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if not product_exists(product_id):
        return jsonify({'error': 'Product not found'}), 404

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Products 
            SET name=%s, description=%s, price=%s, quantity=%s 
            WHERE id=%s
        """, (data['name'], data['description'], data['price'], data['quantity'], product_id))

        conn.commit()
        return jsonify({'message': 'Product updated successfully'}), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# Endpoint to delete a product by ID
@app.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    if not product_exists(product_id):
        return jsonify({'error': 'Product not found'}), 404

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Products WHERE id=%s", (product_id,))
        conn.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()

# Endpoint for user login
@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username == 'hannah' and password == 'hannah21':
        access_token = create_access_token(identity=username)
        return jsonify({'access_token': access_token}), 200
    return jsonify({'message': 'Invalid username or password'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
