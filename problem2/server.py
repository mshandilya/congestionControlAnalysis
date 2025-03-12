import socket

HOST = '172.21.124.53'
PORT = 12345

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"[*] Server listening on {HOST}:{PORT}")
    
    while True:
        conn, addr = server_socket.accept()
        print(f"[+] Connected by {addr}")
        
        data = conn.recv(1024)
        if not data:
            print("[-] No data received, closing connection.")
            conn.close()
            continue
        
        print(f"[+] Received from client: {data.decode('utf-8')}")
        
        response = "Hello from server!"
        conn.sendall(response.encode('utf-8'))
        
        conn.close()

if __name__ == "__main__":
    start_server()
