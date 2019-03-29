import requests
import os
from pprint import pprint
from time import sleep
import objects

# assume we already have created the cluster and DO_CLUSTER_URL is defined
VERSION = 'api_version'
CORE_VERSION = 'v1'
URL = os.environ['DO_CLUSTER_URL']

def make_session():
  sess = requests.Session()
  sess.cert = ['./cert.pem','./key.pem']
  sess.verify = 'ca.pem'
  return sess

def kind_of(object):
  return object['kind'].lower() + 's'

def name_of(object):
  return object['metadata']['name']

def version_of(object):
  return object[VERSION]

def api_path(version=CORE_VERSION):
  if version == CORE_VERSION:
    api = 'api/v1'
  else:
    api = 'apis/' + version
  return '{base}/{api}'.format(base=URL, api=api)

def kind_path(kind, version=CORE_VERSION, namespace='default'):
  return '{base}/namespaces/{ns}/{kind}'.format(
    base = api_path(version),
    ns = namespace,
    kind = kind)

def named_path(kind, name, version=CORE_VERSION, namespace='default'):
  return '{kind_path}/{name}'.format(
    kind_path = kind_path(kind, version, namespace),
    name = name)

def object_kind_path(object, namespace='default'):
  return kind_path(kind_of(object), version_of(object), namespace)

def object_path(object, namespace='default'):
  return(named_path(kind_of(object), name_of(object), version_of(object), namespace))

def object_status_path(object, namespace='default'):
  return object_path(object) + '/status'

def create_object(sess, object, namespace='default', show=False):
   if show:
     pprint(sess.get(api_path(version_of(object))).json())
   return sess.post(object_kind_path(object, namespace), json=object).json()

def delete_object(sess, object, namespace='default'):
  return(sess.delete(object_path(object, namespace)).json())

def deploy_nfs(sess):
  create_object(sess, objects.pvc())
  create_object(sess, objects.nfs_server())
  create_object(sess, objects.nfs_service())
  sleep(5) # give it a little time to start
  print('nfs running in cluster on {ip}'.format(ip=nfs_ip(sess)))

def nfs_ip(sess):
  nfs_ep = sess.get(named_path('endpoints', objects.NFS_SERVICE)).json()
  return nfs_ep['subsets'][0]['addresses'][0]['ip']

def deploy_ssh(sess):
  create_object(sess, objects.ssh_pubkey())
  create_object(sess, objects.ssh_server())
  create_object(sess, objects.ssh_service(nfs_ip(sess)))
  print('ssh accessible on port {port} on IPs {ips}'.format(
    port=objects.SSHD_EXPORT,
    ips=get_node_ips(sess)))

def deploy_web(sess):
  create_object(sess, objects.web_server(nfs_ip(sess)))
  create_object(sess, objects.web_service())
  print('web server accessible at http://{ip}:{port}'.format(
    port=objects.WEB_EXPORT,
    ip=get_node_ips(sess)[0]))

def get_nodes(sess):
  return sess.get(api_path(CORE_VERSION)+'/nodes').json()['items']

def get_node_ip(node):
  addr = next(addr for addr in node['status']['addresses']
                    if addr['type'] == 'ExternalIP')
  return addr['address']

def get_node_ips(sess):
  return list(map(lambda node: get_node_ip(node), get_nodes(sess)))

def ppo(sess, object):
  pprint(sess.get(object_status_path(object)).json())

def ppk(sess, kind, version='v1'):
  pprint(sess.get(kind_path(kind, version)).json())
