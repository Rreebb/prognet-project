import pandas as pd
import matplotlib.pyplot as plt

from plotter.classifier import FlowType


def plot_flow_type_vs_sum_packet_length_boxplot(data: pd.DataFrame, plot_dir: str) -> None:
    data_group_sum = data[["flow_id", "packet_length", "flow_type"]]
    data_group_sum = data_group_sum.groupby(["flow_id", "flow_type"], as_index=False).sum()
    data_group_sum = data_group_sum.rename(columns={"packet_length": "sum(packet_length)"})

    fig, axes = plt.subplots(1, len(FlowType))
    for ax, flow_type in zip(axes, FlowType):
        ax.boxplot(data_group_sum[data_group_sum.flow_type == flow_type.value]["sum(packet_length)"])
        ax.set_title(flow_type.name.lower())

    fig.suptitle("Sum of Flow Packet Lengths for Different Flow Types")
    axes[0].set_ylabel("Flow Size [bytes]")
    fig.savefig(f"{plot_dir}/sum_packet_length_boxplot.pdf")


def plot_flow_type_vs_queue_delay_cdf(data: pd.DataFrame, plot_dir: str) -> None:
    fig, axes = plt.subplots(1, len(FlowType), sharey=True)
    
    for ax, flow_type in zip(axes, FlowType):
        ax.ecdf(data[data.flow_type == flow_type.value]["dequeue_timedelta"])
        ax.set_title(flow_type.name.lower())

    fig.suptitle("Queue Delay CDF for Different Flow Types")
    axes[0].set_ylabel("CDF")
    for ax in axes:
        ax.set_xlabel("Queue Delay [$\\mu s$]")
    fig.savefig(f"{plot_dir}/queue_delay_cdf.pdf")
