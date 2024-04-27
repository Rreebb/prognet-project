#include "types.p4"

struct metadata {}

control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {

    action set_egress_port_and_mac(portId_t egress_port, macAddr_t dst_mac) {
        standard_metadata.egress_spec = egress_port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dst_mac;
        log_msg("Egress port set to {} and dst MAC to {}", {egress_port, dst_mac});
    }

    table l3_forward {
        key = { hdr.ipv4.dstAddr: exact; }
        actions = { set_egress_port_and_mac; }
        size = 256;
    }

    apply {
        if (hdr.ipv4.isValid()) {
            log_msg("Received IPv4: ingress={}; ttl={}; protocol={}; ecn={}; {}.{}.{}.{} -> {}.{}.{}.{}",
                    {standard_metadata.ingress_port, hdr.ipv4.ttl, hdr.ipv4.protocol, hdr.ipv4.ecn,
                    SLICE_IPV4_ADDRESS(hdr.ipv4.srcAddr), SLICE_IPV4_ADDRESS(hdr.ipv4.dstAddr)});
            if (!hdr.tcp.isValid() && !hdr.udp.isValid()) { log_msg("WARN: packet is neither TCP nor UDP"); }
        } else if (hdr.ethernet.etherType == ETHER_TYPE_IPV6) { //We sometimes receive IPv6 packets for some reason
            log_msg("Received IPv6; ingress={}; dropping", {standard_metadata.ingress_port});
            mark_to_drop(standard_metadata);
            return;
        } else { //We are unable to forward non-IPv4 Ethernet packets
            log_msg("ERROR: ether type {}; ingress={}; ethernet-src={}; ethernet-dst={}; dropping",
                    {hdr.ethernet.etherType, standard_metadata.ingress_port,
                    hdr.ethernet.srcAddr, hdr.ethernet.dstAddr});
            mark_to_drop(standard_metadata);
            return;
        }

        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        if (hdr.ipv4.ttl == 0) {
            log_msg("ERROR: TTL expired for destination {}", {SLICE_IPV4_ADDRESS(hdr.ipv4.dstAddr)});
            mark_to_drop(standard_metadata);
            return;
        }

        if (l3_forward.apply().miss) {
            log_msg("FAIL: L3 forward table miss for destination {}", {SLICE_IPV4_ADDRESS(hdr.ipv4.dstAddr)});
            mark_to_drop(standard_metadata);
            return;
        }
    }
}

control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        log_msg("Egress data: timestamp={}; egress_port={}; flow_id=0; vq_id=0; dequeue_timedelta={}",
                {standard_metadata.egress_global_timestamp, standard_metadata.egress_port,
                standard_metadata.deq_timedelta});
    }
}

#include "controls.p4"
