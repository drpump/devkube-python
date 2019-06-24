# Kubernetes from iOS using Python

This repository contains code to create a Kubernetes cluster from iOS using Python scripts on an iPad. The eventual goal is to be able to use an iPad as an end-user device for development of applications running in a cloud-hosted kubernetes cluster.

For an article describing how it is built and used, see http://drpump.github.io/devkube-part2/.

## Prerequisites:

* [iSH](https://ish.app) or an equivalent linux/OS X command line
* git command line installed
* Python3 (on iSH, `apk add python-dev`)
* Public cert for your ssh key in `~/.ssh/id_rsa.pub`
* The python `requests` module (`pip3 install requests`)
* A Digital Ocean account and API token

## Fire it up
```
  $ git clone git@github.com:drpump/devkube-python
  $ cd devkube-python
  $ export DO_TOKEN=<my_token>
  $ python3 docluster.py   ### takes a while to create the cluster
  ...
  $ source cluster.env     ### load the cert and URL for cluster
  $ python3 -i exec.py
  ...
  >>> pk.deploy_nfs()
  Waiting for nfs startup ...
  Waiting for nfs startup ...
  nfs running in cluster on 10.244.0.218
  >>> pk.deploy_ssh()
  ssh accessible on port 30022 on IPs ['165.22.128.219', '165.22.128.246']
  >>> pk.deploy_web()
  web server accessible at http://165.22.128.219:30080
  >>> ^D
  $ ssh -p 30022 root@<your_node_ip>
  ...
  [root@sshd-012345678-9abcd]# cat > /mnt/nfs/index.html
  Hello from your kubernetes cluster
  ^D
  # 
```

Then navigate to the URL printed by `pk.deploy_web()` above to see the result.

If you are using a Linux or OS X machine, you can also use Visual Studio Code for [remote development](https://code.visualstudio.com/docs/remote/ssh) via ssh in this cluster. 
