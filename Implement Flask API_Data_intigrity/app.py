import pyotp
import qrcode
import tempfile
import base64
from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# JWT configuration
app.config['JWT_SECRET_KEY'] = '6ea1abd4aba389631344fb9178577924-4496-ad8a-825691d3c700'
jwt = JWTManager(app)

# Database configuration
db_host = 'localhost'
db_user = 'root'
db_password = ''
db_name = 'mydatabase'

# Connect to MySQL Database
db = mysql.connector.connect(host=db_host, user=db_user, password=db_password, database=db_name)


# Endpoint to register a new user
@app.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.get_json()

    required_fields = ['username', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    hashed_password = generate_password_hash(data['password'])

    # Generate a secret key for 2FA
    totp = pyotp.TOTP(pyotp.random_base32())
    twofa_secret = totp.secret  

    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO Users (username, password, twofa_secret) 
            VALUES (%s, %s, %s)
        """, (data['username'], hashed_password, twofa_secret))
        db.commit()

        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()  


# Endpoint for user login 
# Verify & generate QR code
@app.route('/login', methods=['POST'])
def login_step_1():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    cursor = db.cursor()
    cursor.execute("SELECT password, twofa_secret FROM Users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user or not check_password_hash(user[0], password):  
        cursor.close()
        return jsonify({'error': 'Invalid username or password'}), 401

    # Generate a QR code for Google Authenticator
    totp = pyotp.TOTP(user[1])
    otp_uri = totp.provisioning_uri(username, issuer_name="MyApp")
    
    # Generate QR code as an image
    qr_img = qrcode.make(otp_uri)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_img.save(temp_file.name)

    cursor.close()

    # Send QR image to the user in postman 
    return send_file(temp_file.name, mimetype='image/png', as_attachment=False)


# Endpoint for user login to Verify 2FA code
@app.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    print("Request received!")

    # Check if request is JSON
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # Print received data
    print("Received data:", data)

    username = data.get('username')
    twofa_code = data.get('twofa_code')

    if not username or not twofa_code:
        print("Missing username or 2FA code!")
        return jsonify({'error': 'Missing username or 2FA code'}), 400

    cursor = db.cursor()
    cursor.execute("SELECT twofa_secret FROM Users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        return jsonify({'error': 'User not found'}), 404

    # Initialize TOTP and verify the 2FA code
    totp = pyotp.TOTP(user[0])
    if not totp.verify(twofa_code):
        cursor.close()
        return jsonify({'error': 'Invalid 2FA code'}), 401

    access_token = create_access_token(identity=username, expires_delta=False)
    cursor.close()
    return jsonify({'access_token': access_token}), 200


# Protected endpoint for testing JWT
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    return jsonify({'message': 'Access granted!'})


# Run of the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
