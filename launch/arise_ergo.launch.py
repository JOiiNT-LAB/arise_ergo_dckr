import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Start RViz2 for visualization (requires X11)')

    use_llm = DeclareLaunchArgument(
        'use_llm',
        default_value='false',
        description='Start ergo_advisor, which explains alerts with a local LLM '
                    '(needs the ollama service: docker compose --profile llm up -d)')

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

    # FindPackageShare is a substitution, so the config path is resolved only when
    # the condition holds — with use_rviz:=false this launch file also works in a
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
        output='screen')

    return LaunchDescription([
        use_rviz,
        use_llm,
        realsense_camera,
        body_detect,
        rviz,
        ergodata_calculator,
        rula_calculator,
        reba_calculator,
        ergo_alert,
        ergo_advisor,
        orion_bridge,
    ])
