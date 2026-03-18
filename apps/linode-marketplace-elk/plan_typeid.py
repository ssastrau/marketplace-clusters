#!/usr/bin/env python3

vars_file = "./group_vars/linode/vars"

def get_typeId(name):
    plan_types = {
        "Nanode 1GB": "g6-nanode-1",
        "Linode 2GB": "g6-standard-1",
        "Linode 4GB": "g6-standard-2",
        "Linode 8GB": "g6-standard-4",
        "Linode 16GB": "g6-standard-6",
        "Linode 32GB": "g6-standard-8",
        "Linode 64GB": "g6-standard-16",
        "Linode 96GB": "g6-standard-20",
        "Linode 128GB": "g6-standard-24",
        "Linode 192GB": "g6-standard-32",
        "Linode 24GB": "g7-highmem-1",
        "Linode 48GB": "g7-highmem-2",
        "Linode 90GB": "g7-highmem-4",
        "Linode 150GB": "g7-highmem-8",
        "Linode 300GB": "g7-highmem-16",
        "Dedicated 4GB": "g6-dedicated-2",
        "Dedicated 8GB": "g6-dedicated-4",
        "Dedicated 16GB": "g6-dedicated-8",
        "Dedicated 32GB": "g6-dedicated-16",
        "Dedicated 64GB": "g6-dedicated-32",
        "Dedicated 96GB": "g6-dedicated-48",
        "Dedicated 128GB": "g6-dedicated-50",
        "Dedicated 256GB": "g6-dedicated-56",
        "Dedicated 32GB + RTX6000 GPU x1": "g1-gpu-rtx6000-1",
        "Dedicated 64GB + RTX6000 GPU x2": "g1-gpu-rtx6000-2",
        "Dedicated 96GB + RTX6000 GPU x3": "g1-gpu-rtx6000-3",
        "Dedicated 128GB + RTX6000 GPU x4": "g1-gpu-rtx6000-4",
        "Premium 4GB": "g7-premium-2",
        "Premium 8GB": "g7-premium-4",
        "Premium 16GB": "g7-premium-8",
        "Premium 32GB": "g7-premium-16",
        "Premium 64GB": "g7-premium-32",
        "Premium 96GB": "g7-premium-48",
        "Premium 128GB": "g7-premium-50",
        "Premium 256GB": "g7-premium-56",
        "RTX4000 Ada x1 Small": "g2-gpu-rtx4000a1-s",
        "RTX4000 Ada x1 Medium": "g2-gpu-rtx4000a1-m",
        "RTX4000 Ada x1 Large": "g2-gpu-rtx4000a1-l",
        "RTX4000 Ada x1 X-Large": "g2-gpu-rtx4000a1-xl",
        "RTX4000 Ada x2 Small": "g2-gpu-rtx4000a2-s",
        "RTX4000 Ada x2 Medium": "g2-gpu-rtx4000a2-m",
        "RTX4000 Ada x2 Medium High Storage": "g2-gpu-rtx4000a2-hs",
        "RTX4000 Ada x4 Small": "g2-gpu-rtx4000a4-s",
        "RTX4000 Ada x4 Medium": "g2-gpu-rtx4000a4-m",
        "NETINT Quadra T1U x1 Small": "g1-accelerated-netint-vpu-t1u1-s",
        "NETINT Quadra T1U x1 Medium": "g1-accelerated-netint-vpu-t1u1-m",
        "NETINT Quadra T1U x2 Small": "g1-accelerated-netint-vpu-t1u2-s"
    }

    typeId = plan_types[name]
    return typeId

def update_cluster_type():
    with open(vars_file) as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if "cluster_type" in line:
            value = line.split(":")[1].strip().strip("'").strip('"')
            try:
                new_value = get_typeId(value)
                key = line.split(":")[0].strip()
                line = f"{key}: {new_value}\n"
                print(f"[info] found {key} with typeId {new_value}")
            except:
                print(f"[warn] found {key} but no '{value}' value")
        if line:
            new_lines.append(line)
        
    if new_lines:
        with open(vars_file, "w") as f:
            f.writelines(new_lines)
            print(f"[info] {vars_file} updated..")

# main
update_cluster_type()