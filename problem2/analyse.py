import pyshark
import matplotlib.pyplot as plt

def get_key(src_ip, dst_ip, src_port, dst_port):
    sp = int(src_port)
    dp = int(dst_port)
    
    if (src_ip < dst_ip) or (src_ip == dst_ip and sp < dp):
        return (src_ip, dst_ip, sp, dp)
    else:
        return (dst_ip, src_ip, dp, sp)

def parse_pcap(pcap_file):
    capture = pyshark.FileCapture(pcap_file, display_filter='tcp')
    connections = {}
    base_time = None

    for packet in capture:
        try:
            src_ip = packet.ip.src
            dst_ip = packet.ip.dst
            src_port = packet.tcp.srcport
            dst_port = packet.tcp.dstport
            timestamp = float(packet.sniff_timestamp)
            if base_time is None:
                base_time = timestamp
            timestamp -= base_time

            syn_flag = int(packet.tcp.flags_syn)
            ack_flag = int(packet.tcp.flags_ack)
            fin_flag = int(packet.tcp.flags_fin)
            rst_flag = int(packet.tcp.flags_reset)
            
            seq_num = int(packet.tcp.seq)
            ack_num = int(packet.tcp.ack) if 'ack' in packet.tcp.field_names else None
            
            conn_key = get_key(src_ip, dst_ip, src_port, dst_port)
            if conn_key not in connections:
                connections[conn_key] = {
                    'start_time': None,
                    'fin_seq': None,
                    'fin_ack_needed': None,
                    'end_time': None,
                    'closed': False
                }
            conn = connections[conn_key]
            
            if syn_flag == 1 and ack_flag == 0 and conn['start_time'] is None:
                conn['start_time'] = timestamp
            
            if rst_flag == 1 and not conn['closed']:
                if conn['start_time'] is None:
                    conn['start_time'] = timestamp
                conn['end_time'] = timestamp
                conn['closed'] = True
            
            if fin_flag == 1 and not conn['closed']:
                conn['fin_seq'] = seq_num
                conn['fin_ack_needed'] = seq_num + 1
            
            if ack_flag == 1 and not conn['closed'] and conn['fin_ack_needed'] is not None:
                if ack_num == conn['fin_ack_needed']:
                    if conn['start_time'] is None:
                        conn['start_time'] = timestamp
                    conn['end_time'] = timestamp
                    conn['closed'] = True
        except AttributeError:
            continue
    
    capture.close()
    
    results = []
    for key, conn in connections.items():
        if conn['start_time'] is not None:
            if conn['end_time'] is not None:
                duration = conn['end_time'] - conn['start_time']
            else:
                duration = 100.0
            results.append((conn['start_time'], duration))
    
    results.sort(key=lambda x: x[0])
    return results

def plot_results(results):
    start_times = [r[0] for r in results]
    durations   = [r[1] for r in results]
    
    plt.figure(figsize=(10, 6))
    plt.scatter(start_times, durations, color='blue', alpha=0.7, label='Connections')
    
    plt.axvline(x=20,  color='red', linestyle='--', label='Attack Start (20s)')
    plt.axvline(x=120, color='green', linestyle='--', label='Attack End (120s)')
    
    plt.xlabel('Connection Start Time (seconds)')
    plt.ylabel('Connection Duration (seconds)')
    plt.title('TCP Connection Durations')
    plt.legend()
    plt.grid(True)
    plt.savefig('plot.png')

def main():
    pcap_file = 'synflood.pcap'
    results = parse_pcap(pcap_file)
    plot_results(results)

if __name__ == '__main__':
    main()
