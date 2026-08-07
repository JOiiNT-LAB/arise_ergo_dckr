# This is an auto generated Dockerfile for ros:desktop-full
# generated from docker_images/create_ros_image.Dockerfile.em
# FROM osrf/ros:jazzy-desktop-full
FROM eprosima/vulcanexus:humble-desktop

ENV TZ=Europe/Rome

ARG DEBIAN_FRONTEND=noninteractive

ARG HOME
ARG ROS_WS
ARG ROS_DOMAIN_ID
ENV ROS_WS $ROS_WS

# LOCALE and LANGUAGE settings
RUN apt update \ 
    && apt install -y -q tzdata locales \
    && rm -rf /var/lib/apt/lists/* \    
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && dpkg-reconfigure tzdata 

ENV LANG=en_US.UTF-8  
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# System utilities
RUN apt update && apt install -y \
    git \
    nano \
    htop \
    iftop \
    net-tools \
    iputils-ping \
    at \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Build/graphics dev libraries
RUN apt update && apt install -y \
    build-essential \
    libglfw3-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

# ROS2 packages
RUN apt update && apt install -y \
    ros-humble-joint-state-publisher-gui \
    ros-humble-launch-param-builder \
    ros-humble-tf-transformations \
    ros-humble-diagnostic-updater \
    "ros-humble-librealsense2*" \
    "ros-humble-realsense2-*" \
    ros-humble-launch-pal \
    ros-humble-hri-rviz \
    && rm -rf /var/lib/apt/lists/*

# RUN pip install transform3d google google-cloud mediapipe==0.10.9 protobuf==3.19.4 ikpy lap
RUN pip install "numpy==1.23.5" transform3d google google-cloud mediapipe==0.10.9 protobuf==3.19.4 ikpy lap requests
RUN mkdir -p $ROS_WS/src && mv /root/.bashrc /home/ros_user

ENV HOME $HOME

RUN echo "export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}" >> ~/.bashrc
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
RUN echo "source ${ROS_WS}/install/setup.bash" >> ~/.bashrc

RUN echo "source ~/.bashrc" 

WORKDIR $ROS_WS

CMD ["/bin/bash"]