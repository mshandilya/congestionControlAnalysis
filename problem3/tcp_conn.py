import socket
import argparse
import time
import threading
import pyshark
from datetime import datetime

packet_store = []

def packet_capture(capture_instance):
    try:
        for pkt in capture_instance.sniff_continuously():
            packet_store.append(pkt)
    except Exception as error:
        print("Exception in capture thread:", error)

def set_socket_options(sock, nagle_status, delayed_ack_status):
    if nagle_status == 'disabled':
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print("Nagle's algorithm is turned off (TCP_NODELAY activated)")
        except Exception as err:
            print("Error configuring TCP_NODELAY:", err)
    else:
        print("Nagle's algorithm remains enabled (default)")
        
    if delayed_ack_status == 'disabled':
        try:
            if hasattr(socket, 'TCP_QUICKACK'):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
                print("Delayed ACK is turned off (TCP_QUICKACK activated)")
        except Exception as err:
            print("Failed to disable delayed ACK:", err)
    else:
        print("Delayed ACK remains enabled (default)")

def evaluate_capture(packets):
    if not packets:
        print("No packets were captured")
        return None

    start_time = packets[0].sniff_time
    end_time = packets[-1].sniff_time
    duration = (end_time - start_time).total_seconds()
    ip_bytes_total = 0
    tcp_payload_total = 0
    largest_payload = 0
    lost_segment_count = 0
    tcp_segment_count = 0

    for pkt in packets:
        try:
            if hasattr(pkt, 'ip'):
                ip_bytes_total += int(pkt.ip.len)
            if hasattr(pkt, 'tcp'):
                tcp_segment_count += 1
                payload = int(pkt.tcp.len) if hasattr(pkt.tcp, 'len') else 0
                tcp_payload_total += payload
                if payload > largest_payload:
                    largest_payload = payload
                if hasattr(pkt.tcp, 'analysis_lost_segment'):
                    lost_segment_count += 1
        except Exception as error:
            print("Error processing packet:", error)
            continue

    overall_throughput = ip_bytes_total / duration if duration > 0 else 0
    effective_goodput = tcp_payload_total / duration if duration > 0 else 0
    loss_rate = (lost_segment_count / tcp_segment_count) * 100 if tcp_segment_count > 0 else 0

    return {
        'capture_duration': duration,
        'raw_throughput': overall_throughput,
        'goodput': effective_goodput,
        'max_payload': largest_payload,
        'packet_loss_rate': loss_rate
    }

def start_server(port, nagle_status, delayed_ack_status):
    capture_instance = pyshark.LiveCapture(interface='lo', bpf_filter=f'tcp port {port}')
    capture_thread = threading.Thread(target=packet_capture, args=(capture_instance,), daemon=True)
    capture_thread.start()
    print(f"Initiated packet capture on 'lo' for TCP port {port}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', port))
    server_socket.listen(1)
    print(f"Server is now listening on port {port}...")

    connection, address = server_socket.accept()
    print("Connection accepted from", address)

    set_socket_options(connection, nagle_status, delayed_ack_status)

    bytes_received = 0
    target_bytes = 4096
    while bytes_received < target_bytes:
        chunk = connection.recv(1024)
        if not chunk:
            break
        bytes_received += len(chunk)

    connection.close()
    server_socket.close()

    time.sleep(1)
    capture_thread.join(timeout=2)

    metrics = evaluate_capture(packet_store)
    print(f"Total bytes received: {bytes_received} bytes")
    print(f"Raw throughput (including headers): {metrics['raw_throughput']:.2f} bytes/second")
    print(f"Goodput (TCP payload only): {metrics['goodput']:.2f} bytes/second")
    print(f"Largest TCP payload size: {metrics['max_payload']} bytes")
    print(f"Approximate packet loss rate: {metrics['packet_loss_rate']:.2f}%")

def start_client(host, port, nagle_status, delayed_ack_status):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    set_socket_options(client_socket, nagle_status, delayed_ack_status)

    try:
        client_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}.")
    except Exception as error:
        print("Connection failed:", error)
        return

    message = b'A' * 4096
    chunk_size = 40
    total_chunks = len(message) // chunk_size
    for i in range(total_chunks):
        segment = message[i * chunk_size:(i + 1) * chunk_size]
        try:
            client_socket.sendall(segment)
        except Exception as error:
            print("Error sending data:", error)
            break
        time.sleep(1)
    remaining_bytes = len(message) % chunk_size
    if remaining_bytes:
        client_socket.sendall(message[total_chunks * chunk_size:])
    client_socket.close()

def main():
    parser = argparse.ArgumentParser(description="TCP connection test utility")
    parser.add_argument("--mode", choices=["server", "client"], required=True,
                        help="Run in 'server' or 'client' mode.")
    parser.add_argument("--host", default="172.21.124.53",
                        help="Server hostname (used in client mode).")
    parser.add_argument("--port", type=int, default=12345,
                        help="Port number for connection.")
    parser.add_argument("--nagle", choices=["enabled", "disabled"], required=True,
                        help="Enable or disable Nagle's algorithm.")
    parser.add_argument("--delayed_ack", choices=["enabled", "disabled"], required=True,
                        help="Enable or disable delayed ACK behavior.")
    args = parser.parse_args()
    
    if args.mode == "server":
        start_server(args.port, args.nagle, args.delayed_ack)
    else:
        start_client(args.host, args.port, args.nagle, args.delayed_ack)

if __name__ == "__main__":
    main()
