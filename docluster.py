import requests
import os
import yaml
import base64
import time

REGION='sfo2'
AUTH={'Authorization': 'Bearer ' + os.environ['DO_TOKEN']}
URL='https://api.digitalocean.com/v2/kubernetes/'

def cluster_info(id):
  return requests.get(
	  URL + "clusters/" + id,
	  headers=AUTH).json()['kubernetes_cluster']

def cluster_running(info):
  return info['status']['state'] == 'running'

def write_pem(bytes, filename):
  handle = open(filename, 'wb')
  handle.write(bytes)
  handle.close

# Retrieve the latest kubernetes version slug
info = requests.get(URL+'options', headers=AUTH)
version = info.json()['options']['versions'][0]['slug']
print('Using version ' + version)

# Define cluster and node pool parameters
devpool = {
	'name': 'devpool',
	'size': 's-2vcpu-4gb',
	'count': 2}

cluster = {
	'id': 'devkube 15Mar2019',
	'name': 'devkube',
	'region': REGION,
	'version': version,
	'node_pools': [devpool]}

# Create the cluster
cluster = requests.post(
	URL + 'clusters',
	headers=AUTH,
  json=cluster
).json()
id = cluster['kubernetes_cluster']['id']
#id = os.environ['DO_CLUSTER']

# Wait for cluster running
while (not cluster_running(cluster_info(id))):
  print('Still waiting ...')
  time.sleep(10)
print('Cluster running')

# Get certs and keys for cluster
conf_yaml = requests.get(
	URL + 'clusters/' + id + '/kubeconfig',
	headers=AUTH)

parsed_conf = yaml.safe_load(conf_yaml.text)
write_pem(base64.b64decode(
  parsed_conf['clusters'][0]['cluster']['certificate-authority-data']),
  'ca.pem')
cl_user = parsed_conf['users'][0]['user']
write_pem(base64.b64decode(cl_user['client-certificate-data']), 'cert.pem')
write_pem(base64.b64decode(cl_user['client-key-data']), 'key.pem')

info = cluster_info(id)
handle = open('cluster.env', 'w')
handle.write('export DO_CLUSTER_ID=' + info['id'] + '\n')
handle.write('export DO_CLUSTER_URL=' + info['endpoint'] + '\n')
print('Cluster ready, endpoint, certs and keys saved')
