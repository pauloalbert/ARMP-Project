import matplotlib.pyplot as plt
import re
import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.patches as patches

from PIL import Image
from matplotlib.animation import PillowWriter
from regex import F
from sklearn.preprocessing import normalize

file_path = 'logs/synchronized_path_follow_checks.log'
log_data = None


with open(file_path, 'r') as file:
    log_data = file.read()


pattern = re.compile(
    r"(\d+\.\d+):WARNING:synchronized_path_follow_main.py;pose: \[([\d\., -e\+]+)\], force: \[([\d\., -e\+]+)\]")
matches = pattern.findall(log_data)

timestamps = []
poses = []
forces = []
for match in matches:
    time, pose, force = match
    timestamps.append(float(time))
    poses.append([float(x) for x in pose.split(', ')])
    forces.append([float(x) for x in force.split(', ')])




start_time = elements[0][0]
normalized_timestamps = [t - start_time for t in timestamps]
error_x, error_y, error_z = list(zip(*errors))

# Filter errors based on z position
plate_width, plate_height = 0.297, 0.21
PLATE_LEFT = -plate_width/2
PLATE_RIGHT = plate_width/2
PLATE_UP = plate_height/2
PLATE_DOWN = -plate_height/2
PLATE_CENTER = (np.average([PLATE_LEFT,PLATE_RIGHT]), np.average([PLATE_DOWN,PLATE_UP]))

# flip axis: x = y, y = -x
filtered_errors = [(t, y, -x, a) for t, x, y, z, a in zip(normalized_timestamps, error_x, error_y, error_z, arucos_list) if z == 0.035]

normalized_timestamps, ball_positions_x, ball_positions_y, arucos = zip(*filtered_errors)

FRAMERATE = 30
print("Length of timestamps:", len(normalized_timestamps))
print("Length of ball_positions_x:", len(ball_positions_x))
print("Length of ball_positions_y:", len(ball_positions_y))
print("total time of simulation:", normalized_timestamps[-1] - normalized_timestamps[0], "simulated time: ", len(normalized_timestamps)/FRAMERATE)

####This piece of code tries to ensure the rate of input data matches the gif FPS, however, its close enough as is.
timed_errors = []
lt = normalized_timestamps[0]-1/FRAMERATE
taccum = 0
for t, x, y, a in filtered_errors:
    if taccum < -1/FRAMERATE:           # Only add a value if time difference is significant enough.
        taccum += 1/FRAMERATE
    elif taccum > 1/FRAMERATE:
        timed_errors.append((t,x,y,a))
        timed_errors.append((t,x,y,a))
        taccum += t - lt - 2/FRAMERATE
        lt = t
    else:
        timed_errors.append((t,x,y,a))
        taccum += t - lt - 1/FRAMERATE
        lt = t

normalized_timestamps, ball_positions_x, ball_positions_y, arucos = zip(*timed_errors)
print("Length of timeset timestamps:", len(normalized_timestamps))
print("total time of simulation:", normalized_timestamps[-1] - normalized_timestamps[0], "simulated time: ", len(normalized_timestamps)/FRAMERATE)

#Figure stuff
fig, ax = plt.subplots()
ax.set_aspect(1)
grid_step = 0.05
ax.set_xticks([i for i in np.arange(0,PLATE_RIGHT, grid_step)] + [-i for i in np.arange(grid_step,abs(PLATE_LEFT), grid_step)])
ax.set_yticks([i for i in np.arange(0,PLATE_UP, grid_step)] + [-i for i in np.arange(grid_step, abs(PLATE_DOWN), grid_step)])
ax.set_xlim(PLATE_LEFT,PLATE_RIGHT)
ax.set_ylim(PLATE_DOWN,PLATE_UP)

plt.grid(True, 'major')


# # Add robot hand square
if DO_ROBOT_ARM:
    square = patches.Rectangle((PLATE_CENTER[0]-0.035+ball_screen_radius/2,PLATE_CENTER[1]+0.033+ball_screen_radius), 0.07-ball_screen_radius, 0.1, linewidth=1, alpha=0.2, facecolor='b',hatch='//')
    square2 = patches.Rectangle((PLATE_CENTER[0]-0.07+ball_screen_radius/2,PLATE_UP-0.002), 0.14-ball_screen_radius, 0.1, linewidth=1, alpha=0.2, facecolor='b',hatch='//')
    ax.add_patch(square)
    ax.add_patch(square2)

