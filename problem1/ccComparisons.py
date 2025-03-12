#!/usr/bin/env python

import argparse
import time
import os

from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel, info


class CustomTopo(Topo):

    def build(self, enable_all_links=False, option='a', suboption=None, loss = 0):
        # Create switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Create hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        h7 = self.addHost('h7')

        # Host-to-switch links (no special params by default)
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s2)
        self.addLink(h4, s3)
        self.addLink(h5, s3)
        self.addLink(h6, s4)
        self.addLink(h7, s4)

        # Switch-to-switch links
        #
        # For parts (c) and (d), you can specify bandwidth, loss, etc.
        # by passing bw=, loss=, etc. to the addLink(...) with cls=TCLink.
        #
        # Example default for demonstration: 100Mbps on all, 0% loss
        match(option):
            case 'a' | 'b':
                self.addLink(s1, s2, cls=TCLink)
                self.addLink(s2, s3, cls=TCLink)
                self.addLink(s3, s4, cls=TCLink)
            case 'c':
                self.addLink(s1, s2, cls=TCLink, bw=100)
                self.addLink(s2, s3, cls=TCLink, bw=50)
                self.addLink(s3, s4, cls=TCLink, bw=100)
            case 'd':
                self.addLink(s1, s2, cls=TCLink, bw=100)
                self.addLink(s2, s3, cls=TCLink, bw=50, loss=loss)
                self.addLink(s3, s4, cls=TCLink, bw=100)
            case _:
                self.addLink(s1, s2, cls=TCLink)
                self.addLink(s2, s3, cls=TCLink)
                self.addLink(s3, s4, cls=TCLink)

        # Optionally add s4-s1 to make a square:
        if enable_all_links:
            self.addLink(s4, s1, cls=TCLink, bw=100)
            self.addLink(s2, s4, cls=TCLink, bw=50)  # If you want S2-S4 in certain scenarios


def configure_congestion_control(net, cc_algo):
    for i in range(1, 8):
        host = net.get(f'h{i}')
        host.cmd(f'sysctl -w net.ipv4.tcp_congestion_control={cc_algo}')


def run_option_a(net, cc_algo):
    info("\n*** Running option (a): Single flow H1->H7\n")
    server = net.get('h7')
    client = net.get('h1')
    server_ip = server.IP()
    port = 5001

    # Start iperf server in background
    info("*** Starting iperf3 server on h7...\n")
    server.cmdPrint(f'iperf3 -s -p {port} &')
    server.cmdPrint(f'tcpdump -i h7-eth0 -w /tmp/a_capture_{cc_algo}.pcap &')
    time.sleep(2)

    # Start iperf client
    info("*** Starting iperf3 client on h1...\n")
    client.cmdPrint(f'iperf3 -c {server_ip} -p {port} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log &')
    time.sleep(160)
    info("*** Data transmission complete.\n")


def run_option_b(net, cc_algo):
    info("\n*** Running option (b): Staggered flows H1,H3,H4->H7\n")
    server = net.get('h7')
    server_ip = server.IP()
    port1 = 5001
    port2 = 5002
    port3 = 5003

    h1 = net.get('h1')
    h3 = net.get('h3')
    h4 = net.get('h4')

    # Start iperf server in background (can handle multiple clients)
    server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
    server.cmdPrint(f'tcpdump -i h7-eth0 -w /tmp/b_capture_{cc_algo}.pcap &')
    time.sleep(2)

    info("*** Starting iperf client on h1 at t=0\n")
    h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
    time.sleep(13)
    info("*** Starting iperf client on h3 at t=15\n")
    server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
    time.sleep(2)
    h3.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 120 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
    time.sleep(13)
    info("*** Starting iperf client on h4 at t=30\n")
    server.cmdPrint(f'iperf3 -s -p {port3} > /tmp/h7.log 2> /tmp/h7err.log &')
    h4.cmdPrint(f'iperf3 -c {server_ip} -p {port3} -b 10M -P 10 -t 90 -C {cc_algo} > /tmp/h4.log 2> /tmp/h4err.log &')
    time.sleep(210)
    info("*** All staggered flows completed.\n")


