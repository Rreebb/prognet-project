import base64
import hashlib
import os.path
import re
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd


class SwitchLogParser:
    @staticmethod
    def parse_caching(path: Path) -> pd.DataFrame:
        # Cache the parsed file, but add a hash to the filename to be able to detect changes
        # Detecting changes is not actually necessary anymore: we usually delete the caches when we gather new logs
        sha1 = hashlib.sha1(path.read_bytes()).digest()
        b64 = base64.b64encode(sha1).decode().replace('/', '-')
        parsed_path = path.with_suffix('.parsed.' + b64)

        if os.path.exists(parsed_path):
            with open(parsed_path, 'r') as f:
                # print('Loading cached switch log file...')
                data = pd.read_csv(f)
                # print('Switch log file loaded')
                return data
        else:
            # print('Parsing switch log file...')
            data = SwitchLogParser.parse(path)
            data.to_csv(parsed_path, index=False)
            # print('Switch log file parsed and cached')
            return data

    @staticmethod
    def parse(path: Path) -> pd.DataFrame:
        columns = ['timestamp', 'ingress_port', 'egress_port', 'flow_id', 'vq_id', 'dequeue_timedelta', 'packet_length']
        data = pd.DataFrame(np.empty((0, len(columns)), dtype=np.int64), columns=columns)
        with open(path, 'r') as f:
            for line in f:
                row = SwitchLogParser._parse_line(line)
                if row is not None:
                    data_row_array = np.array(row, dtype=np.int64).reshape((1, len(columns)))
                    data_row_frame = pd.DataFrame(data_row_array, columns=data.columns)
                    data = pd.concat([data, data_row_frame], ignore_index=True)
        return data

    @staticmethod
    def _parse_line(line: str) -> Optional[List[int]]:
        line = line.rstrip()
        match = re.fullmatch(r'\[[^]]+] \[bmv2] \[I] \[[^]]+] Egress data:'
                             r' timestamp=(\d+); ingress_port=(\d+); egress_port=(\d+); '
                             r'flow_id=(\d+); vq_id=(\d+); dequeue_timedelta=(\d+); packet_length=(\d+)', line)
        return list(map(int, match.groups())) if match else None
