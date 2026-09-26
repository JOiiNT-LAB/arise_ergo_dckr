# hri_ergonomics_msgs

Ergonomic assessment interfaces for the ARISE Ergo pipeline, designed as an
extension of [ROS4HRI (REP-155)](https://www.ros.org/reps/rep-0155.html).
ROS4HRI's `hri_msgs` defines no ergonomic types, so these messages fill that gap
while following its conventions: each one starts with a `std_msgs/Header`
(`frame_id` = `body_<body_id>`, `stamp` = time of the skeleton sample) and is
published in the body namespace.

| Message | Topic | Content |
|---|---|---|
| `ErgoData` | `/humans/bodies/<body_id>/ergo_data` | 26 joint angles (degrees) + pelvis speed |
| `RULAScore` | `/humans/bodies/<body_id>/rula_score` | RULA final score (1–7) and partial scores |
| `RebaScore` | `/humans/bodies/<body_id>/reba_score` | REBA final score (1–15) and partial scores |
| `ErgoAlert` | `/humans/bodies/<body_id>/ergo_alert` | OK / WARNING / CRITICAL, sent on level change |
| `ErgoAdvice` | `/humans/bodies/<body_id>/ergo_advice` | explanation + recommendation for an alert |

The message definitions were previously part of `jntlb_fwk_msgs`.
