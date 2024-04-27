#include "types.p4"

#define SMALL_PORT_T_WIDTH 4
typedef bit<SMALL_PORT_T_WIDTH> small_port_t;
#define FLOW_ID_T_WIDTH 12
typedef bit<FLOW_ID_T_WIDTH> flow_id_t;
#define VQ_ID_T_WIDTH (SMALL_PORT_T_WIDTH + FLOW_ID_T_WIDTH)
typedef bit<VQ_ID_T_WIDTH> vq_id_t;

struct metadata {
    flow_id_t flow_id;
    vq_id_t vq_id;
}

control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {

    meter((bit<32>) (1 << VQ_ID_T_WIDTH), MeterType.packets) vq_packets;

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
        } else if (hdr.ethernet.etherType == ETHER_TYPE_IPV6) { //In case we receive IPv6 packets due to some bug
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

        if ((portId_t) ((small_port_t) standard_metadata.egress_spec) != standard_metadata.egress_spec) {
            log_msg("FAIL: Egress port is out of range: {}", {standard_metadata.egress_spec});
            return; //Packet will still be enqueued
        }

        hash(meta.flow_id, HashAlgorithm.crc32, (bit<1>) 0, {
            hdr.ipv4.srcAddr,
            hdr.ipv4.dstAddr,
            hdr.ipv4.protocol,
            hdr.tcp.isValid() ? hdr.tcp.srcPort : (hdr.udp.isValid() ? hdr.udp.srcPort : 0),
            hdr.tcp.isValid() ? hdr.tcp.dstPort : (hdr.udp.isValid() ? hdr.udp.dstPort : 0)
        }, (bit<32>) (1 << FLOW_ID_T_WIDTH));

        meta.vq_id = ((small_port_t) standard_metadata.egress_spec) ++ meta.flow_id;

        meter_color_t color = METER_INVALID;
        vq_packets.execute_meter((bit<32>) meta.vq_id, color);
        log_msg("Meter color of VQ={}: {}", {meta.vq_id, color});

        if (color == METER_GREEN) {
            //Do nothing: just let the packet be forwarded
        } else if (color == METER_YELLOW) {
            if (hdr.ipv4.ecn == 0) { log_msg("WARN: hosts don't support ECN"); }
            hdr.ipv4.ecn = 3; //Set ECN to 11
        } else if (color == METER_RED) {
            mark_to_drop(standard_metadata);
            return;
        } else {
            log_msg("ERROR: Unknown meter color={} for VQ={}", {color, meta.vq_id});
        }
    }
}

control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        log_msg("Egress data: timestamp={}; egress_port={}; flow_id={}; vq_id={}; dequeue_timedelta={}; packet_length={}",
                {standard_metadata.egress_global_timestamp, standard_metadata.egress_port,
                meta.flow_id, meta.vq_id, standard_metadata.deq_timedelta, standard_metadata.packet_length});
    }
}

#include "controls.p4"
