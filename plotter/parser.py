import base64
import hashlib
import os.path
import pathlib
import re
from typing import Optional, List

import numpy as np
import pandas as pd


class SwitchLogParser:
    @staticmethod
    def parse_caching(path: str) -> pd.DataFrame:
        sha1 = hashlib.sha1(pathlib.Path(path).read_bytes()).digest()
        b64 = base64.b64encode(sha1).decode().replace('/', '-')
        parsed_path = path + '.parsed.' + b64
        if os.path.exists(parsed_path):
            with open(parsed_path, 'r') as f:
                print('Loading cached switch log file...')
                data = pd.read_csv(f)
                print('Switch log file loaded')
                return data
        else:
            print('Parsing switch log file...')
            data = SwitchLogParser.parse(path)
            data.to_csv(parsed_path)
            print('Switch log file parsed and cached')
            return data

    @staticmethod
    def parse(path: str) -> pd.DataFrame:
        columns = ['timestamp', 'egress_port', 'flow_id', 'vq_id', 'dequeue_timedelta']
        data = pd.DataFrame(np.empty((0, len(columns)), dtype=np.int64), columns=columns)
        with open(path, 'r') as f:
            for line in f:
                row = SwitchLogParser._parse_line(line)
                if row is not None:
                    data_row = pd.DataFrame(np.array(row, dtype=np.int64).reshape((1, 5)), columns=data.columns)
                    data = pd.concat([data, data_row], ignore_index=True)
        return data

    @staticmethod
    def _parse_line(line: str) -> Optional[List[int]]:
        line = line.rstrip()
        match = re.fullmatch(r'\[[^]]+] \[bmv2] \[I] \[[^]]+] Egress data: timestamp=(\d+); egress_port=(\d+); '
                             r'flow_id=(\d+); vq_id=(\d+); dequeue_timedelta=(\d+)', line)
        return list(map(int, match.groups())) if match else None
