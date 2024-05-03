import os
import time
from argparse import ArgumentParser
from builtins import str
from typing import Literal, List, Tuple, Dict

from p4utils.mininetlib.network_API import NetworkAPI
from p4utils.utils.compiler import P4C

parser = ArgumentParser()
parser.add_argument("--variant", choices=['base', 'pfvq'], default='pfvq',
                    help="Which P4 source code variant to use")
parser.add_argument("--cli", action="store_true",
                    help="Start the Mininet CLI after setting up the network")
args = parser.parse_args()

switch_variant: Literal['base', 'pfvq'] = args.variant

net = NetworkAPI()

# Topology definition
net.addP4Switch('s1')
for i in [1, 2, 3]:
    net.addHost(f'h{i}')
    net.addLink('s1', f'h{i}')
net.setDelayAll(2)

# Host configuration
net.l3()

# Switch configuration
compiler_dir = f'./work/switch_{switch_variant}'
os.makedirs(compiler_dir, exist_ok=True)
net.setCompiler(P4C, outdir=compiler_dir)
net.setP4SourceAll(f'./switch/switch_{switch_variant}.p4')

# Initialize the switches via the controller
net.setTopologyFile(f'./work/topology.json')
os.makedirs(os.path.dirname(net.topoFile), exist_ok=True)
# The topology file will be created on network startup, before the controller is executed
controller_out_file = './work/log/controller.log'
net.execScript(f'python3 -m controller --topology-path {net.topoFile}'
               f' --queue-rate-pps 500'  # 500 pps * 1500 bytes/packet = 6.0 Mbps
               f' --queue-depth-packets 30'  # 1000 ms / 500 pps * 30 packets = 60.0 ms
               f' --vq-committed-alpha 0.2'
               f' --vq-peak-alpha 0.3',
               out_file=controller_out_file)
os.makedirs(os.path.dirname(controller_out_file), exist_ok=True)

# Logging, capturing configuration
net.setLogLevel('info')
net.enableLogAll(log_dir='./work/log')
net.enablePcapDumpAll(pcap_dir='./work/pcap')

# Start Mininet interactively
if args.cli:
    net.enableCli()
    net.startNetwork()
    exit(0)

# Traffic constants
port_min = 5201
flows_rate_count: List[Tuple[str, int]] = [('400K', 10), ('2M', 3)]  # 0.4 Mbps * 10 + 2 Mbps * 3 = 10 Mbps (per port)
task_from_to_sec: Dict[str, Tuple[int, int]] = {
    'server': (1, 31),
    'warmup': (2, 5),
    'evaluation': (10, 30)
}


def get_host_ip(host: str) -> str:
    sw_and_host = filter(lambda x: x[0] == host or x[1] == host, net.links()).__next__()
    sw = sw_and_host[0] if sw_and_host[1] == host else sw_and_host[1]
    ip_with_mask = net.getLink(host, sw)[0]['params2']['ip']
    return ip_with_mask.split('/')[0]


def add_task_iperf_server(host_from: str, host_to: str, time_from: float, time_to: float) -> None:
    for port_offset, (rate, count) in enumerate(flows_rate_count):
        iperf = f'iperf3 --server --port {port_min + port_offset}'
        cmd = f'bash -c "{iperf} > ./work/log/iperf-s_{host_from}-{host_to}_{rate}x{count}.log 2>&1"'
        net.addTask(host_to, cmd, time_from, time_to - time_from)


def add_task_iperf_client(host_from: str, host_to: str, time_from: float, time_to: float) -> None:
    duration = time_to - time_from
    ip = get_host_ip(host_to)
    for port_offset, (rate, count) in enumerate(flows_rate_count):
        port = port_min + port_offset
        iperf = (f'iperf3 --client {ip} --port {port} --bitrate {rate} --fq-rate {rate} --parallel {count}'
                 f' --time {duration} --version4 --set-mss 1460')
        log = f'./work/log/iperf-c_{host_from}-{host_to}_{time_from}s-{time_to}s_{rate}x{count}.log'
        cmd = f'bash -c "{iperf} > {log} 2>&1"'
        net.addTask(host_from, cmd, time_from, duration)


# Schedule traffic
for h in ["h2", "h3"]:
    add_task_iperf_server("h1", h, *task_from_to_sec['server'])
    add_task_iperf_client("h1", h, *task_from_to_sec['warmup'])
    add_task_iperf_client("h1", h, *task_from_to_sec['evaluation'])

# Execute automatic traffic simulation
net.disableCli()
net.startNetwork()
print("Waiting for the the simulation to finish...")
time.sleep(task_from_to_sec['server'][1] + 3)  # Few seconds grace period
net.stopNetwork()

# TODO drop the first N seconds of traffic during evaluation
