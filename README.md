# SO101 MoveIt 2 Configuration

This package contains the MoveIt 2 configuration for the SO101 robotic arm. It provides the necessary SRDF, kinematics (`kinematics.yaml`), planning pipelines (OMPL, CHOMP, Pilz, STOMP), and ros2 controllers required to perform motion planning and trajectory execution.

## Modular Hardware Interface Configuration

The `ros2_control` layout for the arm (`config/so101_new_calib.ros2_control.xacro`) is fully modular and supports dynamically switching between different hardware backends. This eliminates the need to manually comment or uncomment configurations in the `.xacro` files!

By passing the `ros2_control_hardware_type` launch argument, the URDF automatically selects the appropriate hardware interface plugin:

- **`mock_components`**: Sets up `mock_components/GenericSystem` for pure RViz visualization and testing without external simulation or physical hardware.
- **`isaac`**: Configures `topic_based_ros2_control/TopicBasedSystem` to map to `/isaac_joint_commands` and `/isaac_joint_states` for integration with NVIDIA Isaac Sim.
- **`real`**: Configures `topic_based_ros2_control/TopicBasedSystem` to map to `/real_joint_commands` and `/real_joint_states` to drive the physical robot via the `so101_hardware_interface` package.

## Usage

You can launch the MoveIt pipeline and inject the desired hardware interface directly via the command line.

### 1. Pure Simulation (Mock Components)
```bash
ros2 launch so101_moveit2_config custom_demo.launch.py ros2_control_hardware_type:=mock_components
```

### 2. Isaac Sim Integration
Ensure your Isaac Sim environment is running and bridging the correct topics, then launch MoveIt:
```bash
ros2 launch so101_moveit2_config custom_demo.launch.py ros2_control_hardware_type:=isaac
```

### 3. Real Hardware (Physical Robot)
To control the physical SO101 arm, ensure the `so101_hardware_interface` package is built, the workspace is sourced, and the arm has been calibrated via `calibrate.py`. Then run:
```bash
ros2 launch so101_moveit2_config control_real_so101.launch.py ros2_control_hardware_type:=real
```

## Structure
- **`config/`**: Contains the core configuration files including the URDF macros (`so101_new_calib.urdf.xacro`), SRDF (`so101_new_calib.srdf`), `ros2_controllers.yaml`, joint limits, and the modular `so101_new_calib.ros2_control.xacro` switch logic.
- **`launch/`**: Contains the primary launch files (`custom_demo.launch.py` and `control_real_so101.launch.py`) structured to declare and pass the `ros2_control_hardware_type` argument directly to the URDF parser.