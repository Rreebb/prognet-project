import os
from typing import Literal

from p4utils.mininetlib.network_API import NetworkAPI
from p4utils.utils.compiler import P4C

# Which P4 source code variant to use
SWITCH_VARIANT: Literal['base', 'pfvq'] = 'pfvq'

net = NetworkAPI()

# Topology definition
net.addP4Switch('s1')
for i in [1, 2, 3]:
    net.addHost(f'h{i}')
    net.addLink('s1', f'h{i}')
# TODO add latency to links

# Host configuration
net.l3()

# Switch configuration
compiler_dir = f'./work/switch_{SWITCH_VARIANT}'
os.makedirs(compiler_dir, exist_ok=True)
net.setCompiler(P4C, outdir=compiler_dir)
net.setP4SourceAll(f'./switch/switch_{SWITCH_VARIANT}.p4')

# Initialize the switches via the controller
net.setTopologyFile(f'./work/topology.json')
os.makedirs(os.path.dirname(net.topoFile), exist_ok=True)
# The topology file will be created on network startup, before the controller is executed
controller_out_file = './work/log/controller.log'
net.execScript(f'python3 -m controller --topology-path {net.topoFile}'
               f' --queue-rate-pps 500'  # 500 pps * 1500 bytes/packet = 6.0 Mbps
               f' --queue-depth-packets 15'  # 1000 ms / 500 pps * 30 packets = 60.0 ms
               f' --vq-committed-alpha 0.2'
               f' --vq-peak-alpha 0.3',
               out_file=controller_out_file)
os.makedirs(os.path.dirname(controller_out_file), exist_ok=True)

# Logging, capturing configuration
net.setLogLevel('info')
net.enableLogAll(log_dir='./work/log')
net.enablePcapDumpAll(pcap_dir='./work/pcap')

# Execution
net.enableCli()
net.startNetwork()

# TODO look into addTask for automation: https://nsg-ethz.github.io/p4-utils/advanced_usage.html#task-scheduler

# If necessary: run traffic for 5s
# Wait for 5s
# Run the real traffic
# In the evaluation: drop the first 9 seconds of traffic
