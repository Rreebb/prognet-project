import os
import time
from argparse import ArgumentParser
from typing import Literal, List, Tuple, Dict

from p4utils.mininetlib.network_API import NetworkAPI
from p4utils.utils.compiler import P4C

parser = ArgumentParser()
parser.add_argument("--variant", choices=['no-vq', 'per-port-vq', 'per-flow-vq'], default='per-flow-vq',
                    help="Which P4 source code variant to use")
parser.add_argument("--cli", action="store_true",
                    help="Start the Mininet CLI after setting up the network")
parser.add_argument("--vq-committed-alpha", type=float, default=0.2,
                    help="The virtual queues' committed rate to use as a fraction of the switch's maximum rate (only used for pfvq variant)")
parser.add_argument("--vq-peak-alpha", type=float, default=0.3,
                    help="The virtual queues' peak rate to use as a fraction of the switch's maximum rate (only used for pfvq variant)")
args = parser.parse_args()

switch_variant: Literal['no-vq', 'per-port-vq', 'per-flow-vq'] = args.variant

net = NetworkAPI()

# Topology definition
net.addP4Switch('s1')
for i in [1, 2, 3, 4]:
    net.addHost(f'h{i}')
    net.addLink('s1', f'h{i}')
net.setDelayAll(2)  # 2 ms link delay

# Host configuration
net.l3()

# Switch configuration
compiler_dir = f'./work/switch_{switch_variant}'
os.makedirs(compiler_dir, exist_ok=True)
net.setCompiler(P4C, outdir=compiler_dir, opts=f'--target bmv2 --arch v1model --std p4-16'
                                               f' -D VARIANT_{switch_variant.upper().replace("-", "_")}=1')
net.setP4SourceAll(f'./switch/switch.p4')

# Initialize the switches via the controller
net.setTopologyFile(f'./work/topology.json')
os.makedirs(os.path.dirname(net.topoFile), exist_ok=True)
# The topology file will be created on network startup, before the controller is executed
controller_out_file = './work/log/controller.log'
net.execScript(f'python3 -m controller --topology-path {net.topoFile}'
               f' --queue-rate-pps 500'  # 500 pps * 1500 bytes/packet = 6.0 Mbps
               f' --queue-depth-packets 30'  # 1000 ms / 500 pps * 30 packets = 60.0 ms
               f' --vq-committed-alpha {args.vq_committed_alpha}'
               f' --vq-peak-alpha {args.vq_peak_alpha}',
               out_file=controller_out_file)
os.makedirs(os.path.dirname(controller_out_file), exist_ok=True)

# Logging, capturing configuration
net.setLogLevel('info')
net.enableLogAll(log_dir='./work/log')
# net.enablePcapDumpAll(pcap_dir='./work/pcap')
net.disablePcapDumpAll()

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


def add_task_iperf_server(host_to: str, time_from: float, time_to: float) -> None:
    for flow_index, (rate, count) in enumerate(flows_rate_count):
        host_from = f'h{flow_index + 1}'
        iperf = f'iperf3 --server --port {port_min + flow_index}'
        cmd = f'bash -c "{iperf} > ./work/log/iperf-s_{host_from}-{host_to}_{rate}x{count}.log 2>&1"'
        net.addTask(host_to, cmd, time_from, time_to - time_from)


def add_task_iperf_client(host_to: str, time_from: float, time_to: float) -> None:
    duration = time_to - time_from
    ip = get_host_ip(host_to)
    for flow_index, (rate, count) in enumerate(flows_rate_count):
        host_from = f'h{flow_index + 1}'
        iperf = (f'iperf3 --client {ip} --port {port_min + flow_index} --bitrate {rate} --fq-rate {rate}'
                 f' --parallel {count} --time {duration} --version4 --set-mss 1460')
        log = f'./work/log/iperf-c_{host_from}-{host_to}_{time_from}s-{time_to}s_{rate}x{count}.log'
        cmd = f'bash -c "{iperf} > {log} 2>&1"'
        net.addTask(host_from, cmd, time_from, duration)


# Schedule traffic
# h1 and h2 are responsible for smalling small and large flows, respectively.
# Both h1 and h2 send to both h3 and h4: each iperf server receives both traffic types.
for h in ["h3", "h4"]:
    add_task_iperf_server(h, *task_from_to_sec['server'])
    add_task_iperf_client(h, *task_from_to_sec['warmup'])
    add_task_iperf_client(h, *task_from_to_sec['evaluation'])

# Execute automatic traffic simulation
net.disableCli()
net.startNetwork()
print("Waiting for the the simulation to finish...")
time.sleep(task_from_to_sec['server'][1] + 3)  # Few seconds grace period
net.stopNetwork()

# TODO drop the first N seconds of traffic during evaluation

# TODO check results with DCTCP disabled: does it really make a difference?
