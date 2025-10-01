import socket
import os
import mimetypes
import requests

HOST = "127.0.0.1"
PORT = 3030
BASE_DIR = "files"

CENTRAL_HOST = "127.0.0.1" # to change
CENTRAL_PORT = 3000 # to change

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
            response = response_to_client(filepath)

        # If the file is not cached in this server
        else:
            # Fetch content from the central server and cache it
            response = http_get(path)
            # Caching strategy

        conn.sendall(response)

    finally:
        conn.close()

def response_to_client(filepath):
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
    return response

def http_get(filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((CENTRAL_HOST, CENTRAL_PORT))
        request = f"GET /{filename} HTTP/1.1\r\nHost: {CENTRAL_HOST}\r\n\r\n"
        s.sendall(request.encode("utf-8"))

        # Receiving the entire response from the central server
        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk

    # Separate header and body
    header, body = response.split(b"\r\n\r\n", 1)
    header_str = header.decode("utf-8", errors="ignore")
    print("En-têtes reçus:\n", header_str)

    # Create the caching directory if it doesn't already exist
    os.makedirs(BASE_DIR, exist_ok=True)

    # Determine the name of the file that was sent back by the central server
    filename_out = filename
    for line in header_str.split("\r\n"):
        if line.startswith("Content-Disposition:"):
            parts = line.split("filename=")
            if len(parts) > 1:
                filename_out = parts[1].strip('"')
    
    filepath = os.path.join(BASE_DIR, filename_out)

    # Cache the body of the response (=file) in the caching directory of this surrogate server
    with open(filepath, "wb") as f:
        f.write(body)

    print(f"Fichier téléchargé : {filepath}")

    # If the central server responds with a 404 error
    if "404 Not Found" in header_str:
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
        return response
    else:
        filepath = os.path.join(BASE_DIR, filename)
        return response_to_client(filepath)

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
