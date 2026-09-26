cmake_minimum_required(VERSION 3.8)
project(hri_ergonomics_msgs)

find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ErgoData.msg"
  "msg/RULAScore.msg"
  "msg/RebaScore.msg"
  "msg/ErgoAlert.msg"
  "msg/ErgoAdvice.msg"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
