import socket

# local imports
import cache_manager
import mimetypes

HOST = "192.168.1.100"
PORT = 3030

CENTRAL_HOST = "192.168.4.100" # to change
CENTRAL_PORT = 3000 # to change

HOST_TO_CENTRAL = "192.168.X.100" # surrogate server address used to connect to the central server to change

# # for local testing
# HOST = "127.0.0.1"
# CENTRAL_HOST = "127.0.0.1"
# HOST_TO_CENTRAL = "127.0.0.1"

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
            file = request.split(" ")[1].lstrip("/")
        except IndexError:
            file = ""

        if file == "":
            file = "index.html"

        if not cache_manager.is_in_cache(file):
            response = http_get(file)
        else:
            response = cache_manager.get(file)
        conn.sendall(response)

    finally:
        conn.close()

def http_get(filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST_TO_CENTRAL, 0))
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

    # /!\ Remove headers that force download and ensure correct Content-Type/Length
    header_lines = header_str.split("\r\n")
    filtered = []
    existing_content_type = None

    for line in header_lines:
        low = line.lower()
        if low.startswith("content-disposition:"):
            # strip any forced download disposition
            continue
        if low.startswith("content-length:"):
            # we'll recalc length below
            continue
        if low.startswith("content-type:"):
            existing_content_type = line.split(":", 1)[1].strip()
            continue
        filtered.append(line)

    # Choose a sensible Content-Type based on filename if possible
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = existing_content_type or "application/octet-stream"

    filtered.append(f"Content-Type: {mime_type}")
    filtered.append(f"Content-Length: {len(body)}")

    header_str = "\r\n".join(filtered)

    print("En-têtes filtré:\n", header_str)

    # If the central server responds with a 404 error
    if "404 Not Found" in header_str:
        # Serve 404 page with local goat image
        goat_image = ERROR_GOATS.get(404, None)
        if goat_image and cache_manager.is_in_cache(goat_image):
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
        cache_manager.add(filename, header_str, body)
        return response

def run_server():
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
