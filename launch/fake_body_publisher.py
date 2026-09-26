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

Frame convention (matching what the calculator assumes): X forward, Y left,
Z up, with body_<body_id> on the floor under the subject. The head offset is
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
WAIST_HEIGHT = 1.00
SPINE_LEN = 0.35          # waist -> torso
SHOULDER_LEN = 0.45       # waist -> shoulder centre
SHOULDER_HALF_WIDTH = 0.20
HIP_HALF_WIDTH = 0.12
UPPER_ARM_LEN = 0.30
FOREARM_LEN = 0.25
HEAD_UP = 0.175           # torso -> head, vertical part
HEAD_FWD = HEAD_UP / 3.0  # torso -> head, forward part: keeps neck_angle ~ 0
THIGH_LEN = 0.43
SHIN_LEN = 0.44

# Each posture is (name, trunk_flexion, trunk_twist, arm_flexion, elbow_flexion,
# sway_amplitude), angles in degrees, sway in metres. Together they walk the
# pipeline through a low-risk posture up to a clearly bad one.
POSTURES = [
    ("neutral standing",    0.0,  0.0,   0.0,   5.0, 0.000),
    ("arms forward 60deg",  0.0,  0.0,  60.0,  30.0, 0.000),
    ("arms overhead",       0.0,  0.0, 160.0,  20.0, 0.000),
    ("trunk bent 45deg",   45.0,  0.0,  40.0,  60.0, 0.000),
    ("trunk twisted",      20.0, 30.0,  50.0,  45.0, 0.000),
    ("walking in place",    5.0,  0.0,  20.0,  25.0, 0.060),
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


def build_skeleton(trunk_flex, trunk_twist, arm_flex, elbow_flex, sway):
    """Forward-kinematics the 15 joint positions for one posture.

    Returns a dict of link name -> position in the body root frame.
    """
    trunk = rot_y(trunk_flex)
    twist = rot_z(trunk_twist)

    waist = np.array([sway, 0.0, WAIST_HEIGHT])
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
            waist + np.array([0.0, sign * HIP_HALF_WIDTH, -0.05]))

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

        self.rate = self.get_parameter('rate').value
        self.posture_duration = self.get_parameter('posture_duration').value
        self.sway_period = self.get_parameter('sway_period').value
        self.body_ids = list(self.get_parameter('body_ids').value)

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

            # A moving waist is what makes the calculator's `speed` field non-zero.
            sway = sway_amp * math.sin(2.0 * math.pi * elapsed / self.sway_period)
            joints = build_skeleton(trunk_flex, trunk_twist, arm_flex, elbow_flex, sway)

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
