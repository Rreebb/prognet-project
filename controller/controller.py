import logging
from typing import List, Dict

from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI
from p4utils.utils.topology import NetworkGraph

from controller.data import Config


class Controller:
    def __init__(self, topology: NetworkGraph, config: Config) -> None:
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._logger.info("Initializing controller...")
        self._topology: NetworkGraph = topology
        self._config: Config = config
        self._host_names: List[str] = sorted(self._topology.get_hosts().keys())
        self._switch_names: List[str] = sorted(self._topology.get_p4switches().keys())
        self._controllers: Dict[str, SimpleSwitchThriftAPI] = \
            {sw: SimpleSwitchThriftAPI(self._topology.get_thrift_port(sw)) for sw in self._switch_names}

    def initialize_switches(self) -> None:
        self._logger.info("Initializing switches...")
        for sw, controller in self._controllers.items():
            self._logger.info(f"Initializing switch {sw}...")
            controller.reset_state()
            self._set_switch_queue_limits(sw)
            self._set_virtual_queue_limits(sw)
            self._fill_l3_tables(sw)
        self._logger.info("Switches have been initialized")

    def _set_switch_queue_limits(self, sw: str) -> None:
        controller = self._controllers[sw]
        controller.set_queue_rate(self._config.switch_queue_rate_pps)
        controller.set_queue_depth(self._config.switch_queue_depth_packets)

    def _set_virtual_queue_limits(self, sw: str) -> None:
        controller = self._controllers[sw]
        meter_name = "MyIngress.vq_packets"

        # Virtual queues might not exist, it depends on which P4 program is running
        if meter_name in controller.get_meter_arrays():
            self._logger.info("Virtual queue found in switch, configuring...")
        else:
            self._logger.info("Virtual queue not found in switch, skipping...")
            return

        max_rate, max_depth = self._config.switch_queue_rate_pps, self._config.switch_queue_depth_packets
        alpha_c, alpha_p = self._config.virtual_queue_committed_alpha, self._config.virtual_queue_peak_alpha
        cir, cburst, pir, pburst = max_rate * alpha_c, max_depth * alpha_c, max_rate * alpha_p, max_depth * alpha_p
        sec_to_micro = 1 / 1_000_000  # Documentation incorrectly states that rates are in unit/second
        rates = [(cir * sec_to_micro, int(cburst)), (pir * sec_to_micro, int(pburst))]  # burst sizes must be integers
        self._logger.debug(f"VQ rates: [(cir, cburst), (pir, pburst)] = {rates}")
        controller.meter_array_set_rates(meter_name, rates)

    def _fill_l3_tables(self, sw: str) -> None:
        """Fill in the next hop from the switch towards each host. This could be improved by longest prefix matching."""
        for dst in self._host_names:
            path: List[str] = list(self._topology.get_shortest_paths_between_nodes(sw, dst)[0])
            self._logger.debug(f'Registering first hop of path: {" -> ".join(path)}')

            dst_ip = self._topology.get_host_ip(dst)
            egress_port = self._topology.node_to_node_port_num(path[0], path[1])
            next_mac = self._topology.node_to_node_mac(path[1], path[0])
            self._controllers[sw].table_add("l3_forward", "set_egress_port_and_mac",
                                            [dst_ip], [str(egress_port), next_mac])
