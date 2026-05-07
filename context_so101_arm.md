# Project Context: SO101 Arm Control with ROS 2, MoveIt2, and Real Hardware

## Overview
The goal of this project is to control the SO101 robotic arm using ROS 2, MoveIt2, and a custom hardware interface. The architecture dynamically supports simulation (Isaac Sim), mock components (RViz only), and the physical hardware utilizing Feetech STS3215 serial servos.

## Architectural and Configuration Details

### 1. Hardware Interface (`so101_hardware_interface`)
- **Package Type:** Built as an `ament_cmake` package utilizing `ament_cmake_python` to properly install Python executable scripts (`scripts/hardware_interface.py`) and internal modules (`so101_hardware_interface.motors.feetech`).
- **Bridge Mechanism:** Uses `topic_based_ros2_control`. The Python node subscribes to `/real_joint_commands` and publishes actual joint states to `/real_joint_states`.
- **Serial Stability:** Prevents `[TxRxResult]` lockups by forcing a `1,000,000` baud rate and throttling the update loop to 25Hz.
- **Safe Startup:** Implements a "lock current position" mechanism. On launch, it dynamically reads the current physical joint states, clamps them to safe bounds, and commands them before turning on torque, preventing the arm from dropping or jumping.

### 2. MoveIt2 Configuration (`so101_moveit2_config`)
- **Modular `ros2_control`:** The URDF (`so101_new_calib.urdf.xacro`) and control macro (`so101_new_calib.ros2_control.xacro`) are dynamically parameterized using the `ros2_control_hardware_type` argument.
- **Supported Modes via CLI Argument:**
  - `mock_components`: Uses `mock_components/GenericSystem` for pure algorithmic testing in RViz.
  - `isaac`: Bridges `/isaac_joint_commands` and `/isaac_joint_states` for NVIDIA Isaac Sim.
  - `real`: Bridges `/real_joint_commands` and `/real_joint_states` for physical execution via `so101_hardware_interface`.

### 3. Calibration and Mathematical Alignment
- **Methodology:** Instead of relying on complex offset code, physical zeroes are determined structurally using recorded `#range_min` and `#range_max` variables generated from the `calibrate.py` tool. These values are saved to `resource/so101_calibration.json`.
- **Calculation:**
  - Standard Rotational Joints: `0` radians is aligned exactly to the physical middle: `(range_min + range_max) / 2.0`.
  - Gripper: `0` is aligned to the fully closed position: `range_min`.
- This simple baseline ensures the physical robot's coordinate system perfectly mirrors the strict `-pi` to `pi` bounds expected by MoveIt2 and RViz planning—bypassing "Start state out of bounds" errors.

## Current State
The project is fully functional, integrated, and completely modular. You can switch seamlessly between simulated, mock, and real hardware logic via launch arguments without manually commenting out source code. The real-world python interface cleanly passes executable checks, robustly maintains the serial connection, and correctly bridges joint states to MoveIt.# Project Context: SO101 Arm Control with ROS 2, MoveIt2, and Real Hardware

## Overview
The main goal of this project is to control the SO101 robotic arm using ROS 2, MoveIt2, and a custom hardware interface. The project started by integrating the arm with simulation (Isaac Sim) and RViz, and later transitioned to running the physical hardware utilizing Feetech STS3215 serial servos.

## Phase 1: Simulation and MoveIt Bringup
**Goal:** Get the arm simulating properly in Isaac Sim, with planning provided by MoveIt2.

**Problems & Solutions:**
- **Controller Spawning:** The `custom_demo.launch.py` was modeled after a Panda robot, leading to misnamed controllers and TF tree root inconsistencies.
  - *Solution:* Fixed controller names, mapped the base transform from `panda_link0` to `root`, and ensured RViz loaded the correct config.
- **Clock Issues:** Controllers were hanging because `use_sim_time` was misconfigured.
  - *Solution:* Disabled `use_sim_time` when not explicitly relying on the simulation clock.
- **Gripper Missing:** The gripper joint trajectory execution was failing.
  - *Solution:* Modified `ros2_controllers.yaml` to include the `gripper` joint in the action controller array.
- **Isaac Sim Connection:** The simulation wasn't moving because the topics didn't align.
  - *Solution:* Corrected the target topic from `/isaac_joint_command` to the correct namespace format.

## Phase 2: Real Hardware Transition
**Goal:** Control the physical SO101 robot since there was no existing C++ native `ros2_control` hardware plugin for the Feetech servos.

**Problems & Solutions:**
- **Hardware Interface Architecture:**
  - *Solution:* Since creating a full `ros2_control` C++ plugin from scratch is complex, we leveraged `topic_based_ros2_control`. This allowed us to write a custom Python node (`arm_hardware_interface/hardware_interface.py`) that wraps the `lerobot` Python serial driver. MoveIt communicates with the physical arm by publishing to `/real_joint_commands` and subscribing to `/real_joint_states`.
- **Serial Communication Lockups:**
  - *Problem:* Experiencing frequent `[TxRxResult] There is no status packet!` errors, causing the serial bus to crash.
  - *Solution:* Fixed by forcing a `1_000_000` baud rate in the `HardwareInterface` node and slowing down the state publishing loop to 25Hz (0.04s) to prevent packet collisions.
- **Startup Drops:** The arm would go limp or jump aggressively on launch.
  - *Solution:* Developed a `lock_current_position()` method on startup that immediately reads the current physical joint states, clamps them to safe bounds, and writes them back as target goals before turning on torque.
- **Stale Build Issues with topic_based_ros2_control:**
  - *Problem:* Faced persistent unexplained issues with commands and states not reflecting properly despite correct logic.
  - *Solution:* Discovered that the `topic_based_ros2_control` compiled workspace had issues. Deleting its build/install artifacts and rebuilding it completely from scratch resolved these hidden integration problems.

## Phase 3: Calibration and Mathematical Alignment
**Goal:** Make the physical robot's zero-position exactly match RViz's zero-position to avoid `Start state out of bounds` planning failures in MoveIt.

**Problems & Solutions:**
- **Incorrect Coordinate Mapping:** RViz showed the arm completely straight, but the physical robot was bent entirely differently. The conversion from `0-4095` encoder ticks to `-pi to pi` radians was entirely wrong.
- **Failed `lerobot` Logic Port:** We attempted to port the exact `apply_calibration()` and `revert_calibration()` math from the `lerobot` framework, relying heavily on a `homing_offset`. However, shifting around `2048` and applying modulo math proved overly complex and buggy for MoveIt's strict coordinate expectations.
- **The Final Simple Solution:**
  - Instead of utilizing abstract offsets, the user proposed geometric truth: Using `range_min` and `range_max` from `so101_calibration.json`.
  - For standard rotational joints, `0` radians is simply the middle of the mechanical range: `(range_min + range_max) / 2.0`.
  - For the gripper, `0` is simply its fully closed position: `range_min`.
  - We refactored `ticks_to_radians` and `radians_to_ticks` in the python hardware interface to shift away from this true physical center, apply the drive mode inversions if `drive_mode == 1`, and clamp safely using `max` and `min` bounds instead of standard `modulo` operations.

## Current State
The project is fully functional. The physical robot spawns completely flush with the virtual RViz representation. The topic-based hardware interface is robustly maintaining the serial bus connection, and MoveIt can successfully plan and execute trajectories without throwing bounds errors.