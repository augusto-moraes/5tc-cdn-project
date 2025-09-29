import socket

HOST = "127.0.0.1"
PORT = 8080

def http_get(filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        request = f"GET /{filename} HTTP/1.1\r\nHost: {HOST}\r\n\r\n"
        s.sendall(request.encode("utf-8"))

        response = s.recv(4096).decode("utf-8", errors="ignore")
        print("Réponse du serveur:\n")
        print(response)

if __name__ == "__main__":
    http_get("test.txt")   # essaie avec un fichier qui existe
    http_get("notfound.txt")  # essaie avec un fichier qui n’existe pas