# # add arucos
VALID_ARUCOS = [a for a in range(12)]
SIZE = 51.5
VERT_DISP = 23 + SIZE
HOR_DISP = 23 + SIZE
SQUARE_SHAPE = [(-SIZE/2, SIZE/2), (SIZE/2, SIZE/2), (SIZE/2, -SIZE/2), (-SIZE/2, -SIZE/2)]
SHAPE = (3,4)
ARUCO_OBJ = [[(-1*(HOR_DISP * (i) + d[0] - HOR_DISP*(SHAPE[0]-1)/2) / 1000., (VERT_DISP*(-j) + d[1] + VERT_DISP*(SHAPE[1]-1)/2)/1000., 0) for d in SQUARE_SHAPE]  for j in range(SHAPE[1]) for i in range(SHAPE[0])]

if DO_ARUCOS_COLOR is not None:
    for aruco in ARUCO_OBJ:
        square = patches.Rectangle((PLATE_CENTER[0]+aruco[2][1],PLATE_CENTER[1]+aruco[2][0]), SIZE/1000., SIZE/1000., alpha=0.15, facecolor='black')
        ax.add_patch(square)

ball_dot, = plt.plot([], [], 'ro', markersize=ball_screen_radius*72/0.035)
old_dots, = plt.plot([],[], 'x', markersize=8)
if DO_PID_VECTOR:
    arrow = plt.quiver([0,0,0],[0,0,0],[0,0,0],[0,0,0],angles='xy', scale_units='xy', scale=1)

def init():
    ball_dot.set_data([], [])
    if DO_PID_VECTOR is True:
        return old_dots, ball_dot
    return old_dots, ball_dot

def update(frame):
    ball_dot.set_data([ball_positions_x[frame]], [ball_positions_y[frame]])
    if DO_TRAILING_X_COUNT > 0:
        old_dots.set_data(ball_positions_x[max(frame-DO_TRAILING_X_COUNT,0):max(frame-1,0)], ball_positions_y[max(frame-DO_TRAILING_X_COUNT,0):max(frame-1,0)])
    if DO_ARUCOS_COLOR is True:
        patch_list = []
        for index, aruco in enumerate(ARUCO_OBJ):
            patch_list.append(patches.Rectangle((PLATE_CENTER[0]+aruco[2][1],PLATE_CENTER[1]+aruco[2][0]), SIZE/1000., SIZE/1000., alpha=0.15, facecolor=('green' if index in arucos[frame] else 'black')))
        for p in ax.patches:
            p.remove()
        for p in patch_list:
            ax.add_patch(p)
        if DO_ROBOT_ARM:
            square = patches.Rectangle((PLATE_CENTER[0]-0.035+ball_screen_radius/2,PLATE_CENTER[1]+0.033+ball_screen_radius), 0.07-ball_screen_radius, 0.1, linewidth=1, alpha=0.2, facecolor='b',hatch='//')
            square2 = patches.Rectangle((PLATE_CENTER[0]-0.07+ball_screen_radius/2,PLATE_UP-0.002), 0.14-ball_screen_radius, 0.1, linewidth=1, alpha=0.2, facecolor='b',hatch='//')
            ax.add_patch(square)
            ax.add_patch(square2)

    if DO_PID_VECTOR:
        SET_FAKE_TIME(normalized_timestamps[frame])
        dx = pid_controller_x(ball_positions_x[frame],)
        dy = pid_controller_y(ball_positions_y[frame])
        arrow.set_UVC([dx,0,dx],[0,dy,dy],[1,0,0.5])#1,0 fucks with the colors somehow, which i wanted?
        return old_dots, ball_dot

    return old_dots, ball_dot

try:
    anim = FuncAnimation(plt.gcf(), update, frames=len(normalized_timestamps), init_func=init, blit=True)
    anim.save('media/ball_simulation12.gif', writer='pillow', fps=30)
except Exception as e:
    print(f"Error saving GIF: {e}")
