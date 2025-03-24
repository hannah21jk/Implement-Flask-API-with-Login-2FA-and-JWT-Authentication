import secrets
def generate_jwt_secret_key(length=32):
    jwt_secret_key=secrets.token_hex(length//2)
    return jwt_secret_key
if __name__ == '__main__':
  jwt_secret_key=generate_jwt_secret_key()
  print("JWT Secret Key:", jwt_secret_key)