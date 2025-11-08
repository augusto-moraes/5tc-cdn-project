import socket
import os

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

# --- 404 Template Handling ---
# Define the path to the 404 HTML template file
_404_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', '404.html')
_404_PAGE_TEMPLATE = None # Will store the loaded template string
_SIMPLE_404_FALLBACK = b"<h1>404 Not Found</h1>" # A basic fallback HTML as bytes

# Attempt to load the 404 template file once at startup
try:
    with open(_404_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        _404_PAGE_TEMPLATE = f.read()
except FileNotFoundError:
    print(f"WARNING: 404 template file not found at {_404_TEMPLATE_PATH}. Using simple fallback for 404 errors.")
except Exception as e:
    print(f"WARNING: Error reading 404 template file {_404_TEMPLATE_PATH}: {e}. Using simple fallback for 404 errors.")
# --- End 404 Template Handling ---

def _build_404_response():
    """Builds and returns a complete HTTP 404 response."""
    goat_image = ERROR_GOATS.get(404)
    body = _SIMPLE_404_FALLBACK  # Default to the simple fallback

    # Attempt to use the template if it was loaded and the goat image is cached
    if _404_PAGE_TEMPLATE and goat_image and cache_manager.is_in_cache(goat_image):
        try:
            # Format the template with the goat image path and encode to bytes
            formatted_body = _404_PAGE_TEMPLATE.format(goat_image=goat_image)
            body = formatted_body.encode("utf-8")
        except KeyError:
            # This happens if the template is missing the {goat_image} placeholder
            print(f"WARNING: 404 template at {_404_TEMPLATE_PATH} is malformed (missing '{{goat_image}}' placeholder). Using simple fallback.")
        except Exception as e:
            # Catch any other unexpected rendering errors
            print(f"WARNING: An unexpected error occurred while rendering 404 template: {e}. Using simple fallback.")

    header = (
        "HTTP/1.1 404 Not Found\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Content-Type: text/html\r\n\r\n"
    )
    return header.encode("utf-8") + body

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
    try:
        header, body = response.split(b"\r\n\r\n", 1)
    except ValueError:
        # Handle cases where the response is malformed (e.g., no body)
        header, body = response, b""

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
        return _build_404_response()

    else:
        cache_manager.add(filename, header_str, body)
        return cache_manager.get(filename)

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