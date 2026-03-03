import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit as onprocess_exit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
import xacro

def generate_launch_description():
    
    robotXacroName='so101_new_calib'
    namePackage='so101_moveit2_config'
    modelFileRelativePath='config/so101_new_calib.urdf.xacro'
    
    # MoveIt2 configuration
    moveit_config = (
        MoveItConfigsBuilder(robot_name="so101_new_calib", package_name="so101_moveit2_config")
        .robot_description(
            file_path=modelFileRelativePath,
            mappings={"ros2_control_hardware_type": LaunchConfiguration("ros2_control_hardware_type")},
        )
        .robot_description_semantic(file_path="config/so101_new_calib.srdf")
        .planning_scene_monitor(publish_robot_description=True, publish_robot_description_semantic=True)
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl", "chomp", "pilz_industrial_motion_planner", "stomp"])
        .to_moveit_configs()
    )
    
    # Simulation Config (Gazebo)
    gazebo_rosPackageLaunch=PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'))
    gazeboLaunch=IncludeLaunchDescription(gazebo_rosPackageLaunch, launch_arguments={'gz_args': ['-r -v4 empty.sdf'], 'on_exit_shutdown': 'true'}.items()) 
    
    spawn_model_node_gazebo=Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', robotXacroName, '-topic', 'robot_description'],
        output='screen'
    )

    # Command-line arguments
    rviz_config_arg = DeclareLaunchArgument("rviz_config", default_value="moveit.rviz")
    db_arg = DeclareLaunchArgument("db", default_value="False")
    ros2_control_hardware_type = DeclareLaunchArgument("ros2_control_hardware_type", default_value="mock_components")

    # Global Sim Time Parameter
    sim_time_param = {"use_sim_time": True}

    # RViz
    rviz_config_path = os.path.join(get_package_share_directory("so101_moveit2_config"), "config", "moveit.rviz")
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_path],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            sim_time_param, # Added sim_time
        ],
    )

    # Static TF
    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "world", "base_link"],
        parameters=[sim_time_param] # Added sim_time
    )

    # Publish TF
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description, sim_time_param], # Added sim_time
    )

    # Controller Spawners (Notice the removal of ros2_control_node)
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    so101_arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_trajectory_controller", "-c", "/controller_manager"],
    )

    so101_gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_action_controller", "-c", "/controller_manager"],
    )
    
    # Move_group node
    config_dict = moveit_config.to_dict()
    config_dict.update(sim_time_param) # Added sim_time
    
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[config_dict],
        arguments=["--ros-args", "--log-level", "info"],
    )
    
    # Corrected Event Handlers: Wait for the robot to spawn in Gazebo before starting controllers
    delay_joint_state_broadcaster_spawner = RegisterEventHandler(
        onprocess_exit(
            target_action=spawn_model_node_gazebo, # Trigger when spawn finishes
            on_exit=[joint_state_broadcaster_spawner],
        )
    )
    
    # Controller spawners DO exit once the controller is loaded, so this logic is fine
    delay_so101_arm_controller_spawner = RegisterEventHandler(
        onprocess_exit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[so101_arm_controller_spawner],
        )
    )
    
    delay_so101_gripper_controller_spawner = RegisterEventHandler(
        onprocess_exit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[so101_gripper_controller_spawner],
        )
    )
    
    bridge_params=os.path.join(
        get_package_share_directory(namePackage),
        'parameters',
        'bridge_param.yaml'
    )

    start_gazebo_ros_bridge_cmd=Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={bridge_params}',
        ],
        output='screen'
    )

    return LaunchDescription(
        [
            gazeboLaunch,
            spawn_model_node_gazebo,
            rviz_config_arg,
            db_arg,
            ros2_control_hardware_type,
            rviz_node,
            static_tf_node,
            robot_state_publisher,
            move_group_node,
            delay_joint_state_broadcaster_spawner,
            delay_so101_arm_controller_spawner,
            delay_so101_gripper_controller_spawner,
            start_gazebo_ros_bridge_cmd,
        ]
    )