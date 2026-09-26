#!/usr/bin/env python3
"""Publish a synthetic ROS4HRI body skeleton, so the ergonomic pipeline can run
without a RealSense camera and without hri_body_detect.

Like hri_body_detect, it follows the ROS4HRI conventions: the ids of the bodies
are published on /humans/bodies/tracked, and each body gets the 15 tf frames
`ergodata_calculator` looks up (<link>_<body_id>, relative to body_<body_id>),
cycling through a fixed sequence of postures. Only the translations matter: the
calculator ignores the rotations.

The `body_ids` parameter (default ["default"], the id hri_body_detect uses)
simulates several people; each one starts its posture cycle one posture later
than the previous, so their scores differ at any given time.

Frame convention (REP-155): body_<body_id> has its origin at the mid point of
the hips, X forward (out of the body), Y left, Z up; it is parented to the
camera frame (`camera_link`, as hri_body_detect parents it to the camera), 2.5 m
in front of it and facing it. Walking in place moves body_<body_id> itself, as
a real tracker does, which is what the calculator's `speed` measures. The head
offset is
1/3 of its vertical offset, which is exactly the `atan(1/3) = 18.4349` degrees
the calculator subtracts from `neck_angle` — so the neutral posture yields a
neck angle of ~0 instead of an arbitrary constant.
"""

import math

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from hri_msgs.msg import IdsList
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

# Segment lengths in metres, roughly a 1.75 m subject.
HIP_HEIGHT = 0.95         # floor -> mid point of the hips (body_<id> origin)
WAIST_ABOVE_HIPS = 0.05   # mid-hips -> waist

# Where the simulated people stand with respect to the camera frame.
CAMERA_HEIGHT = 1.20      # camera above the floor
CAMERA_DISTANCE = 2.50    # people stand this far in front of the camera
BODY_SPACING = 0.80       # lateral distance between simulated people
SPINE_LEN = 0.35          # waist -> torso
SHOULDER_LEN = 0.45       # waist -> shoulder centre
SHOULDER_HALF_WIDTH = 0.20
HIP_HALF_WIDTH = 0.12
UPPER_ARM_LEN = 0.30
FOREARM_LEN = 0.25
HEAD_UP = 0.175           # torso -> head, vertical part
# The calculator subtracts the URDF head offset, atan(1/3) = 18.4349 deg, from
# neck_angle. Leaning the head a further NECK_FLEXION forward gives a natural,
# slightly flexed neck. It must not be exactly 0: RULA/REBA read any negative
# neck angle as extension, so floating-point noise around 0 used to flip the
# scores of every posture.
NECK_FLEXION = 5.0
HEAD_FWD = HEAD_UP * math.tan(math.atan(1.0 / 3.0) + math.radians(NECK_FLEXION))
THIGH_LEN = 0.43
SHIN_LEN = 0.44

# Each posture is (name, trunk_flexion, trunk_twist, arm_flexion, elbow_flexion,
# sway_amplitude), angles in degrees, sway in metres. Together they walk the
# pipeline through a low-risk posture up to a clearly bad one: "bent 70deg
# reaching" is the one that crosses the RULA warning threshold (5). Every angle
# is kept at least a few degrees away from the RULA/REBA band limits, so the
# expected scores do not depend on floating-point rounding.
POSTURES = [
    ("neutral standing",    0.0,  0.0,   0.0,   5.0, 0.000),
    ("arms forward 60deg",  0.0,  0.0,  60.0,  30.0, 0.000),
    ("arms overhead",       0.0,  0.0, 160.0,  20.0, 0.000),
    ("bent 70deg reaching", 70.0,  0.0, 110.0,  50.0, 0.000),
    ("trunk twisted",      25.0, 30.0,  50.0,  45.0, 0.000),
    ("walking in place",   10.0,  0.0,  10.0,  25.0, 0.060),
]


def rot_y(deg):
    """Rotation about +Y: tilts a vector forward (+X) for a positive angle."""
    a = math.radians(deg)
    return np.array([[math.cos(a), 0.0, math.sin(a)],
                     [0.0, 1.0, 0.0],
                     [-math.sin(a), 0.0, math.cos(a)]])


def rot_z(deg):
    """Rotation about +Z: yaws a vector, used for trunk twisting."""
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0.0],
                     [math.sin(a), math.cos(a), 0.0],
                     [0.0, 0.0, 1.0]])


