import threading
import subprocess

def run_app():
    subprocess.run(["python", "app.py"])

def run_products():
    subprocess.run(["python", "products.py"])

if __name__ == "__main__":
    # Start the app and products services in separate threads
    app_thread = threading.Thread(target=run_app)
    products_thread = threading.Thread(target=run_products)

    app_thread.start()
    products_thread.start()

    app_thread.join()
    products_thread.join()
