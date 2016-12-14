#!/usr/bin/env python
import requests
import xmltodict
import json
import re
import datetime,pytz
from influxdb import InfluxDBClient
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

nsx_mgr = ['192.168.0.100','192.168.1.100','192.168.2.100']
nsx_user = 'admin'
nsx_password = 'password'
ifdb_host = 'localhost'
ifdb_port = 8086
ifdb_user = 'root'
ifdb_password = 'password'
ifdb_dbname = 'influxdb'

def get_edges(nsxm):
  edges = []
  response = requests.get( 'https://'+nsxm+'/api/4.0/edges', auth=(nsx_user,nsx_password), verify=False )
  root = xmltodict.parse(response.text)
  for edge in root["pagedEdgeList"]["edgePage"]["edgeSummary"]:
    if edge["edgeType"] == "gatewayServices":
      edges.append(edge["objectId"])
  return edges

def get_edge_ifstats(nsxm,target):
  response = requests.get( 'https://'+nsxm+'/api/4.0/edges/'+target+'/statistics/dashboard/interface?interval=1', auth=(nsx_user,nsx_password), verify=False )
  root = xmltodict.parse(response.text)
  data = root["dashboardStatistics"]["data"]
  vnicstats = []
  fields = {}
  for interface in data["interfaces"]:
    vnic = interface[0:7].replace("__","")
    if re.search('__in__pkt',interface):
      tag = 'inpkt'
    elif re.search('__in__byte',interface):
      tag = 'inbyte'
    elif re.search('__out__pkt',interface):
      tag = 'outpkt'
    elif re.search('__out__byte',interface):
      tag = 'outbyte'
    ifvalue = float(data["interfaces"][interface]["dashboardStatistic"][1]["value"])
    fields[tag]=ifvalue
    if len(fields) == 4:
      ts = float(data["interfaces"][interface]["dashboardStatistic"][1]["timestamp"])
      timestamp = datetime.datetime.fromtimestamp(ts, pytz.timezone('UTC')).isoformat()
      stats = {"measurement":nsxm,"tags":{"vnic":vnic,"edge_id":target},"fields":fields,"time":timestamp}
      vnicstats.append(stats)
      fields = {}
  return vnicstats

def main():
  for nsxm in nsx_mgr:
    edges = get_edges(nsxm)
    ifdbclient = InfluxDBClient(ifdb_host, ifdb_port, ifdb_user, ifdb_password, ifdb_dbname)
    for edge in edges:
      ifstats = get_edge_ifstats(nsxm,edge)
      ifdbclient.write_points(ifstats)
    
if __name__== '__main__':
  main()

