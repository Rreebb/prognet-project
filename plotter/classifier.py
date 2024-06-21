import numpy as np
import pandas as pd

from plotter.constants import FlowType


def classify_flow_size(data: pd.DataFrame, flow_size_threshold: int) -> pd.DataFrame:
    """Classify flows based on the sum of the packets' length."""
    data_group_sum = data[["flow_id", "packet_length"]].groupby(
        "flow_id").sum().rename(columns={"packet_length": "sum(packet_length)"})

    data_group_sum["sum(packet_length)"] = np.where(data_group_sum["sum(packet_length)"] <= flow_size_threshold,
                                                    FlowType.SMALL.value, FlowType.LARGE.value)
    flow_to_type = data_group_sum.rename(columns={"sum(packet_length)": "flow_type"})
    data = data.join(flow_to_type, on='flow_id')

    return data


def classify_ingress_port(data: pd.DataFrame) -> pd.DataFrame:
    """
    Classify flows based on their packets' ingress port: port=1 -> FlowType[1], etc.
    Because of flow ID collisions, two log entries with the same flow ID might have different flow types.
    """
    data["flow_type"] = np.where(data["ingress_port"] == 1, FlowType.SMALL.value, FlowType.LARGE.value)
    return data
