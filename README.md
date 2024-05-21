Yada Yada this is a semester project we'll make this more official later i promise.


Idea: having the arm hold a plate, on which a ball resides, and to try to move it around a pre determined obstacle, to a predetermined goal.

- The first challenge we would face with this project is planning a path where we have a constraint that is not just robot-robot and robot-obstacle collisions, but also an allowed angle of the plate, that may have some leeway. (we are not entirely sure if this is non trivial however).
- The second challenge we want to try to explore, is using the real-sense camera to check how far the ball is from the center of the plate, and adjusting the angle to prevent it from falling out. this closed loop is akin to a local avoidance among a global planner.

### Goals
1. Writing a motion planning algorithm that has the plate constraints in mind
2. Learning the realSense API
3. Writing URX path follower.
4. Balancing a ball on a plate with URX
5. combining the two!
