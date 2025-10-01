import socket
import os
import mimetypes

HOST = "200.200.200.1"
PORT = 80
BASE_DIR = "files"

# Map HTTP status codes to local goat images
ERROR_GOATS = {
    400: "400.jpg",
    404: "404.jpg",
    500: "500.jpg",
    200: "200.jpg"
}

def handle_client(conn):
    try:
        request = conn.recv(1024).decode("utf-8", errors="ignore")
        print("Request:\n", request)

        try:
            path = request.split(" ")[1].lstrip("/")
        except IndexError:
            path = ""

        if path == "":
            path = "index.html"

        filepath = os.path.join(BASE_DIR, path)

        if os.path.isfile(filepath):
            # Serve existing file
            with open(filepath, "rb") as f:
                body = f.read()
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "application/octet-stream"
            header = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            )
            response = header.encode("utf-8") + body

        else:
            # Serve 404 page with local goat image
            goat_image = ERROR_GOATS.get(404, None)
            if goat_image and os.path.isfile(os.path.join(BASE_DIR, goat_image)):
                body = f"""
                <html>
                <head><title>404 Not Found</title></head>
                <body>
                    <h1>Oops! Page not found</h1>
                    <img src="/{goat_image}" alt="404 Goat" style="max-width:600px;">
                </body>
                </html>
                """.encode("utf-8")
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
    os.makedirs(BASE_DIR, exist_ok=True)
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
