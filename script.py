import subprocess #lib for running bash cmds in python
import csv 
import platform #used to find out os
import re #regex lib for parsing ping output
import urllib.request #used to get public ip address

#csv format
#IP/HOST,PORT,GB/S,CONTINENT,COUNTRY,SITE,PROVIDER


#return a list of ip servers from csv file
def load_csv(csv_path = "listed_iperf3_servers.csv"):
    hosts = []
    with open(csv_path, newline = "", encoding = "utf-8") as f:
        reader = csv.DictReader(f) #first row is header makes dict keyed by header names
        for row in reader: 
            host = row["IP/HOST"].strip() #column that holds IP
            if not host:
                continue #skips unneeded items
            hosts.append({
                "host": host,
                "country": row.get("COUNTRY", ""),
                "site": row.get("SITE", ""),
                "provider": row.get("PROVIDER", "")
            })
    return hosts



#host = ip
#count = how many echo requests to send (4 default on windows)
def ping(host, count = 4):
    flag = "-c" #flag for linux/mac
    if platform.system() == "Windows":
        flag = "-n"
    out = subprocess.run(["ping", flag, str(count), host], capture_output=True, text=True)
    return out.stdout #parse this output for min/avg/max rtt


def parse_rtt(output):
    #pull all time = xx ms from output
    #match to 'time=23.4ms', 'time=40ms', 'time<1ms' for any os 
    #instead of reading the summary which is different just sum up the times and calc ourselves
    times = [float(t) for t in re.findall(r"time[=<]\s*([\d.]+)\s*ms", output)]
    if not times: 
        return None
    return {
        "min": min(times),
        "avg": sum(times) / len(times),
        "max": max(times),
        "count": len(times)
    }

#combo func
def ping_and_parse(host, count=4):
    output = ping(host, count)
    stats = parse_rtt(output)
    if stats is None:
        return {"host": host, "responsive": False}
    return {"host": host, "responsive": True, **stats}


#main loop 
for server in load_csv():
    result = ping_and_parse(server["host"])
    print(result)