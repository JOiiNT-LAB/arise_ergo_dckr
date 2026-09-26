# RebaScore.msg
# ROS4HRI style: stamp = time of the skeleton sample the value comes from,
# frame_id = root frame of the body (body_<body_id>).
std_msgs/Header header

int32 full

int32 trunk
int32 neck
int32 legs
int32 score_a

int32 left_upper_arm
int32 right_upper_arm
int32 upper_arm

int32 left_lower_arm
int32 right_lower_arm
int32 lower_arm

int32 left_wrist
int32 right_wrist
int32 wrist
int32 score_b
