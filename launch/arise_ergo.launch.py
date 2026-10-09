import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription,
                            RegisterEventHandler)
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


def generate_launch_description():
    use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Start RViz2 for visualization (requires X11)')

    use_camera = DeclareLaunchArgument(
        'use_camera',
        default_value='true',
        description='Start the RealSense driver — set to false to feed the detector '
                    'from something else (a rosbag, a video republished on the camera topics)')

    use_orion = DeclareLaunchArgument(
        'use_orion',
        default_value='true',
        description='Start orion_bridge — set to false to test the ROS2 side without '
                    'writing to the FIWARE stack')

    use_llm = DeclareLaunchArgument(
        'use_llm',
        default_value='false',
        description='Start ergo_advisor, which explains alerts with a local LLM '
                    '(needs the ollama service: docker compose --profile llm up -d)')

    realsense_camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('realsense2_camera'),
                'launch', 'rs_launch.py')),
        # The detector reads the depth at a colour-image pixel (the hips), so the depth
        # has to be registered on the colour image: the driver's align_depth filter.
        launch_arguments={'align_depth.enable': 'true'}.items(),
        condition=IfCondition(LaunchConfiguration('use_camera')))

    # Upstream hri_body_detect (ros4hri, 3.4.x) as a lifecycle node. Its own launch file
    # needs PAL's launch_pal and diagnostic_aggregator, which are not in this image, so
    # the node is started here with the RealSense topics. It publishes one random id per
    # track under /humans/bodies/<id>/, the ids of the people it follows are on
    # /humans/bodies/tracked.
    body_detect = LifecycleNode(
        package='hri_body_detect',
        executable='hri_body_detect',
        name='hri_body_detect',
        namespace='',
        output='both',
        emulate_tty=True,
        parameters=[{'use_depth': True,
                     'detection_conf_thresh': 0.5}],
        remappings=[
            ('image', '/camera/camera/color/image_raw'),
            ('camera_info', '/camera/camera/color/camera_info'),
            ('depth_image', '/camera/camera/aligned_depth_to_color/image_raw'),
            ('depth_info', '/camera/camera/aligned_depth_to_color/camera_info')])

    configure_body_detect = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(body_detect),
        transition_id=Transition.TRANSITION_CONFIGURE))

    activate_body_detect = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=body_detect, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(body_detect),
            transition_id=Transition.TRANSITION_ACTIVATE))]))

    # human_ros4hri.rviz instead of the human_description one: that file is written for
    # the single id `default` (frames *_default, Fixed Frame body_default) and shows
    # nothing with real ids. This one uses the hri_rviz Skeletons3D / TF_HRI displays,
    # which follow whatever bodies are tracked.
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(THIS_DIR, 'human_ros4hri.rviz')],
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
        use_camera,
        use_orion,
        use_llm,
        realsense_camera,
        body_detect,
        configure_body_detect,
        activate_body_detect,
        rviz,
        ergodata_calculator,
        rula_calculator,
        reba_calculator,
        ergo_alert,
        ergo_advisor,
        orion_bridge,
    ])
