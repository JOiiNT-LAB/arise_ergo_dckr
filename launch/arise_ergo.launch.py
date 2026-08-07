import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    realsense_camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('realsense2_camera'),
                'launch', 'rs_launch.py')))

    body_detect = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('hri_body_detect'),
                'launch', 'hri_body_detect_with_args.launch.py')))

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(
            get_package_share_directory('human_description'),
            'config', 'human.rviz')],
        output='screen')

    ergodata_calculator = Node(
        package='ergo_pkg_py',
        executable='ergodata_calculator',
        name='ergodata_calculator',
        output='screen')

    rula_calculator = Node(
        package='ergo_pkg_py',
        executable='rula_calculator',
        name='rula_calculator',
        output='screen')

    # orion_bridge.py is not registered as a console_scripts entry point in
    # ergo_pkg_py/setup.py, so it can't be launched as a standard Node yet.
    orion_bridge = ExecuteProcess(
        cmd=['python3', PathJoinSubstitution([
            EnvironmentVariable('ROS_WS'),
            'src', 'ergo_pkg_py', 'ergo_pkg_py', 'orion_bridge.py'])],
        name='orion_bridge',
        output='screen')

    return LaunchDescription([
        realsense_camera,
        body_detect,
        rviz,
        ergodata_calculator,
        rula_calculator,
        orion_bridge,
    ])
