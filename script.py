import json
import socket
import subprocess

import geopy.distance
import matplotlib.pyplot as plt
import requests

# from https://www.latlong.net/place/purdue-university-in-west-lafayette-34294.html
PURDUE_COORDS = (40.423710, -86.921242)


class Host:

    def __init__(self, host, count):
        self.host = host

        self.ok = self.ping(count) and self.calculate_dist()
        if self.ok:
            print(f"pinged {self.host} dist: {self.dist_km} rtt min {self.rtt_min} max {self.rtt_max} avg {self.rtt_avg}")

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
        ip = socket.gethostbyname(self.host)
        res = requests.get(f"http://ip-api.com/json/{ip}")

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
    cmd = ["traceroute", "-n", "-m", str(hops), "-q", str(probes), "-w", str(wait), self.host]

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

    # TODO: parse handeling and prolly more err checks


with open("listed_iperf3_servers.json", "r") as f:
    servers_json = json.load(f)

hosts = []

for server in servers_json:
    host = Host(server["IP/HOST"], 5)

    if host.ok:
        hosts.append(host)

distance = [host.dist_km for host in hosts]
rtt_min = [host.rtt_min for host in hosts]
rtt_max = [host.rtt_max for host in hosts]

plt.scatter(distance, rtt_min, label='RTT min', color='tab:blue', s=15)
plt.scatter(distance, rtt_max, label='RTT max', color='tab:red', s=15)

plt.xlabel('Distance (km)')
plt.ylabel('RTT (ms)')
plt.title('Distance vs RTT')
plt.legend()
plt.tight_layout()
plt.savefig('output.png')
