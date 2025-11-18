import socket
import os
import mimetypes

# CENTRAL SERVER
HOST = "192.168.4.100" 
PORT = 3000 
BASE_DIR = "cache"

#HOST = "127.0.0.1" # for testing purposes

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

            # Forces download of the file so that the surrogates can cache it
            header = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Content-Type: {mime_type}\r\n"
                f"Content-Disposition: attachment; filename=\"{os.path.basename(filepath)}\"\r\n\r\n"
            )

            response = header.encode("utf-8") + body

            print(f"[INFO] Requested file {filepath} served.")

        else:
            # Return an HTTP 404 code when the central server doesn't have the file.
            header = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Length: 0\r\n"
                "Content-Type: text/plain\r\n\r\n"
            )

            goat_image = ERROR_GOATS.get(404, None)

            body = f"""
            <html>
            <head><title>404 Not Found</title></head>
            <body>
                <h1>Oops! Page not found</h1>
                <img src="/{goat_image}" alt="404 Goat" style="max-width:600px;">
            </body>
            </html>
            """.encode("utf-8")

            response = header.encode("utf-8") + body

            print(f"[INFO] Requested file {filepath} not found. 404 error sent.")

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