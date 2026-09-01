import subprocess #lib for running bash cmds in python
import csv 
import platform #used to find out os

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


