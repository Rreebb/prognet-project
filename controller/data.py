from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    switch_queue_rate_pps: int
    switch_queue_depth_packets: int
    virtual_queue_committed_alpha: float
    virtual_queue_peak_alpha: float
