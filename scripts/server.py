import socket
import os

HOST = "127.0.0.1"   # Localhost: à changer
PORT = 8080          # Port du serveur
BASE_DIR = "files"   # Dossier où chercher les fichiers

def handle_client(conn):
    request = conn.recv(1024).decode("utf-8")
    print("Requête reçue :\n", request)

    # Récupération du nom de fichier depuis la requête
    try:
        filename = request.split(" ")[1].lstrip("/")
    except IndexError:
        filename = ""

    filepath = os.path.join(BASE_DIR, filename)

    if os.path.isfile(filepath):
        with open(filepath, "rb") as f:
            body = f.read()
        header = "HTTP/1.1 200 OK\r\n"
    else:
        header = "HTTP/1.1 404 Not Found\r\n"

    response = header.encode("utf-8")
    conn.sendall(response)
    conn.close()

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Serveur démarré sur http://{HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            print("Connexion de", addr)
            handle_client(conn)

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)  # Crée le dossier si inexistant
    run_server()
