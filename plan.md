# Per-flow Virtual Queues (Project 9)

Team members:

- Rebeka Kámán
- Gergely Sárközi

## Task

### Description

- Virtual Queue
  - have a smaller service rate than the real port
  - Emulated by token/leaky buckets – see meters in P4
- One physical queue with service rate $R$
  - Virtual queues with service rate $R \times alpha$, $alpha \in (0,1)$
  - Virtual queue for each active flow
    - Flow identification – tables, or hash
  - If per-flow VQ is full, we drop the packet

### Provided references

- [How to Build a Virtual Queue from Two Leaky Buckets (and why one is not enough)](https://www.bobbriscoe.net/projects/ipe2eqos/pcn/vq2lb/vq2lb_tr.pdf)
  - The memo explains why certain markers are not sufficient when building virtual queues
    - Leaky bucket (or token bucket): only supports what is called excess-traffic-marking (see [RFC 5670](https://datatracker.ietf.org/doc/html/rfc5670))
	- [Single rate three color marker](https://datatracker.ietf.org/doc/html/rfc2697): the two buckets used by the algorithm are emptied in the wrong order
  - The paper claims that the goal is to implement threshold-marking (see [RFC 5670](https://datatracker.ietf.org/doc/html/rfc5670))
	- The memo proposes a way to build such a marker by combining two leaky buckets
  - The authors do not mention [two rate three color markers](https://datatracker.ietf.org/doc/html/rfc2698), despite it, to the best of our knowledge and understanding, being exactly what the authors built by combining two leaky buckets
    - Two rate three color markers are [supported by P4](https://staging.p4.org/p4-spec/p4runtime/v1.3.0/P4Runtime-Spec.html#sec-meterentry-directmeterentry)
  - The paper assumes a single virtual queue is used for each egress port, while we want to use a virtual queue for each flow-egress port pair
- [The Native AQM for L4S Traffic](https://www.bobbriscoe.net/projects/latency/l4saqm_tr.pdf)
  - The memo explores how and why virtual queues could be (or should be) added to the native L4S AQM algorithm
  - The paper assumes a single virtual queue is used for each egress port, while we want to use a virtual queue for each flow-egress port pair
  - The author claims that (non-per-flow) virtual queues should usually closely mimic the real queue: an $alpha$ value of $\sim 98\%$ is a good choice for them

## Goal summary

The goal is to implement per-flow virtual queues with threshold-marking support using two rate three color markers:

- [ECN](https://datatracker.ietf.org/doc/html/rfc3168) will be used to mark packets exceeding the committed information rate
- Packets exceeding the peak information rate will be dropped

The individual flows will be distinguished based on the hash of their [5-tuple](https://nordvpn.com/cybersecurity/glossary/5-tuple/).
In case of a hash collision, two or more flows will end up sharing the same virtual queue, therefore they may experience reduced bandwidth.

The task and the linked memos do not specify what $alpha$ value to use and whether it should be a static value (e.g. hardcoded) or a dynamic value (that changes based on e.g. flow count).
We have been unable to find any previous work that offers satisfactory guidance in this matter.

## Implementation

The implementation will use the [BMv2 simple switch target](https://github.com/p4lang/behavioral-model/blob/main/docs/simple_switch.md) to be run via [p4-utils](https://github.com/nsg-ethz/p4-utils).

### Data plane

- The solution will be based on P4 source code implementing IPv4 routing
- Virtual queues will be implemented via two rate three color markers, which in turn will be implemented using P4 `meter` externs
- Each flow gets its own virtual queue for each egress port
  - A `meter` extern is actually an array of two rate three color markers: it has a size and can be indexed
  - The indexes are `bit<32>` values, and they will be the composition (bitwise concatenation) of the following:
    - Egress port id (`bit<9> egress_spec`); we will assume that the switch has at most 16 egress ports
    - Hash of the flow identifier (5-tuple); we can freely determine how many bits this should span, but decreasing the bit width increases the chances of hash collisions occurring
- We use composition instead of hashing because we believe that hash collisions shouldn't happen between distinct egress ports
- Packets that aren't dropped by the IPv4 routing algorithm will be marked by the two rate three color marker
  - Green packets will be queued normally
  - Yellow packets will be queued, but their ECN bits will be set to show that there is congestion
  - Red packets will not be queued: they will be dropped
- If enough flows transmit at rates just below the virtual queue rates, then no virtual queue will detect congestion, but the switch's queue will still get filled up
  - By default, this results in packets being dropped that don't fit in the queue, without taking the size of the packet's virtual queue into account
  - Future work can explore solutions to this problem, e.g. at the very least introducing the use of ECN in this scenario as well

### Control plane

The control plane is responsible for configuring the bandwidth limits:

- The switch's queue depth and queue rate must be set
- `meter` externs' rates and burst sizes must be set based on the switch's limits
  - If the switch's queue rate is $R$, then the meters' rates are $R \times alpha$, where $0 < alpha < 1$
  - An appropriate $alpha$ value must be determined

In future work it may be possible to use a dynamic $alpha$ value that is based on e.g. the flow count.
The control plane would need to periodically retrieve a flow count estimate and reconfigure the data plane `meter` externs accordingly.
It is unclear whether such a reconfiguration would erase the previous state of the `meter` externs.
Such an erasure would have negative consequences, as the length of the virtual queues would essentially be set to zero whenever the $alpha$ value is adjusted.

## Evaluation

- We will run simulations containing a mix of small and large flows, examining the flow completion times and suffered delays
  - Flow completion times can be visualized using boxplots
  - Queue delays can be visualized over time or via [CDFs](https://en.wikipedia.org/wiki/Cumulative_distribution_function)
- We will compare the results with different $alpha$ values being used
- We will compare the following cases:
  - Virtual queues being used
  - Virtual queues not being used (the switch only executes regular IPv4 routing)
  - Single virtual queue being used (instead of a separate one being used for each flow)

The topology used for simulations will contain a few hosts connected by a single switch.
This small topology is sufficient to test both the per-flow and per-port nature of the virtual queues.

### Traffic generation

The `iperf` utility command is capable of transmitting TCP packets at a specified rate and is therefore sufficient for our traffic generation needs.
Lacking better ideas, we will run multiple `iperf` sessions parallel to each other to be able to generate flows with both lower and higher transmission rates.

The machine running the simulation should support ECN for its TCP streams (e.g. by supporting DCTCP).
If we are unable to get ECN to work, we will set the two rates of the two rate three color marker to the same value.
That way no packets will get marked yellow, but will instead be either green (simply enqueued) or red (dropped).

### Extracting relevant data

The flow completion times and the queue delays experienced by the different flows will be retrieved from the switch logs:
we will log the current time, egress port, flow id hash, and dequeue timedelta in the egress pipeline of the data plane.

If the this data extraction method proves insufficient, we can try parsing the PCAP files generated during simulations to retrieve latency information and flow completion times.
The [Scapy](https://scapy.net/) Python library supports the parsing of PCAP files through e.g. `PcapReader`.

## Alternatives (noted, but not planned)

- Some P4 targets don't support two rate three color markers according to [Virtual Queues for P4: A Poor Man’s Programmable Traffic Manager](https://ieeexplore.ieee.org/abstract/document/9420725)
  - An implementation could be provided that relies on combining two single rate three color markers to support such targets
- Instead of using ECN, RED AQM could be used for the virtual queues
  - The [EWMA](https://en.wikipedia.org/wiki/Exponential_smoothing) of the queue length would have to be calculated and stored in a register array (containing a separate average for each flow-egress port pair)
    - These registers eliminate the need for P4 `meter` externs, but the logic used for indexing them can be reused
	- The average would have to be calculated in the egress pipeline, but read in the ingress pipeline, which might not be allowed by some P4 targets
  - The drop probability could be linear (when the average is between two thresholds), which can be implemented using the random extern (without requiring a match-action table)
