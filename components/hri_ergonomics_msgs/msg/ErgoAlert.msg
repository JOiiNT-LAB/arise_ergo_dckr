# ErgoAlert.msg
# Published on /humans/bodies/<body_id>/ergo_alert only when the alert level changes (edge-triggered).
# ROS4HRI style: stamp = time of the skeleton sample the value comes from,
# frame_id = root frame of the body (body_<body_id>).
std_msgs/Header header

int32 LEVEL_OK=0
int32 LEVEL_WARNING=1
int32 LEVEL_CRITICAL=2

int32 level
string description
int32 rula_score