def run_option_c(net, cc_algo, suboption = '1'):
    info("\n*** Running option (c).\n")
    if suboption == '1':
        net.configLinkStatus('s1', 's2', 'down')
        server = net.get('h7')
        client = net.get('h3')
        server_ip = server.IP()
        port = 5001
        server.cmdPrint(f'iperf3 -s -p {port} &')
        server.cmdPrint(f'tcpdump -i any -w /tmp/c1_capture_{cc_algo}.pcap &')
        time.sleep(2)

        client.cmdPrint(f'iperf3 -c {server_ip} -p {port} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
        time.sleep(160)
        info("*** Data transmission complete.\n")
        net.configLinkStatus('s1', 's2', 'up')

    elif suboption.startswith('2'):
        match(suboption[1:]):
            case 'a':
                server = net.get('h7')
                server_ip = server.IP()
                port1 = 5001
                port2 = 5002

                h1 = net.get('h1')
                h2 = net.get('h2')

                # Start iperf server in background (can handle multiple clients)
                server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'tcpdump -i any -w /tmp/c2a_capture_{cc_algo}.pcap &')
                time.sleep(2)

                info("*** Starting iperf client on all clients\n")
                h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
                h2.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
                time.sleep(300)
                info("*** All flows completed.\n")
            case 'b':
                server = net.get('h7')
                server_ip = server.IP()
                port1 = 5001
                port2 = 5002

                h1 = net.get('h1')
                h3 = net.get('h3')

                # Start iperf server in background (can handle multiple clients)
                server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'tcpdump -i any -w /tmp/c2b_capture_{cc_algo}.pcap &')
                time.sleep(2)

                info("*** Starting iperf client on all clients\n")
                h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
                h3.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
                time.sleep(300)
                info("*** All flows completed.\n")
            case 'c':
                server = net.get('h7')
                server_ip = server.IP()
                port1 = 5001
                port2 = 5002
                port3 = 5003

                h1 = net.get('h1')
                h3 = net.get('h3')
                h4 = net.get('h4')

                # Start iperf server in background (can handle multiple clients)
                server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port3} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'tcpdump -i any -w /tmp/c2c_capture_{cc_algo}.pcap &')
                time.sleep(2)

                info("*** Starting iperf client on all clients\n")
                h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
                h3.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
                h4.cmdPrint(f'iperf3 -c {server_ip} -p {port3} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h4.log 2> /tmp/h4err.log &')
                time.sleep(450)
                info("*** All flows completed.\n")
            case _:
                info("*** Unknown option. Starting CLI for manual debugging...\n")        
    else:
        info("*** Unknown option. Starting CLI for manual debugging...\n")

