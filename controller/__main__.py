import json
import logging
import sys
import time
from argparse import ArgumentParser, FileType

import networkx
from p4utils.utils.topology import NetworkGraph

from controller.controller import Controller
from controller.data import Config


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
                        stream=sys.stdout)

    parser = ArgumentParser()
    parser.add_argument('--topology-path', type=FileType(), required=True)
    parser.add_argument("--queue-rate-pps", type=int, required=True)
    parser.add_argument("--queue-depth-packets", type=int, required=True)
    parser.add_argument("--vq-committed-alpha", type=float, required=True)
    parser.add_argument("--vq-peak-alpha", type=float, required=True)
    args = parser.parse_args()

    # We don't use p4utils.utils.helper.load_topo because it imports mininet logging, which screws up the logging module
    with args.topology_path as f:
        topology = NetworkGraph(networkx.node_link_graph(json.load(f)))

    config = Config(
        switch_queue_rate_pps=args.queue_rate_pps,
        switch_queue_depth_packets=args.queue_depth_packets,
        virtual_queue_committed_alpha=args.vq_committed_alpha,
        virtual_queue_peak_alpha=args.vq_peak_alpha,
    )
    controller = Controller(topology, config)
    controller.initialize_switches()

    logging.getLogger(__name__).info('Controller has finished; waiting until interrupted...')
    while True:
        time.sleep(999)


if __name__ == '__main__':
    main()
