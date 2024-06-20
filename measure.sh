#!/usr/bin/env bash
set -e -u -o pipefail

rm -rf work/measure/

run(){
    local name=$1
    local network_params=$2
    echo "Running $name"
    # shellcheck disable=SC2086
    python network.py $network_params >work/log/network.log 2>&1
    mv -v work/log work/measure/"$name"
}

run "no-vq"       "--variant no-vq"
run "ppvq-95-98"  "--variant per-port-vq --vq-committed-alpha 0.95 --vq-peak-alpha 0.98"
run "ppvq-98-100" "--variant per-port-vq --vq-committed-alpha 0.98 --vq-peak-alpha 1.00"
run "pfvq-10-20"  "--variant per-flow-vq --vq-committed-alpha 0.10 --vq-peak-alpha 0.20"
run "pfvq-20-30"  "--variant per-flow-vq --vq-committed-alpha 0.20 --vq-peak-alpha 0.30"
run "pfvq-30-40"  "--variant per-flow-vq --vq-committed-alpha 0.30 --vq-peak-alpha 0.40"
