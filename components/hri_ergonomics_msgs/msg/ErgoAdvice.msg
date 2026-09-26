# ErgoAdvice.msg
# Published on /humans/bodies/<body_id>/ergo_advice by ergo_advisor when that body's ergo_alert enters WARNING or CRITICAL.
# The scores are computed deterministically upstream; this message only explains them.
# ROS4HRI style: stamp = time of the skeleton sample the value comes from,
# frame_id = root frame of the body (body_<body_id>).
std_msgs/Header header

int32 level
int32 rula_score
string explanation
string recommendation
bool generated_by_llm
