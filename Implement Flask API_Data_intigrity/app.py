import pyotp
import qrcode
from flask import Flask, request, jsonify
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

    # Check if all required fields are provided
    required_fields = ['username', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Hash the password before storing it
    hashed_password = generate_password_hash(data['password'])

    # Generate a secret key for Google Authenticator to store in the database
    totp = pyotp.TOTP(pyotp.random_base32())
    # Get the secret key
    twofa_secret = totp.secret  

    cursor = db.cursor()
    try:
        # Insert the new user into the database with the 2FA secret
        cursor.execute("""
            INSERT INTO Users (username, password, twofa_secret) 
            VALUES (%s, %s, %s)
        """, (
            data['username'], hashed_password, twofa_secret
        ))
        db.commit()

        # Generate a QR code for Google Authenticator
        otp_uri = totp.provisioning_uri(data['username'], issuer_name="MyApp")
        img = qrcode.make(otp_uri)
        img.save(f"{data['username']}_qr.png")

        return jsonify({
            'message': 'User created successfully',
            # Return the QR code filename
            'qr_code': f"{data['username']}_qr.png"  
        }), 201
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()  


# Endpoint for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    # Get the 2FA code from the request
    twofa_code = data.get('twofa_code')  

# Check if the username, password, and 2FA code are provided
# If not, return an error message
    if not twofa_code:
        return jsonify({'message': 'Missing 2FA code'}), 400

    # Check if the username exists in the database
    cursor = db.cursor()
    cursor.execute("SELECT password, twofa_secret FROM Users WHERE username = %s", (username,))
    user = cursor.fetchone()

    # Check if passwords match and the 2FA code is valid
    if user and check_password_hash(user[0], password):  
        # Initialize the TOTP object with the user's secret
        totp = pyotp.TOTP(user[1])

        # Verify the 2FA code
        if totp.verify(twofa_code):
            # Generate access token valid for 10 minutes
            access_token = create_access_token(identity=username, expires_delta=False)
            cursor.close()
            return jsonify({'access_token': access_token}), 200
        else:
            cursor.close()
            return jsonify({'message': 'Invalid 2FA code'}), 401
    else:
        cursor.close()
        return jsonify({'message': 'Invalid username or password'}), 401


# Endpoint to test 2FA code
@app.route('/test-2fa', methods=['GET'])
@jwt_required()
def test_2fa():
    username = request.args.get('username')

    # Retrieve the 2FA secret from the database
    cursor = db.cursor()
    cursor.execute("SELECT twofa_secret FROM Users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        # Initialize the TOTP object with the user's secret
        totp = pyotp.TOTP(user[0])
        # Generate the current 2FA code
        current_code = totp.now()
        return jsonify({'message': 'Current 2FA code', 'code': current_code}), 200
    else:
        cursor.close()
        return jsonify({'message': 'User not found'}), 404


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
