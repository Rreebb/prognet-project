#!/usr/bin/env bash
set -e -u -o pipefail

rm -rf work/measure
rm -rf work/log
mkdir -p work/measure

run(){
    local name=$1
    local network_params=$2
    echo "Running $name..."

    mkdir -p work/log
    # shellcheck disable=SC2086
    python network.py $network_params >>work/log/network.log 2>&1
    mv work/log work/measure/"$name"
}

run "no-vq"       "--variant no-vq"

run "ppvq-90-95"  "--variant per-port-vq --vq-committed-alpha 0.90 --vq-peak-alpha 0.95"
run "ppvq-95-98"  "--variant per-port-vq --vq-committed-alpha 0.95 --vq-peak-alpha 0.98"
run "ppvq-98-100" "--variant per-port-vq --vq-committed-alpha 0.98 --vq-peak-alpha 1.00"

run "pfvq-05-10"  "--variant per-flow-vq --vq-committed-alpha 0.05 --vq-peak-alpha 0.10"
run "pfvq-07-08"  "--variant per-flow-vq --vq-committed-alpha 0.07 --vq-peak-alpha 0.08"
run "pfvq-10-15"  "--variant per-flow-vq --vq-committed-alpha 0.10 --vq-peak-alpha 0.15"
