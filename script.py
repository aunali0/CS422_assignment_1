import geopy.distance
import matplotlib.pyplot as plt
import requests

import json
import subprocess
import platform

# from https://www.latlong.net/place/purdue-university-in-west-lafayette-34294.html
PURDUE_COORDS = (40.423710, -86.921242)

with open("listed_iperf3_servers.json", "r") as f:
    servers_json = json.load(f)

class Host:
    def __init__(self, host, count):
        self.host = host

        self.ok = self.ping(count)
        if self.ok:
            self.ok = self.calculate_dist()


    def ping(self, count):
        flag = "-c" #flag for linux/mac
        if platform.system() == "Windows":
            flag = "-n"

        out = subprocess.run(["ping", flag, str(count), "-i", "0.1", self.host], capture_output=True, text=True)

        if out.returncode != 0:
            print(f"couldn't ping {self.host} : {out.stderr}")
            return False

        lines = out.stdout.splitlines()

        # e.g. PING speed.mymanga.pro (102.215.35.132): 56 data bytes
        ip_line = lines[0]
        self.ip = ip_line.split()[2][1:-2]

        # e.g. round-trip min/avg/max/stddev = 212.948/213.369/214.287/0.444 ms
        stat_str = lines[-1]

        stat_list = list(map(float, stat_str.split()[3].split("/")))
        self.rtt_min = stat_list[0]
        self.rtt_avg = stat_list[1]
        self.rtt_max = stat_list[2]
        
        return True


    def calculate_dist(self):
        self.dist = None

        resp = requests.get(f"http://ip-api.com/json/{self.ip}")
        if resp.status_code != 200:
            print("bad response for {self.host} status code {resp.status_code}")
            return False

        resp_json = resp.json()
        if resp_json["status"] != "success":
            print("bad response for {self.host}")
            print(resp_json)
            return False


        host_coords = (resp_json["lat"], resp_json["lon"])
        self.dist_km = geopy.distance.geodesic(PURDUE_COORDS, host_coords).km
        print("dist is ", self.dist_km)

        return True

hosts = []

for server in servers_json:
    host = Host(server["IP/HOST"], 5)
    if host.ok:
        hosts.append(host)

distance = [host.dist_km for host in hosts]
rtt_min  = [host.rtt_min for host in hosts]
rtt_max  = [host.rtt_max for host in hosts]

plt.scatter(distance, rtt_min, label='RTT min', color='tab:blue', s=15)
plt.scatter(distance, rtt_max, label='RTT max', color='tab:red', s=15)

plt.xlabel('Distance')
plt.ylabel('RTT')
plt.title('Distance vs RTT')
plt.legend()
plt.tight_layout()
plt.savefig('output.png')

