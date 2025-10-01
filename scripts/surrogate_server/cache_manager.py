import os
import mimetypes
import random

CACHE_DIR = "cache"
CACHE_SIZE = 4

# Ensure the cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def add(filename, header_str, body):
    # Check if the cache is full
    if len(os.listdir(CACHE_DIR)) >= CACHE_SIZE:
        # Find the least recently used (LRU) file
        files = os.listdir(CACHE_DIR)
        lru_file = min(files, key=lambda f: os.path.getatime(os.path.join(CACHE_DIR, f)))
        lru_file_path = os.path.join(CACHE_DIR, lru_file)
        
        # Delete the LRU file
        os.remove(lru_file_path)
        print(f"Cache full. Deleted least recently used file: {lru_file}")
    
    # Determine the name of the file that was sent back by the central server
    filename_out = filename
    for line in header_str.split("\r\n"):
        if line.startswith("Content-Disposition:"):
            parts = line.split("filename=")
            if len(parts) > 1:
                filename_out = parts[1].strip('"')
    
    filepath = os.path.join(CACHE_DIR, filename_out)

    # Cache the body of the response (=file) in the caching directory of this surrogate server
    with open(filepath, "wb") as f:
        f.write(body)

    print(f"Fichier téléchargé : {filepath}")

def is_in_cache(file_name):
    return os.path.isfile(os.path.join(CACHE_DIR, file_name))

def get(file_name):
    # get existing file
    filepath = os.path.join(CACHE_DIR, file_name)
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

def clear():
    for file_name in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
    print("Cache cleared.")