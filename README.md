# NEED
Decentralized container based network emulator

## New

This version is now using the images from NEED_Images/samples_need_2_0/.

Comunication is done through Aeron.

Every process is started from the God conatiner and the ones on the same machine comunicate via shared memory. With other machines, via reliable UDP.

In this branch the structure for packets is: 

The host corresponding to the qlen should be identifiable by the 1st link in the list.
```
//  packet:
//      #flows                  uint8/uint16 (depending on # of hosts)
//      list_of_flows           list of flows described below
//
//      flow:
//			qlen                uint16
//          throughput          uint32
//          #links              uint8/uint16 (depending on # of hosts)
//          list_of_link_ids    list of uint8/uint16 (depending on # of hosts)
```




This readme is a quick introduction to get NEED running, for further reference see the [NEED Wiki](https://github.com/miguelammatos/NEED/wiki)

## Pre-requisites
You need a machine running Linux with a recent version of Docker installed, and python 3.

This machine has to be a manager of a Docker Swarm.
(it needs to be a manager so that the God container can attach itself to the test_network)

To create a Swarm of 1 machine execute:
```
$docker swarm init
```

## Install instructions


Clone this repo with:
```
$git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/NEED.git
```

Installing the python package will give you access to the NEEDdeploymentGenerator command to translate need topology descritions into Docker Swarm Compose files on your local machine.
```
$pip wheel --no-deps . .
$pip install need-2.0-py3-none-any.whl
```

You also need to build the need docker image, to do so execute on this folder:
```
$docker build --rm -t need:2.0 .
```

## How to use
Some simple experiment examples are available in the examples folder.

These experiments use images that are available in https://github.com/joaoneves792/NEED_Images

Before proceding you should build all the images in the folder "samples_need_2_0/" of the above repo.

To avoid changing the xml example files the images should be built with the following tags:

|folder|Tag|
|------|---|
|alpineclient|  warpenguin.no-ip.org/alpineclient:1.0 |
|alpineserver|  warpenguin.no-ip.org/alpineserver:1.0 |
|dashboard|     warpenguin.no-ip.org/dashboard:1.0 |
|logger|        warpenguin.no-ip.org/logger:1.0 |

to build each image cd into its respective folder and execute:
```
$docker build -t <Tag> .
```

Experiments are described as xml files that can be converted into Docker Swarm Compose files with the NEEDdeploymentGenerator command.

Example:
```
$NEEDdeploymentGenerator topology5.xml -s > topology5.yaml
```

This experiment requires the existence of an attachable network named "test_overlay".
To create it run:
```
docker network create --attachable --driver=overlay --subnet=10.1.0.0/24 test_overlay
```

This example uses the overlay driver, but ipvlan/macvlan networks are also supported.

Make sure to define a subnet that does not collide with other networks on your setup.


The experiment can then be deployed to the Swarm with:
```
$docker stack deploy -c topology5.yaml 5
```

(Where 5 is an arbitrary name for the stack you are deploying)

After the experiment is deployed, the dashboard should be accessible on http://127.0.0.1:8088

The dashboard was designed to work even if a conventional browser is not an option

You can use it with a terminal based browser like w3m or simply by issuing HTTP GET requests at http://127.0.0.1:8088/start
and http://127.0.0.1:8088/stop with a basic tool such as curl.

After the dashboard initializes you have to wait until all services report Ready.

Then you can start the experiment, this will launch the applications inside the containers.

Stopping an experiment will stop the applications and ensure a clean shutdown of need.

After stopping an experiment you can remove the containers with:
```
$docker stack rm 5
```

## Note
Removing the containers without cleanly stopping the experiment can potentially trigger a kernel memory corruption bug, leading to system instability!

If you have started an experiment (services report as "running" on the dashboard) allways stop it through the dashboard before removing the containers.




# NEED on Kubernetes

Since version 2.0, NEED experiments can also be run with Kubernetes as an orchestrator.

### Setup

Sources: https://serverfault.com/a/684792; https://gist.github.com/alexellis/fdbc90de7691a1b9edb545c17da2d975

First, disable swap on your system.

Find swap volumes with `cat /proc/swaps`

Then, turn off swap:

```
$sudo swapoff --a
```

Comment out any of the volumes found before in `/etc/fstab` and reboot your system.

Then, install Kubernetes:

```
$curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add - && \
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list && \
sudo apt-get update -q && \
sudo apt-get install -qy kubeadm
```

Do this on all nodes.

### The Kubernetes master node

Only on the master node, execute:

```
$sudo sysctl net.bridge.bridge-nf-call-iptables=1
$sudo kubeadm init --token-ttl=0
```

The `kubeadm init` command tells you to execute the following statements. Do it:

```
$mkdir -p $HOME/.kube && \
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config && \
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

It also gives you a join command like this: `sudo kubeadm join <IP>:<PORT> --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>`. Use this on the worker nodes to join the cluster.

Next (on the master again), install the Weavenet CNI plugin:

```
$kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')"
```

If you want to run pods on the master node, un-taint it:

```
$kubectl taint nodes --all node-role.kubernetes.io/master-
```

### Creating manifest files for NEED experiments

For instructions on how to install the NEED tools like the NEEDdeploymentGenerator, see above. To generate a Docker Swarm compose file, run:

```
$NEEDdeploymentGenerator topology5.xml -s > topology5.yaml
```

To generate a Kubernetes manifest file, however, run:

```
$NEEDdeploymentGenerator topology5.xml -k > topology5.yaml
```

Note that this must be run from the folder in which the `topology` file sits, or a parent directory.

### Running a NEED experiment on Kubernetes

Navigate to the folder where your generated manifest yaml sits, and execute:

```
$kubectl apply -f topology5.yaml
```

To access the dashboard, run `$kubectl get pods -o wide` and find the dashboard pod. Copy the IP address shown and open <IP>:8088 in your browser.

To remove all components fo the experiment, run:

```
$kubectl delete -f topology5.yaml
```
