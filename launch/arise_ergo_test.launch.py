"""Run the ergonomic pipeline against a synthetic body, with no camera attached.

Same node chain as arise_ergo.launch.py, but `fake_body_publisher.py` replaces
the RealSense camera and hri_body_detect. Useful to check the calculators, the
alert node and the Orion bridge on a machine with no RealSense, or in CI.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


def generate_launch_description():
    use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='Start RViz2 to look at the synthetic skeleton (requires X11)')

    use_orion = DeclareLaunchArgument(
        'use_orion',
        default_value='true',
        description='Start orion_bridge — set to false to test the ROS2 side '
                    'without the FIWARE stack running')

    fake_body = ExecuteProcess(
        cmd=['python3', os.path.join(THIS_DIR, 'fake_body_publisher.py')],
        name='fake_body_publisher',
        output='screen')

    # FindPackageShare is a substitution, so the path is resolved only if the
    # condition holds — with use_rviz:=false this launch file works in a
    # workspace where human_description was never built.
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', PathJoinSubstitution(
            [FindPackageShare('human_description'), 'config', 'human.rviz'])],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz')))

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

    reba_calculator = Node(
        package='ergo_pkg_py',
        executable='reba_calculator',
        name='reba_calculator',
        output='screen')

    ergo_alert = Node(
        package='ergo_pkg_py',
        executable='ergo_alert',
        name='ergo_alert',
        output='screen')

    orion_bridge = Node(
        package='ergo_pkg_py',
        executable='orion_bridge',
        name='orion_bridge',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_orion')))

    return LaunchDescription([
        use_rviz,
        use_orion,
        fake_body,
        rviz,
        ergodata_calculator,
        rula_calculator,
        reba_calculator,
        ergo_alert,
        orion_bridge,
    ])
