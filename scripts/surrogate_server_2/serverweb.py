import socket

# local imports
import cache_manager
import mimetypes
import threading

import time

# SURROGATE 2
# Anycast address: communication with the client
HOST = "192.168.1.100"
PORT = 3030

# Second interface: communication with peers and central server
HOST_TO_CENTRAL = "192.168.6.100"

# CENTRAL SERVER
CENTRAL_HOST = "192.168.4.100" 
CENTRAL_PORT = 3000 

# SURROGATE PEERS
# List of surrogates in the same AS
SURROGATE_PEERS = [
   ("192.168.5.100", 3030)
]

""" # for local testing
HOST = "127.0.0.1"
CENTRAL_HOST = "127.0.0.1"
HOST_TO_CENTRAL = "127.0.0.1" """

# Function to handle the communication with the client and the peers
# 1) CLIENT REQUEST: anycast address
# If in cache, send the file.
# If not, ask the peers. 
# If no peer has the file, ask the central server.

# 2) PEER REQUEST: interface 2
# If in cache, send the file.
# If not, send a 404 response.
def handle_client(conn):
    try:
        print(f"######### [INFO] Time : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} #########")
        conn.settimeout(3)  # Set a timeout of 3 seconds

        try:
            request = conn.recv(1024).decode("utf-8", errors="ignore")
        except socket.timeout:
            print("[Error] Request timed out.")
            return
        
        print("Request:\n", request)

        try:
            file = request.split(" ")[1].lstrip("/")
        except Exception as e:
            print(f"[Error] Exception: {e}, aborting.")
            return

        if file == "":
            file = "index.html"

        cache_manager.checkTTL()

        client_ip = conn.getpeername()[0]
        
        # If the request comes from a peer (another surrogate)
        # In this case, the surrogate receives the request on its second interface
        if client_ip.startswith("192.168."):
            print(f"[INFO] Request from peer {client_ip} for {file}")
            if cache_manager.is_in_cache(file):
                response = cache_manager.get(file)
                print(f"[INFO] requested file {file} sent to peer {client_ip}.")
            else:
                # If the requested file is not in the local cache, send a 404 response to the peer
                body = b"File not found on this surrogate"
                header = (
                    "HTTP/1.1 404 Not Found\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Content-Type: text/plain\r\n\r\n"
                )
                response = header.encode("utf-8") + body

        # If the request comes from a client
        # In this case, the surrogate receives the request on its anycast address: 192.168.1.100
        else:
            # 1) Check if the file is in the cache
            if cache_manager.is_in_cache(file):
                print(f"[INFO] Cache hit for {file}")
                response = cache_manager.get(file)

            # 2) If not in the cache, ask peers for file
            else:
                print(f"[INFO] Cache miss for {file}, asking peers...")
                response = ask_peers_for_file(file)

                if response:
                    print(f"[INFO] Got {file} from peer")
                    # Store the file in the local cache
                    header, body = response.split(b"\r\n\r\n", 1)
                    cache_manager.add(file, header.decode("utf-8", errors="ignore"), body)
                                
                # 3) If no peer has the file, ask the central server
                else:
                    print(f"[INFO] File not found on peers, fetching from central server...")
                    response = http_get(file)

        conn.sendall(response)

    finally:
        conn.close()

# Application-level broadcast
# Send a unicast request for a file to all the peers in the list
# Communicate through the second interface
def ask_peers_for_file(filename):
    for host, port in SURROGATE_PEERS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_sock:
                peer_sock.bind((HOST_TO_CENTRAL, 0))
                peer_sock.connect((host, port))
                print(f"peer host: {host}")
                print(f"peer port: {port}")

                request = f"GET /{filename} HTTP/1.1\r\nHost: {host}\r\n\r\n"
                peer_sock.sendall(request.encode("utf-8"))

                response = b""
                while True:
                    chunk = peer_sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                # If the response is a 200 OK: the peer had the file and sent it
                if b"200 OK" in response.split(b"\r\n\r\n", 1)[0]:
                    print(f"[INFO] Found {filename} on peer {host}")
                    return response

        except Exception as e:
            continue

    # If none of the peers had the file, we return None
    print(f"[INFO] {filename} not found on any peer.")
    return None

# Send a request for a file to the central server
# Communicate through the second interface
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
        print("[INFO] Central server returned 404, forwarding HTML error page to client.")
        
        # Force valid HTTP headers to send to browser
        new_header = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
        )
        return new_header.encode("utf-8") + body

    else:
        cache_manager.add(filename, header_str, body)
        return cache_manager.get(filename)

# Run the two servers on two threads:
# 1) Server on the anycast address: 192.168.1.100 to communicate with the client
# 2) Server on the second interface to receive requests from peers
def run_server(host):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, PORT))
        s.listen()
        print(f"Server running at http://{host}:{PORT}")
        while True:
            conn, addr = s.accept()
            print(f"\n######### Connected on {host} from {addr} #########")
            handle_client(conn)

if __name__ == "__main__":
    # 1) Interface for the clients
    t1 = threading.Thread(target=run_server, args=(HOST,))

    # 2) Interface to listen to peer requests
    t2 = threading.Thread(target=run_server, args=(HOST_TO_CENTRAL,))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

if __name__ == "__main__":
    run_server()