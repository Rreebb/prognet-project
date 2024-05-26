import pandas as pd
import matplotlib.pyplot as plt

from plotter.classifier import FlowType


def plot_flow_type_vs_sum_packet_length_boxplot(data: pd.DataFrame, plot_dir: str, debug: bool = False) -> None:
    data_group_sum = data[["flow_id", "packet_length", "flow_type"]]
    data_group_sum = data_group_sum.groupby(["flow_id", "flow_type"], as_index=False).sum()
    data_group_sum = data_group_sum.rename(columns={"packet_length": "sum(packet_length)"})

    x, labels = [], []
    for flow_type in FlowType:
        x.append(data_group_sum[data_group_sum.flow_type == flow_type.value]["sum(packet_length)"])
        labels.append(flow_type.name.lower())
    
    fig, ax = plt.subplots()
    ax.boxplot(x, labels=labels)

    fig.show()
    fig.savefig(f"{plot_dir}/sum_packet_length_boxplot.pdf")
