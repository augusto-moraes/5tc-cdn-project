import socket
import os
import mimetypes

HOST = "200.200.200.1"   # Listen on all interfaces (includes 200.200.200.1)
PORT = 80          # Use 80 for browser compatibility
BASE_DIR = "files" # Folder with HTML files

def handle_client(conn):
    try:
        request = conn.recv(1024).decode("utf-8", errors="ignore")
        print("Request:\n", request)

        # Extract filename from request
        try:
            path = request.split(" ")[1].lstrip("/")
        except IndexError:
            path = ""

        if path == "":
            path = "index.html"  # default page

        filepath = os.path.join(BASE_DIR, path)

        # Serve file if it exists
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                body = f.read()
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "text/html"
            header = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            )
            response = header.encode("utf-8") + body
        else:
            body = b"<h1>404 Not Found</h1>"
            header = (
                "HTTP/1.1 404 Not Found\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Content-Type: text/html\r\n\r\n"
            )
            response = header.encode("utf-8") + body

        conn.sendall(response)

    finally:
        conn.close()

def run_server():
    os.makedirs(BASE_DIR, exist_ok=True)  # Ensure folder exists
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server running at http://{HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            print("Connected:", addr)
            handle_client(conn)

if __name__ == "__main__":
    run_server()
