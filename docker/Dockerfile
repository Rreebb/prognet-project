FROM ubuntu:20.04

WORKDIR /workspace

# Install Mininet, Python and related tools
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y dnsutils ifupdown iproute2 iptables iputils-ping tcpdump \
       net-tools curl iperf3 xterm x11-xserver-utils graphviz libnanomsg-dev mininet \
       python3 python-is-python3 python3-pip python3-tk \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir graphviz matplotlib networkx mininet psutil ipaddr scapy nnpy pandas

# Install bmv2 and p4c
# Source: https://github.com/p4lang/p4c?tab=readme-ov-file#ubuntu
RUN . /etc/lsb-release \
    && echo "deb http://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${DISTRIB_RELEASE}/ /" | tee /etc/apt/sources.list.d/home:p4lang.list \
    && curl -fsSL https://download.opensuse.org/repositories/home:p4lang/xUbuntu_${DISTRIB_RELEASE}/Release.key | gpg --dearmor | tee /etc/apt/trusted.gpg.d/home_p4lang.gpg > /dev/null \
    && apt-get update \
    && apt-get install -y p4lang-p4c p4lang-bmv2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install p4-utils and its dependencies
RUN apt-get update \
    && apt-get install -y git bridge-utils sudo \
    && git clone https://github.com/nsg-ethz/p4-utils.git \
    && cd p4-utils \
    && ./install.sh \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && curl https://raw.githubusercontent.com/mininet/mininet/master/mininet/log.py > /usr/local/lib/python3.8/dist-packages/mininet/log.py

# Enable DCTCP
RUN echo "net.ipv4.tcp_congestion_control=dctcp" >> /etc/sysctl.conf && sysctl -p

WORKDIR /workspace/mnt

CMD ["/bin/bash"]
