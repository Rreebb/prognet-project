from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from plotter.constants import FlowType, MAX_QUEUE_DELAY_MS


def plot_flow_type_vs_sum_packet_length_boxplot(name_to_data: Dict[str, pd.DataFrame], plot_dir: Path) -> None:
    name_to_data_group_sum = dict()
    for name, data in name_to_data.items():
        data_group_sum = data[["flow_id", "packet_length", "flow_type"]]
        data_group_sum = data_group_sum.groupby(["flow_id", "flow_type"], as_index=False).sum()
        data_group_sum = data_group_sum.rename(columns={"packet_length": "sum(packet_length)"})
        name_to_data_group_sum[name] = data_group_sum

    fig, axes = plt.subplots(1, len(FlowType))
    fig.suptitle("Sum of Flow Packet Lengths for Different Flow Types")
    axes[0].set_ylabel("Flow Size [KBs]")

    for ax, flow_type in zip(axes, FlowType):
        ax: Axes = ax  # Type hint
        ax.set_title(f"'{flow_type.name.capitalize()}' Flows")

        x, labels = [], []
        for name, data_group_sum in name_to_data_group_sum.items():
            labels.append(name)
            values = data_group_sum[data_group_sum.flow_type == flow_type.value]["sum(packet_length)"]
            values /= 1_000  # Convert bytes to kilobytes
            x.append(values)
        ax.boxplot(x, labels=labels)

    fig.savefig(f"{plot_dir}/sum_packet_length_boxplot.pdf")


def plot_flow_type_vs_queue_delay_cdf(name_to_data: Dict[str, pd.DataFrame], plot_dir: Path) -> None:
    fig, axes = plt.subplots(1, len(FlowType), sharey='all', sharex='all')
    fig.suptitle("Queue Delay CDF for Different Flow Types")
    axes[0].set_ylabel("Cumulative Distribution")
    axes[0].set_xlabel("Queue Delay [ms]")
    axes[0].set_xlim(-3, MAX_QUEUE_DELAY_MS + 3)  # padding: +-3

    # TODO different line styles for different P4 source variants, different colors for different alpha values

    for ax, flow_type in zip(axes, FlowType):
        ax: Axes = ax  # Type hint
        axes[0].set_title(f"'{flow_type.name.capitalize()}' Flows")

        for name, data in name_to_data.items():
            # Axes.ecdf is not available for Python 3.8 (which Ubuntu 20.04 uses)
            values = data[data.flow_type == flow_type.value]["dequeue_timedelta"]
            values /= 1_000  # Convert microseconds to milliseconds
            if len(values) == 0:
                print(f'WARNING: No data in {name} for the {flow_type.name} flow type. Skipping.')
                continue

            # Handles duplicates and sorts the data
            x, counts = np.unique(values, return_counts=True)
            cumulative_sum = np.cumsum(counts)
            y = cumulative_sum / cumulative_sum[-1]
            # Forces a jump at smallest data value
            x = np.insert(x, 0, x[0])
            y = np.insert(y, 0, 0.0)
            # Steps-post ensures that the jumps occur at the right place
            ax.plot(x, y, drawstyle='steps-post', label=name)

    fig.legend(loc='lower right')
    fig.tight_layout()
    fig.savefig(f"{plot_dir}/queue_delay_cdf.pdf")
