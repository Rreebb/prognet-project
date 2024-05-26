from enum import Enum

import numpy as np
import pandas as pd


class FlowType(Enum):
    SMALL = 1
    LARGE = 2


def classify_data(data: pd.DataFrame, flow_size_threshold: int, debug: bool = False) -> pd.DataFrame:
    data_group_sum = data[["flow_id", "packet_length"]].groupby(
        "flow_id").sum().rename(columns={"packet_length": "sum(packet_length)"})

    if debug:
        print("Value of data group sum:")
        print(data_group_sum.reset_index())

    data_group_sum["sum(packet_length)"] = np.where(data_group_sum["sum(packet_length)"] <= flow_size_threshold,
                                                    FlowType.SMALL.value, FlowType.LARGE.value)
    flow_to_type = data_group_sum.rename(columns={"sum(packet_length)": "flow_type"})
    data = data.join(flow_to_type, on='flow_id')

    for flow_type in FlowType:
        print(f"Number of {flow_type.name.lower()} flows: {(flow_to_type.flow_type == flow_type.value).sum()}")

    return data
