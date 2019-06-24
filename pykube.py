import requests
import os
from pprint import pprint
from time import sleep
import objects

# assume we already have created the cluster and DO_CLUSTER_URL is defined
VERSION = 'api_version'
CORE_VERSION = 'v1'
URL = os.environ['DO_CLUSTER_URL']

# Helper methods for kubernetes API paths
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


class PyKube:
  """
    Class encapsulating a set of functions and state for interacting with a kubernetes cluster
  """
  
  # initializer creates a self.sess.on
  def __init__(self, cert_files=['./cert.pem','./key.pem'], ca='ca.pem'):
    self.sess = requests.Session()
    self.sess.cert = cert_files
    self.sess.verify = ca

  def create_object(self, object, namespace='default', show=False):
     if show:
       pprint(self.sess.get(api_path(version_of(object))).json())
     return self.sess.post(object_kind_path(object, namespace), json=object).json()

  def delete_object(self, object, namespace='default'):
    return(self.sess.delete(object_path(object, namespace)).json())

  def deploy_nfs(self):
    self.create_object(objects.pvc())
    self.create_object(objects.nfs_server())
    self.create_object(objects.nfs_service())
    ip = self.nfs_ip()
    while (not ip):
      print('Waiting for nfs startup ...')
      sleep(3)
      ip = self.nfs_ip()
    print('nfs running in cluster on {ip}'.format(ip=ip))
  
  def nfs_ip(self):
    nfs_ep = self.sess.get(named_path('endpoints', objects.NFS_SERVICE)).json()
    if 'subsets' in nfs_ep:
      return nfs_ep['subsets'][0]['addresses'][0]['ip']
    else:
      return None

  def deploy_ssh(self):
    self.create_object(objects.ssh_pubkey())
    self.create_object(objects.ssh_server(self.nfs_ip()))
    self.create_object(objects.ssh_service())
    print('ssh accessible on port {port} on IPs {ips}'.format(
      port=objects.SSHD_EXPORT,
      ips=self.get_node_ips()))

  def deploy_web(self):
    self.create_object(objects.web_server(self.nfs_ip()))
    self.create_object(objects.web_service())
    print('web server accessible at http://{ip}:{port}'.format(
      port=objects.WEB_EXPORT,
      ip=self.get_node_ips()[0]))

  def get_nodes(self):
    return self.sess.get(api_path(CORE_VERSION)+'/nodes').json()['items']

  def get_node_ip(self, node):
    addr = next(addr for addr in node['status']['addresses']
                      if addr['type'] == 'ExternalIP')
    return addr['address']

  def get_node_ips(self):
    return list(map(lambda node: self.get_node_ip(node), self.get_nodes()))

  def ppo(self, object):
    pprint(self.sess.get(object_status_path(object)).json())

  def ppk(self, kind, version='v1'):
    pprint(self.sess.get(kind_path(kind, version)).json())