def build_skeleton(trunk_flex, trunk_twist, arm_flex, elbow_flex):
    """Forward-kinematics the 15 joint positions for one posture.

    Returns a dict of link name -> position in the body root frame, whose
    origin is the mid point of the hips.
    """
    trunk = rot_y(trunk_flex)
    twist = rot_z(trunk_twist)

    waist = np.array([0.0, 0.0, WAIST_ABOVE_HIPS])
    torso = waist + trunk @ np.array([0.0, 0.0, SPINE_LEN])
    shoulder_c = waist + trunk @ np.array([0.0, 0.0, SHOULDER_LEN])
    head = torso + trunk @ np.array([HEAD_FWD, 0.0, HEAD_UP])

    joints = {
        "waist": waist,
        "torso": torso,
        "head": head,
    }

    # Shoulder line follows both the trunk flexion and the twist.
    for side, sign in (("l", 1.0), ("r", -1.0)):
        joints[f"{side}_shoulder"] = (
            shoulder_c + trunk @ twist @ np.array([0.0, sign * SHOULDER_HALF_WIDTH, 0.0]))
        joints[f"{side}_hip"] = (
            waist + np.array([0.0, sign * HIP_HALF_WIDTH, -WAIST_ABOVE_HIPS]))

    # Arms: hanging straight down is (0, 0, -1); a positive arm_flexion swings
    # the segment forward, so the shoulder-elbow vector rotates by -arm_flex.
    upper_dir = trunk @ rot_y(-arm_flex) @ np.array([0.0, 0.0, -1.0])
    fore_dir = trunk @ rot_y(-(arm_flex + elbow_flex)) @ np.array([0.0, 0.0, -1.0])
    for side in ("l", "r"):
        shoulder = joints[f"{side}_shoulder"]
        elbow = shoulder + upper_dir * UPPER_ARM_LEN
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_wrist"] = elbow + fore_dir * FOREARM_LEN

    # Legs stay straight: the RULA leg score is not the point of this fixture.
    for side, sign in (("l", 1.0), ("r", -1.0)):
        hip = joints[f"{side}_hip"]
        knee = hip + np.array([0.0, 0.0, -THIGH_LEN])
        joints[f"{side}_knee"] = knee
        joints[f"{side}_ankle"] = knee + np.array([0.0, 0.0, -SHIN_LEN])

    return joints


class FakeBodyPublisher(Node):

    def __init__(self):
        super().__init__('fake_body_publisher')

        self.declare_parameter('rate', 30.0)
        self.declare_parameter('posture_duration', 6.0)
        self.declare_parameter('sway_period', 2.0)
        self.declare_parameter('body_ids', ['default'])
        self.declare_parameter('camera_frame', 'camera_link')

        self.rate = self.get_parameter('rate').value
        self.posture_duration = self.get_parameter('posture_duration').value
        self.sway_period = self.get_parameter('sway_period').value
        self.body_ids = list(self.get_parameter('body_ids').value)
        self.camera_frame = self.get_parameter('camera_frame').value

        self.broadcaster = TransformBroadcaster(self)
        self.tracked_pub = self.create_publisher(IdsList, '/humans/bodies/tracked', 1)
        self.start = self.get_clock().now()
        self.current_posture = {}

        self.timer = self.create_timer(1.0 / self.rate, self.publish_skeleton)
        self.get_logger().info(
            f"Publishing a synthetic body skeleton at {self.rate:.0f} Hz — "
            f"{len(POSTURES)} postures, {self.posture_duration:.0f}s each, "
            f"bodies {self.body_ids}")

    def publish_skeleton(self):
        elapsed = (self.get_clock().now() - self.start).nanoseconds / 1e9
        stamp = self.get_clock().now().to_msg()

        tracked = IdsList()
        tracked.header.stamp = stamp
        tracked.ids = self.body_ids
        self.tracked_pub.publish(tracked)

        for offset, body_id in enumerate(self.body_ids):
            index = (int(elapsed / self.posture_duration) + offset) % len(POSTURES)
            name, trunk_flex, trunk_twist, arm_flex, elbow_flex, sway_amp = POSTURES[index]

            if name != self.current_posture.get(body_id):
                self.current_posture[body_id] = name
                self.get_logger().info(f"Posture [{body_id}] -> {name}")

            # Walking in place moves the whole body (body_<id>) back and forth in
            # front of the camera: that is what the calculator's `speed` measures.
            sway = sway_amp * math.sin(2.0 * math.pi * elapsed / self.sway_period)
            lateral = (offset - (len(self.body_ids) - 1) / 2.0) * BODY_SPACING

            body = TransformStamped()
            body.header.stamp = stamp
            body.header.frame_id = self.camera_frame
            body.child_frame_id = f'body_{body_id}'
            body.transform.translation.x = CAMERA_DISTANCE + sway
            body.transform.translation.y = lateral
            body.transform.translation.z = HIP_HEIGHT - CAMERA_HEIGHT
            body.transform.rotation.z = 1.0  # yaw 180 deg: the body faces the camera
            body.transform.rotation.w = 0.0
            self.broadcaster.sendTransform(body)

            joints = build_skeleton(trunk_flex, trunk_twist, arm_flex, elbow_flex)
            for link, position in joints.items():
                tf = TransformStamped()
                tf.header.stamp = stamp
                tf.header.frame_id = f'body_{body_id}'
                tf.child_frame_id = f'{link}_{body_id}'
                tf.transform.translation.x = float(position[0])
                tf.transform.translation.y = float(position[1])
                tf.transform.translation.z = float(position[2])
                tf.transform.rotation.w = 1.0
                self.broadcaster.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = FakeBodyPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
