import json
import os
import random
import socket
import subprocess

import geopy.distance
import matplotlib.pyplot as plt
import requests

# from https://www.latlong.net/place/purdue-university-in-west-lafayette-34294.html
PURDUE_COORDS = (40.423710, -86.921242)

OUTPUT_DIR = "output"


class Host:

    def __init__(self, host, count):
        self.host = host

        self.ok = self.ping(count) and self.calculate_dist()
        if self.ok:
            print(
                f"pinged {self.host} dist: {self.dist_km} rtt min {self.rtt_min} max {self.rtt_max} avg {self.rtt_avg}")

    def ping(self, count):
        cmd = ["ping", "-c", str(count), "-i", "0.1", self.host]
        out = subprocess.run(cmd, capture_output=True, text=True)

        if out.returncode != 0:
            err = out.stderr.strip() or out.stdout.strip()
            print(f"\ncouldn't ping {self.host} : {err}\n")

            return False

        lines = out.stdout.splitlines()

        # e.g. round-trip min/avg/max/stddev = 212.948/213.369/214.287/0.444 ms
        stat_line = lines[-1]
        stat_list = list(map(float, stat_line.split()[3].split("/")))

        self.rtt_min = stat_list[0]
        self.rtt_avg = stat_list[1]
        self.rtt_max = stat_list[2]

        return True

    def calculate_dist(self):
        self.ip = socket.gethostbyname(self.host)
        res = requests.get(f"http://ip-api.com/json/{self.ip}")

        if res.status_code != 200:
            print(f"bad response for {self.host} with status code {res.status_code}")
            return False

        res_json = res.json()

        if res_json["status"] != "success":
            print(f"bad response for {self.host}")
            print(res_json)
            return False

        host_coords = (res_json["lat"], res_json["lon"])
        self.dist_km = geopy.distance.geodesic(PURDUE_COORDS, host_coords).km

        return True

    def traceroute(self, hops, probes, wait):
        # set max hops probes and waitime
        cmd = ["traceroute", "-I", "-n", "-m", str(hops), "-q", str(probes), "-w", str(wait), self.host]

        # worst timeout everything probe on every hop times out
        timeout = hops * probes * wait + 5
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"traceroute to {self.host} timed out")
            return False

        if out.returncode != 0:
            print(f"couldn't traceroute {self.host} : {out.stderr}")
            return False

        self.hops = []
        self.reached = False

        for line in out.stdout.splitlines():
            parsed = line.split()

            if not parsed or not parsed[0].isdigit():
                continue

            hop_num = int(parsed[0])

            # parse out times
            times = [float(time) for time, next in zip(parsed, parsed[1:]) if next == "ms"]

            if not times:
                continue

            self.hops.append((hop_num, sum(times) / len(times)))

            if self.ip in parsed:
                self.reached = True

        print(f"traced {self.host}: {len(self.hops)} hops, reached={self.reached}")
        return len(self.hops) > 0


def plot_hop_latency_breakdown(traced_hosts):
    """Plot estimated per-hop latency for each traced destination."""
    fig, ax = plt.subplots()

    for host_index, host in enumerate(traced_hosts):
        previous_hop = 0
        previous_rtt = 0
        bar_bottom = 0

        for hop_number, rtt in host.hops:
            # A gap in hop numbers represents one or more non-responsive hops.
            hop_label = (f"Hop {hop_number}" if hop_number == previous_hop + 1
                         else f"Hops {previous_hop + 1}-{hop_number}")
            hop_latency = max(0, rtt - previous_rtt)

            ax.bar(host_index, hop_latency, bottom=bar_bottom,
                   color=plt.cm.tab20((hop_number - 1) % 20),
                   edgecolor="black", linewidth=0.4)

            if hop_latency >= 2:
                ax.text(host_index, bar_bottom + hop_latency / 2, hop_label,
                        ha="center", va="center", fontsize=6)

            bar_bottom += hop_latency
            previous_hop = hop_number
            previous_rtt = rtt

    ax.set_xticks(range(len(traced_hosts)))
    ax.set_xticklabels([host.host for host in traced_hosts], rotation=20,
                       ha="right")
    ax.set_xlabel("Destination IP")
    ax.set_ylabel("Estimated latency (ms)")
    ax.set_title("Per-hop Latency Breakdown")
    fig.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/hop_latency_breakdown.pdf")
    plt.close(fig)


os.makedirs(OUTPUT_DIR, exist_ok=True)

with open("listed_iperf3_servers.json", "r") as f:
    servers_json = json.load(f)

hosts = []

for server in servers_json:
    host = Host(server["IP/HOST"], 5)

    if host.ok:
        hosts.append(host)

traced = []
host_pool = hosts[:]
random.shuffle(host_pool)  # select randomly

for host in host_pool:
    if len(traced) >= 5:
        break

    if host.traceroute(hops=30, probes=3, wait=1) and host.reached:
        traced.append(host)

print([h.host for h in traced])

distance = [host.dist_km for host in hosts]
rtt_min = [host.rtt_min for host in hosts]
rtt_max = [host.rtt_max for host in hosts]

hop_num = [h.hops[-1][0] for h in traced]
rtts = [h.rtt_avg for h in traced]

plt.scatter(distance, rtt_min, label='RTT min', color='tab:blue', s=15)
plt.scatter(distance, rtt_max, label='RTT max', color='tab:red', s=15)

plt.xlabel('Distance (km)')
plt.ylabel('RTT (ms)')
plt.title('Distance vs RTT')
plt.legend()
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/distance-vs-rtt.png')
plt.close()

plt.figure()

plt.scatter(hop_num, rtts, label='RTT avg', color='tab:green', s=15)
plt.xlabel('Hop count')
plt.ylabel('RTT (ms)')
plt.title('Hop count vs RTT')
plt.legend()
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/hop-count-vs-rtt.png')
plt.close()

plot_hop_latency_breakdown(traced)
