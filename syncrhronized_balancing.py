import sys
import os
import numpy as np
from simple_pid import PID

# Append the parent directory of the current script's directory to sys.path
from src.CameraUtils.CameraStreamer import CameraStreamer
from src.CameraUtils.localization import get_aruco_corners, get_object, getPixelOnPlane, get_obj_pxl_points
from src.CameraUtils.cameraConstants.constants import *
from src.CameraUtils.CameraFunctions import *
from src.MotionUtils.motionConstants.constants import *
from src.Robot.RTDERobot import *
import src.MotionUtils.PathFollow as PathFollow

def toView(conf, end = "\n"):
    return [round(a, 2) for a in conf]

# TEMP
def shortenLookahead(lookahead, other_robot_loc, other_robot_target):
    """decrease lookahead based on the other robots position
       [!] DO NOT DECREASE CLAMP!!! otherwise both robots will simply deadlock"""
    other_distance_squared = np.dot(other_robot_loc - other_robot_target, other_robot_loc - other_robot_target)
    shorten = 0.75 / (other_distance_squared + 0.001)
    return PathFollow.clamp(shorten * lookahead ,0 , lookahead)

"""Path follower that maintains the camera runs the same path points as the task robot.
    Requires both robots to use 'rtde_synced_servoj.urp'"""

task_path = [[-0.129, -1.059, -1.229, -0.875, 1.716, 1.523],
             [0.3, -1.059, -1.229, -0.875, 1.716, 1.523],
             [-0.3, -1.059, -1.229, -0.875, 1.716, 1.523],
             [0.3, -1.059, -1.229, -0.875, 1.716, 1.523]]

camera_path = [[-0.01, -1.653, 0.0, -0.572, -1.399, 0.0],
               [-0.3, -1.653, 0.0, -0.572, -1.399, 0.0],
               [0.3, -1.653, 0.0, -0.572, -1.399, 0.0],
               [-0.3, -1.653, 0.0, -0.572, -1.399, 0.0]]

SLOW_LOOKAHEAD = 0.1
SLOW_EDGE_CUTOFF = 0.05
SLOW_CLAMP = 0.1

task_follower = PathFollow.PathFollowStrict(task_path, SLOW_LOOKAHEAD, SLOW_EDGE_CUTOFF)
print("initializing Robots")
camera = CameraStreamer(no_depth=True)
task_robot = RTDERobot("192.168.0.12",config_filename="control_loop_configuration.xml")
camera_robot = RTDERobot("192.168.0.10",config_filename="control_loop_configuration.xml")

pid_controller_x = PID(Kp=0.9, Ki=0, Kd=0.321)
pid_controller_x.setpoint = 0

pid_controller_y = PID(Kp=0.7, Ki=0, Kd=0.16)
pid_controller_y.setpoint = 0

plate_center = (0, 0, 0)

CAMERA_FAILED_MAX = 5

print("start!")

timer_print = 0
keep_moving = True
has_started = False
_task_target_t = 0
_task_target_edge = 0
# initial_pos = [-0.129, -1.059, -1.229, -0.875, 1.716, 1.523]

while keep_moving:
    color_image, _, _, _, _, Is_image_new = camera.get_frames()
    task_state = task_robot.getState()
    cam_state = camera_robot.getState()

    if not task_state or not cam_state:
        print("Robot ", "task (or both)" if not task_state else "cam", " is not on!")
        break

    # Wait for both robots to say they are waiting to start. (the programs are running)
    if (task_state.output_int_register_0 != 2 or cam_state.output_int_register_0 !=2) and not has_started:
        task_robot.sendWatchdog(1)
        camera_robot.sendWatchdog(1)

        timer_print += 1
        if timer_print % 120 == 1:
            print(" waiting for ", "[task robot]" if task_state.output_int_register_0 != 2 else "", " [camera_robot]" if cam_state.output_int_register_0 != 2 else "")
            print("task config:", [round(q,2) for q in task_state.target_q])
            print("camera config:", [round(q,2) for q in cam_state.target_q])
    else:
        # Running!
        task_robot.sendWatchdog(2)
        camera_robot.sendWatchdog(2)

        has_started = True

    # Has started ignores the flags once we are running ( once we do, the robots are no longer "waiting to start" )
    if not has_started:
        continue

    if not Is_image_new:
        print("Old image!")
        continue
    if color_image is None or color_image.size == 0:
        continue

    current_task_config = task_state.target_q
    current_cam_config = cam_state.target_q

    ball_position = get_ball_position(color_image,DEBUG=False)
    error = (0,0)
    if ball_position is None:
        camera_failed_counter += 1
        if camera_failed_counter < CAMERA_FAILED_MAX:
            continue
        print("camera failed for ", camera_failed_counter, " frames")
    else:
        camera_failed_counter = 0
        error = ball_position - plate_center

    # Follow camera path
    cam_lookahead_config = PathFollow.getClampedTarget(current_cam_config, PathFollow.getPointFromT(camera_path, _task_target_edge, _task_target_t), SLOW_CLAMP)
    shortened_lookahead = shortenLookahead(TASK_PATH_LOOKAHEAD, current_cam_config, cam_lookahead_config)

    # Follow task path
    task_lookahead_config, target_edge, target_t = task_follower.getLookaheadData(current_task_config,lookahead_distance=shortened_lookahead)
    task_follower.updateCurrentEdge(current_task_config)

    _task_target_edge = target_edge
    _task_target_t = target_t

    task_config = PathFollow.getClampedTarget(current_task_config, task_lookahead_config, SLOW_CLAMP)
    task_config[5] += pid_controller_x(-error[1])
    task_config[3] += pid_controller_y(-error[0])

    camera_robot.sendConfig(cam_lookahead_config)
    task_robot.sendConfig(task_config)



