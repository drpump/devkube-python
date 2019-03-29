# objects for use in the creation of a cluster
import yaml
import os
import base64

NFS_PORTS = {'nfs': 2049, 'mountd':20048, 'rpcbind':111}
NFS_ROLE = 'nfs-server'
NFS_SERVICE = 'nfs-service'
NFS_PVC = 'nfs-pvc'
NFS_VOLUME = 'nfs-volume'
WEB_SERVER_ROLE = 'web-server'
WEB_SERVICE = 'web-service'
WEB_EXPORT=30080
SSHD_ROLE = 'sshd-server'
SSHD_SERVICE = 'sshd-service'
SSHD_EXPORT = 30022
PUBKEY_PATH = os.environ['HOME'] + '/.ssh/id_rsa.pub'

def encode_pubkey(path=PUBKEY_PATH):
  f = open(path, 'rb')
  return base64.standard_b64encode(f.read()).decode('ascii')

def pvc(name=NFS_PVC, storage='1Gi', klass='do-block-storage'):
  "Returns a kubernetes persistent volume claim object with  ReadWriteOnce mode."

  return {
    'api_version': 'v1',
    'kind': 'PersistentVolumeClaim',
    'metadata': {'name': name},
    'spec': {
      'accessModes': ['ReadWriteOnce'],
      'resources': {
        'requests': {
          'storage': storage
        }
      },
      'storageClassName': klass
    }
  }

def ports_obj(dict, type='port'):
  return list(map(lambda kv: {'name':kv[0], type:kv[1]}, dict.items()))

def deployment(name, role, containers, volumes):
  "Returns a base kubernetes deployment object without replication."

  return {
    'api_version': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': name},
    'spec': {
      'replicas': 1,
      'template': {
        'metadata': {
          'labels': {
            'app': name,
            'role': role
          }
        },
        'spec': {
          'containers': containers,
          'volumes': volumes
        }
      },
      'selector': {
        'matchLabels': {
          'role': role
        }
      }
    }
  }

def nfs_deployment(name, role, container, nfs_host, mount_point='/data', nfs_path='/'):
  "Deployment object for single-container deployments that mount  the specified nfs_path on the specified mount_point"

  container['volumeMounts'] = [{
    'name': NFS_VOLUME,
    'mountPath': mount_point
  }]
  volume = {
    'name': NFS_VOLUME,
    'nfs': {'server': nfs_host, 'path' : nfs_path}
  }
  return deployment(name, role, [container], [volume])

def web_server(nfs_host):
  name = 'nginx'
  mount_point = '/usr/share/nginx/html'
  container = {
                'name': name,
                'image': "nginx:latest",
                'ports': [{'name': 'web', 'containerPort': 80}]
              }
  return(nfs_deployment(name, WEB_SERVER_ROLE, container, nfs_host, mount_point=mount_point))

def alpine_server(nfs_host):
  name = 'alpine'
  container = {
    'name': name,
    'image': 'markeijsermans/debug:alpine',
    'command': ['sleep', '9999999']
  }
  return(nfs_deployment(name, 'alpine-role', container, nfs_host, mount_point='/mnt/nfs'))

def ssh_pubkey(pubkey=encode_pubkey()):
  "Secrets object containing public key for rsa_id, requires rsa public key for authorised user encoded as base64"
  return {
    'api_version': 'v1',
    'kind': 'Secret',
    'metadata': {
      'name': 'sshkey'
    },
    'type': 'Opaque',
    'data': {
      'authorizedkeys': pubkey
    }
  }

def ssh_server(nfs_host):
  name = 'sshd'
  container = {
    'name': name,
    'image': 'kubernetesio/sshd-jumpserver',
    'ports': [{'containerPort': 22}],
    'securityContext': {
      'privileged': True
    },
    'env': [{
      'name': 'PUBLIC_KEY',
      'valueFrom': {
        'secretKeyRef': {
          'name': 'sshkey',
          'key': 'authorizedkeys'
        }
      }
    }]
  }
  return(nfs_deployment(name, SSHD_ROLE, container, nfs_host, mount_point='/mnt/nfs'))

def nfs_server(name='nfs', pvc=NFS_PVC, role=NFS_ROLE, ports=NFS_PORTS):
  "Deployment object for an NFS server. The role name is used for subsequent matching in a service specification."

  container = {
                'name': name,
                'image': 'janeczku/nfs-ganesha:latest',
                'ports': ports_obj(ports, 'containerPort'),
                'volumeMounts': [
                  {'name': 'nfs-volume', 'mountPath': '/data/nfs'}
                ],
                'securityContext': {
                  'privileged': True
                }
              }
  volume = {
             'name': 'nfs-volume',
             'persistentVolumeClaim': {
               'claimName': pvc
             }
           }
  return deployment(name, role, [container], [volume])

def service(name, spec, namespace):
  return {
    'api_version': 'v1',
    'kind': 'Service',
    'metadata': {
      'name': name,
      'namespace': namespace
    },
    'spec': spec
  }

def exposed_service(name, match_role, port_name, port, nodeport, namespace):
  "Service object for server listining on port, exposing on nodeport"
  spec = {
    'type': 'NodePort',
    'ports': [{
      'name': port_name,
      'port': port,
      'nodePort': nodeport,
    }],
    'selector': {
        'role': match_role
    }
  }
  return service(name, spec, namespace)

def web_service(match_role=WEB_SERVER_ROLE, namespace='default'):
  return exposed_service(WEB_SERVICE, match_role, 'http', 80, WEB_EXPORT, namespace)

def ssh_service(match_role=SSHD_ROLE, namespace='default'):
  return exposed_service(SSHD_SERVICE, match_role, 'ssh', 22, SSHD_EXPORT, namespace)

def nfs_service(match_role=NFS_ROLE, namespace='default'):
  spec = {
    'type': 'ClusterIP',
    'ports': ports_obj(NFS_PORTS),
    'selector': {
      'role': match_role
    },
    'clusterIP': 'None'
  }
  return service(NFS_SERVICE, spec, namespace)

#file = open('yaml/nfs-service.yml', 'r')
#yml = yaml.safe_load(file.read())
