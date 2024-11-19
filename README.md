<p align="center"> 
  <img src="images/jntlb_logo.png" alt="jntlb_logo">
</p>
<h1 align="center">Superelectric docker package </h1>
<h3 align="center"> Superelectric repository for testing ROS2 communication with videostreaming  </h3>  

</br>


![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

# Prepare host system for the docker container

1) #### Add Docker's official GPG key:
    ```sh
    sudo apt-get update
    sudo apt-get install ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    ```

2) #### Add the repository to Apt sources:
    ```sh
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    ```
3) #### Install latest version
    ```sh
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```
4) #### Test the installation
    ```sh
    sudo docker run hello-world
    ```

2) #### Docker post-installation steps (suggested, not required)
    ```sh
    sudo groupadd docker    
    sudo usermod -aG docker $USER
    newgrp docker
    ```
4) #### Test post-installation procedure
    ```sh
    docker run hello-world
    ```
5) #### You don't need 'sudo' command anymore to use docker commands

# Compile the docker image and the resulting container

1) #### Disable the access control to xhost from any host, useful when using gui application inside docker:
    ```sh
    xhost +
    ```

2) #### Clone super_dckr repo:
    ```sh
    git clone https://github.com/JOiiNT-LAB/super_dckr.git
    cd super_dckr
    git submodule update --init --recursive
    ```

4) #### Compile super_dckr docker image
    ```sh
    docker compose build
    ```

5) #### Start the container in background:
    ```sh
    docker compose up -d
    ```    

6) #### Open a terminal in the container to interact with it:
    ```sh
    docker exec -it superelectric /bin/bash
    ```    
7) #### From now on the commands must be launched inside the container and not in the host machine

8) #### The first time running the container compile the workspace:
    ```sh
    cd && ./install.sh
    ```    

9) #### Best practice is to push the packages in the host and not in the docker container

# How to use superelectric container

    ros2 topic info -v <topic-name> 
    ros2 doctor -r 
    ros2 doctor -r | grep middleware

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)


<!-- CONTRIBUTORS -->
<h2 id="contributors"> :scroll: Contributors</h2>
<p>
  :man: <b>Mario Corsanici</b> <br>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Email: <a>mario.corsanici@intellimech.it</a> <br>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; GitHub: <a href="https://github.com/mariocorsanici">@mario-corsanici</a> <br>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Linkedin: <a href="https://www.linkedin.com/in/mario-corsanici-0b7b1a138/">@mario-corsanici-linkedin</a> <br>
</p>