from collections import Counter
from enum import Enum
from typing import Dict

import pandas as pd


class FlowSize(Enum):
    SMALL = 1
    LARGE = 2


def classify_data(data: pd.DataFrame, flow_size_threshold: int, debug: bool = False) -> Dict[int, FlowSize]:
    data_group_sum = data[["flow_id", "packet_length"]].groupby(
        "flow_id").sum().rename(columns={"packet_length": "sum(packet_length)"})
    ret = dict()

    if debug:
        print(data_group_sum)
        
    for flowId, row in data_group_sum.iterrows():
        ret[flowId] = FlowSize.LARGE if row["sum(packet_length)"] > flow_size_threshold else FlowSize.SMALL

    for flow_size in FlowSize:
        print(f"Number of {flow_size.name.lower()} flows:",
              Counter(ret.values())[flow_size])

    return ret