def run_option_d(net, cc_algo, suboption = '1'):
    info("\n*** Running option (d).\n")
    if suboption == '1':
        net.configLinkStatus('s1', 's2', 'down')
        server = net.get('h7')
        client = net.get('h3')
        server_ip = server.IP()
        port = 5001
        server.cmdPrint(f'iperf3 -s -p {port} &')
        server.cmdPrint(f'tcpdump -i any -w /tmp/d1_capture_{cc_algo}.pcap &')
        time.sleep(2)

        client.cmdPrint(f'iperf3 -c {server_ip} -p {port} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
        time.sleep(160)
        info("*** Data transmission complete.\n")
        net.configLinkStatus('s1', 's2', 'up')

    elif suboption.startswith('2'):
        match(suboption[1:]):
            case 'a':
                server = net.get('h7')
                server_ip = server.IP()
                port1 = 5001
                port2 = 5002

                h1 = net.get('h1')
                h2 = net.get('h2')

                # Start iperf server in background (can handle multiple clients)
                server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'tcpdump -i any -w /tmp/d2a_capture_{cc_algo}.pcap &')
                time.sleep(2)

                info("*** Starting iperf client on all clients\n")
                h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
                h2.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
                time.sleep(300)
                info("*** All flows completed.\n")
            case 'b':
                server = net.get('h7')
                server_ip = server.IP()
                port1 = 5001
                port2 = 5002

                h1 = net.get('h1')
                h3 = net.get('h3')

                # Start iperf server in background (can handle multiple clients)
                server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'tcpdump -i any -w /tmp/d2b_capture_{cc_algo}.pcap &')
                time.sleep(2)

                info("*** Starting iperf client on all clients\n")
                h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
                h3.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
                time.sleep(300)
                info("*** All flows completed.\n")
            case 'c':
                server = net.get('h7')
                server_ip = server.IP()
                port1 = 5001
                port2 = 5002
                port3 = 5003

                h1 = net.get('h1')
                h3 = net.get('h3')
                h4 = net.get('h4')

                # Start iperf server in background (can handle multiple clients)
                server.cmdPrint(f'iperf3 -s -p {port1} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port2} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'iperf3 -s -p {port3} > /tmp/h7.log 2> /tmp/h7err.log &')
                server.cmdPrint(f'tcpdump -i any -w /tmp/d2c_capture_{cc_algo}.pcap &')
                time.sleep(2)

                info("*** Starting iperf client on all clients\n")
                h1.cmdPrint(f'iperf3 -c {server_ip} -p {port1} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h1.log 2> /tmp/h1err.log &')
                h3.cmdPrint(f'iperf3 -c {server_ip} -p {port2} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h3.log 2> /tmp/h3err.log &')
                h4.cmdPrint(f'iperf3 -c {server_ip} -p {port3} -b 10M -P 10 -t 150 -C {cc_algo} > /tmp/h4.log 2> /tmp/h4err.log &')
                time.sleep(450)
                info("*** All flows completed.\n")
            case _:
                info("*** Unknown option. Starting CLI for manual debugging...\n")        
    else:
        info("*** Unknown option. Starting CLI for manual debugging...\n")


def main():
    setLogLevel('info')

    parser = argparse.ArgumentParser(description="Custom Mininet Topology for TCP Congestion Experiments")
    parser.add_argument('--option', '-o', type=str, default='a',
                        help='Which experiment option to run: a, b, c, d, etc.')
    parser.add_argument('--cc', type=str, default='yeah',
                        help='TCP Congestion Control Algorithm (e.g., reno, cubic, bbr, etc.)')
    parser.add_argument('--loss', type=float, default=0.0,
                        help='Link loss percentage to apply on S2-S3 (e.g., 1.0 means 1%%)')
    parser.add_argument('--enable_all_links', action='store_true',
                        help='Enable all possible switch-to-switch links (S4-S1, S2-S4) in the topology.')
    args = parser.parse_args()

    # Build topology
    option = args.option.split('.')
    suboption = option[1] if len(option) > 1 else None
    option = option[0]
    topo = CustomTopo(enable_all_links=args.enable_all_links, option=option, suboption=suboption, loss=args.loss)
    net = Mininet(topo=topo, controller=OVSController, link=TCLink, autoSetMacs=True)
    net.start()

    # If we have a nonzero loss, configure it on the S2-S3 link:
    if args.loss > 0:
        link_s2_s3 = net.linksBetween(net.get('s2'), net.get('s3'))
        if link_s2_s3:
            # Typically there will be exactly 1 link in the list:
            link_obj = link_s2_s3[0]
            # We set loss on both interfaces:
            link_obj.intf1.config(loss=args.loss)
            link_obj.intf2.config(loss=args.loss)
            info(f"*** Configured {args.loss}% loss on link s2-s3\n")

    # Configure congestion control on all hosts
    configure_congestion_control(net, args.cc)

    # Dispatch to the requested experiment
    if args.option.lower() == 'a':
        run_option_a(net, args.cc)
    elif args.option.lower() == 'b':
        run_option_b(net, args.cc)
    elif args.option.lower().startswith('c'):
        run_option_c(net, args.cc, suboption)
    elif args.option.lower().startswith('d'):
        run_option_d(net, args.cc, suboption)
    else:
        info("*** Unknown option. Starting CLI for manual debugging...\n")

    # Drop into CLI for any extra commands or debugging
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()
