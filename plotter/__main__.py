import os
from argparse import ArgumentParser, FileType

import pandas as pd
from plotter.parser import SwitchLogParser
from matplotlib import pyplot as plt


def generate_plots(data: pd.DataFrame, plot_dir: str) -> None:
    pass


# TODO classify flows to flow types (based on flow sizes: small, large)


def load_data(switch_log_path: str) -> pd.DataFrame:
    data: pd.DataFrame = SwitchLogParser.parse_caching(switch_log_path)
    print(f'Count of log entries: {data.shape[0]}')

    # Consider the timestamp of the first log entry as the epoch time
    start_time = data.at[0, 'timestamp']
    data['timestamp'] = data['timestamp'] - start_time

    print(f'First few log entries: (time unit: microseconds)')
    print(data.head())
    return data


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('--switch-log-path', type=FileType(), required=True)
    parser.add_argument('--plot-dir', type=str, required=True)
    parser.add_argument('--open-plots', action='store_true')
    args = parser.parse_args()

    data = load_data(args.switch_log_path.name)

    if not os.path.exists(args.plot_dir):
        os.makedirs(args.plot_dir)

    generate_plots(data, args.plot_dir)

    if args.open_plots:
        plt.show()


if __name__ == '__main__':
    main()
