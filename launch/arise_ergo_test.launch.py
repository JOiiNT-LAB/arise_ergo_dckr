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

    use_llm = DeclareLaunchArgument(
        'use_llm',
        default_value='false',
        description='Start ergo_advisor, which explains alerts with a local LLM '
                    '(needs the ollama service: docker compose --profile llm up -d)')

    body_ids = DeclareLaunchArgument(
        'body_ids',
        default_value="['default']",
        description="ROS4HRI body ids simulated by the fixture, e.g. \"['a', 'b']\" "
                    "to test several people at once")

    fake_body = ExecuteProcess(
        cmd=['python3', os.path.join(THIS_DIR, 'fake_body_publisher.py'),
             '--ros-args', '-p', ['body_ids:=', LaunchConfiguration('body_ids')]],
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

    ergo_advisor = Node(
        package='ergo_pkg_py',
        executable='ergo_advisor',
        name='ergo_advisor',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_llm')))

    orion_bridge = Node(
        package='ergo_pkg_py',
        executable='orion_bridge',
        name='orion_bridge',
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_orion')))

    return LaunchDescription([
        use_rviz,
        use_llm,
        use_orion,
        body_ids,
        fake_body,
        rviz,
        ergodata_calculator,
        rula_calculator,
        reba_calculator,
        ergo_alert,
        ergo_advisor,
        orion_bridge,
    ])
