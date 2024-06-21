import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict

import pandas as pd
from matplotlib import pyplot as plt

from plotter.classifier import classify_ingress_port
from plotter.constants import IPERF_CLIENT_HOST_COUNT, LOGS_DROP_LENGTH_SECONDS, FlowType, IPERF_CONNECTION_COUNT
from plotter.parser import SwitchLogParser
from plotter.plotter import plot_flow_type_vs_queue_delay_cdf, plot_flow_type_vs_sum_packet_length_boxplot


def generate_plots(name_to_data: Dict[str, pd.DataFrame], plot_dir: Path) -> None:
    plot_flow_type_vs_sum_packet_length_boxplot(name_to_data, plot_dir)
    plot_flow_type_vs_queue_delay_cdf(name_to_data, plot_dir)


def load_data(switch_log_path: Path) -> pd.DataFrame:
    data: pd.DataFrame = SwitchLogParser.parse_caching(switch_log_path)

    # Drop the backward packets (e.g. TCP ACKs): take only packets that are outbound to an iperf server
    data = data[data.egress_port > IPERF_CLIENT_HOST_COUNT]

    # Consider the timestamp of the first log entry as the epoch time
    start_time = data.at[0, 'timestamp']
    data['timestamp'] -= start_time

    # Drop the first few seconds, the Mininet warmup phase
    data = data[data.timestamp >= LOGS_DROP_LENGTH_SECONDS * 1_000_000]

    # Drop the smallest flows: they are iperf meta flows, and they would be outliers in the graphs
    flow_lengths = data[["flow_id", "packet_length"]].groupby("flow_id").sum()
    flow_lengths = flow_lengths.rename(columns={"packet_length": "flow_length"})
    flow_lengths.sort_values("flow_length", ascending=True, inplace=True)
    to_drop_flows = flow_lengths.head(IPERF_CONNECTION_COUNT).index
    data = data[~data.flow_id.isin(to_drop_flows)]

    # Consider the timestamp of the first log entry as the epoch time
    # Yes, do this again: we dropped the first few seconds, so the start time has changed
    data.reset_index(inplace=True)  # Make the first row be at index 0
    start_time = data.at[0, 'timestamp']
    data['timestamp'] -= start_time

    return data


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('--measure-dir', type=Path, required=True)
    parser.add_argument('--plot-dir', type=Path, required=True)
    parser.add_argument('--open-plots', action='store_true')
    args = parser.parse_args()

    # Load some args into intermediate variables to add type hints
    args_measure_dir: Path = args.measure_dir
    args_plot_dir: Path = args.plot_dir

    if not args_measure_dir.exists():
        raise FileNotFoundError(f'Cannot find the directory: {args_measure_dir}')

    # The names of the individual measurements (e.g. different switch variants, different alpha values)
    names = [folder.name for folder in args_measure_dir.iterdir() if folder.is_dir()]
    names.sort()  # Sort the names to ensure the order is consistent
    print(f'Found the following measurements: {", ".join(names)}')
    if len(names) == 0:
        raise ValueError('No measurements have been found')

    print('Notes regarding the raw data:')
    print('  Time unit: microseconds')
    print('  Packet length unit: bytes')
    print('  Flow types: ' + ", ".join([f'{flow_type.value}={flow_type.name.lower()}' for flow_type in FlowType]))
    print()

    # Load the measurements
    name_to_data: Dict[str, pd.DataFrame] = dict()
    for name in names:
        print(f"Loading measurement: {name}")
        data: pd.DataFrame = load_data(args_measure_dir / name / 'p4s.s1.log')
        print(f'  Count of log entries: {data.shape[0]}')

        data = classify_ingress_port(data)
        data_flows = data[['flow_id', 'flow_type']].drop_duplicates()  # Flow to flow_type mapping
        for flow_type in FlowType:
            # noinspection PyUnresolvedReferences
            print(f"  Number of {flow_type.name.lower()} flows: {(data_flows.flow_type == flow_type.value).sum()}")

        name_to_data[name] = data
        print(f'  First few classified log entries:')
        print(data.head())
        print()

    os.makedirs(args_plot_dir, exist_ok=True)
    generate_plots(name_to_data, args_plot_dir)

    if args.open_plots:
        plt.show()


if __name__ == '__main__':
    main()
