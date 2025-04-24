<p align="center"> 
  <img src="images/jntlb_logo.png" alt="jntlb_logo">
</p>
<h1 align="center"> Ergonomy package python </h1>
<h3 align="center"> A ROS2 package to compute RULA score for ergonomy </h3>  

</br>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

# Description:

The folder contains all the components to get the images from a realsense camera, to run ROS4HRI human pose estimation pipeline, visualize it on RViz and compute RULA index for human ergonomy estimation. The system is based on ROS2 Vulcanexus Jazzy by EProsima and the container is intended to work on Ubuntu since it is necessary to map the host usb ports on the container ports.  

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

# Hardware setup

1) #### Connect a realsense camera to the computer and verify if it is recognized by the operative system

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

# Installation

1) #### Disable the access control to xhost from any host, useful when using gui application inside docker:
    ```sh
    xhost +
    ```

2) #### Clone arise_ergo_dckr repo:
    ```sh
    git clone https://github.com/JOiiNT-LAB/arise_ergo_dckr.git
    cd arise_ergo_dckr
    git submodule update --init --recursive
    ```

4) #### Compile super_dckr docker image
    ```sh
    docker compose build
    ```

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

# Usage

1) #### Open a terminal in the container to interact with it:
    ```sh
    docker exec -it arise_ergo_dckr /bin/bash
    ```

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)


<!-- CONTRIBUTORS -->
<h2 id="contributors"> :scroll: Contributors</h2>
<p>
  :man: <b>Mario Corsanici</b> <br>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Email: <a>mario.corsanici@intellimech.it</a> <br>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; GitHub: <a href="https://github.com/mariocorsanici">@mario-corsanici</a> <br>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Linkedin: <a href="https://www.linkedin.com/in/mario-corsanici-0b7b1a138/">@mario-corsanici-linkedin</a> <br>
</p>