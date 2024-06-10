
from time import time
from math import fmod
import numpy as np
from realsense_camera.CameraStreamer import *
from RTDERobot import *
import robot_utils.kinematicsUtils as fk

from simple_pid import PID

print("here")
camera = CameraStreamer()
task_robot = RTDERobot("192.168.0.11",config_filename="control_loop_configuration.xml")
camera_robot = RTDERobot("192.168.0.10",config_filename="control_loop_configuration.xml")

def get_world_position_from_buffers(pixel_x, pixel_y, depth_frame, depth_intrinsic):
    depth = depth_frame.get_distance(pixel_x, pixel_y)

    # Convert pixel coordinates to world coordinates (from the Camera's Perspective!)
    ball_position = rs.rs2_deproject_pixel_to_point(depth_intrinsic, [pixel_x, pixel_y], depth)
    return np.array(ball_position)

def get_position():
    color_image, depth_image, depth_frame, depth_map, depth_intrinsics = camera.get_frames()
    if color_image.size == 0 or depth_image.size == 0:
        print("Can't receive frame (stream end?).")
        return None  # Return None to indicate an error state

    positions = detect_object(color_image)
    if len(positions) == 0:
        print('No object detected!')
        return None

    x1, y1, x2, y2 = positions[0]
    ball_center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
    return get_world_position_from_buffers(ball_center[0],ball_center[1], depth_frame,depth_intrinsics)

pid_controller_x = PID(Kp=1.5, Ki=0, Kd=0.5)
pid_controller_x.setpoint = 0

pid_controller_y = PID(Kp=0.6, Ki=0, Kd=0.1)
pid_controller_y.setpoint = 0

print("start!")
keep_moving = True
not_started = True
initial_pos = [0.12, -2.47, 0.018, -0.65, 1.456, -1.608]
while keep_moving:
    task_state = task_robot.getState()
    cam_state = camera_robot.getState()

    if not task_state.output_int_register_0:
        print("Not started yet", [round(q,2) for q in task_state.target_q])
        continue
    elif not_started:
        not_started = True

    if not task_state or not cam_state:
        break
    task_robot.sendWatchdog(1)
    camera_robot.sendWatchdog(1)

    current_task_config = task_state.target_q
    current_cam_config = cam_state.target_q

    ball_position = get_position()
    if ball_position is None:
        continue
    plate_center = fk.ur3e_effector_to_home(current_task_config,fk.plate_from_ee([0,0,0,1]))
    ball_top = fk.ur5e_effector_to_home(current_cam_config, fk.camera_from_ee(ball_position))
    plate_z_axis = fk.ur3e_effector_to_home(current_task_config,fk.plate_from_ee([0,0,1,1]))
    plate_x_axis = fk.ur3e_effector_to_home(current_task_config,fk.plate_from_ee([1,0,0,1]))
    plate_y_axis = fk.ur3e_effector_to_home(current_task_config,fk.plate_from_ee([0,1,0,1]))
    transform_to_plate = np.matrix([[plate_x_axis[0],plate_y_axis[0],plate_z_axis[0],plate_center[0]],
                                           [plate_x_axis[1],plate_y_axis[1],plate_z_axis[1],plate_center[1]],
                                           [plate_x_axis[2],plate_y_axis[2],plate_z_axis[2],plate_center[2]],
                                           [0,0,0,1]])
    # Transform to plate is supposed to give us the inverse matrix.
    # E.G. error = np.dot(transform_to_plate, ball_top)
    # Otherwise, we can try to get the dot product with the axis from the plate
    # E.G. x_error = np.dot(plate_x_axis, (ball_top - plate_center))
    error = ball_top - [-0.61362,-0.11040671,0.63503892, 1.]

    pos = initial_pos.copy()
    pos[5] += pid_controller_x(-error[1])
    pos[3] += pid_controller_y(-error[0])
    print(error)
    task_robot.sendConfig(pos)

