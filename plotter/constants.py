from enum import Enum


class FlowType(Enum):
    SMALL = 1
    LARGE = 2


# Switches have a fixed queue size and a fixed dequeue rate, therefore a maximum queue delay can be determined
MAX_QUEUE_DELAY_MS = 60

# This many hosts will be used to generate traffic, starting with h1 and switch port 1
IPERF_CLIENT_HOST_COUNT = len(FlowType)

# This many hosts will be used to receive traffic, hN and port indexes are continued from the client hosts
IPERF_SERVER_HOST_COUNT = 2

# How many iperf connections will be established in total
IPERF_CONNECTION_COUNT = IPERF_SERVER_HOST_COUNT * len(FlowType)

# How many seconds of log data should be dropped from the start of the logs (to drop the warmup phase)
LOGS_DROP_LENGTH_SECONDS = 6
