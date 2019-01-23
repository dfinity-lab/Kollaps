# NEED
Decentralized container based network emulator

Clone this repo with:
```
$git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/NEED.git
```

This readme is a quick introduction to get NEED running, for further reference see the [NEED Wiki](https://github.com/miguelammatos/NEED/wiki)

## Pre-requisites
You need a machine running Linux with a recent version of Docker installed, and python 3.

Also this machine has to be part of a Docker Swarm.

To create a Swarm of 1 machine execute:
```
$docker swarm init
```

## Install instructions
```
$pip wheel --no-deps . .
$pip install need-1.1-py3-none-any.whl
```
Installing the python package will give you access to the NEEDdeploymentGenerator command to translate need topology descritions into Docker Swarm Compose files on your local machine.

You also need to build the need docker image, to do so execute on this folder:
```
$docker build --rm -t need:1.1 .
```

## How to use
Some simple experiment examples are available in the examples folder.

These experiments use images that are available in https://github.com/joaoneves792/NEED_Images

Before proceding you should build all the images in the folder "samples_need_1_1/" of the above repo.

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
$NEEDdeploymentGenerator topology5.xml > topology5.yaml
```

This experiment requires that a network named "test_overlay" exists.
To create it run:
```
docker network create --driver=overlay --subnet=10.1.0.0/24 test_overlay
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


