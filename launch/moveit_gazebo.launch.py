import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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
    pathModelFile=os.path.join(get_package_share_directory(namePackage),modelFileRelativePath)
    
    robotDescription=xacro.process_file(pathModelFile).toxml()
    
    gazebo_rosPackageLaunch=PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'))
    gazeboLaunch=IncludeLaunchDescription(gazebo_rosPackageLaunch, launch_arguments={'gz_args': ['-r -v4 empty.sdf'], 'on_exit_shutdown': 'true'}.items())
    
    robot_description_file_path = os.path.join(
        get_package_share_directory("so101_moveit2_config"),
        "config",
        "so101_new_calib.urdf.xacro",
    )
    
    joint_controller_file_path = os.path.join(
        get_package_share_directory("so101_moveit2_config"),
        "config",
        "trajectory_controller.yaml",
    )
    
    # Spawn the robot in Gazebo
    spawn_model_node_gazebo=Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', robotXacroName,
            '-topic', 'robot_description',
            '-z', '0.1',
        ],
        output='screen'
    )
    

    # Command-line arguments
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value="moveit.rviz",
        description="RViz configuration file",
    )

    db_arg = DeclareLaunchArgument(
        "db", default_value="False", description="Database flag"
    )

    ros2_control_hardware_type = DeclareLaunchArgument(
        "ros2_control_hardware_type",
        default_value="mock_components",
        description="ROS 2 control hardware interface type to use for the launch file -- possible values: [mock_components, isaac]",
    )

    moveit_config = (
        MoveItConfigsBuilder(robot_name="so101_new_calib", package_name="so101_moveit2_config")
        .robot_description(
            file_path="config/so101_new_calib.urdf.xacro",
            mappings={
                "ros2_control_hardware_type": LaunchConfiguration(
                    "ros2_control_hardware_type"
                )
            },
        )
        .robot_description_semantic(file_path="config/so101_new_calib.srdf")
        .planning_scene_monitor(
            publish_robot_description=True, publish_robot_description_semantic=True
        )
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(
            pipelines=["ompl", "chomp", "pilz_industrial_motion_planner", "stomp"]
        )
        .to_moveit_configs()
    )

    # Start the actual move_group node/action server
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()],
        arguments=["--ros-args", "--log-level", "info"],
    )

    # RViz
    rviz_base = LaunchConfiguration("rviz_config")
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("so101_moveit2_config"), "launch", rviz_base]
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
    )

    # Static TF
    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "world", "base_link"],
    )

    # Publish TF
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description],
    )

    # ros2_control using FakeSystem as hardware
    ros2_controllers_path = os.path.join(
        get_package_share_directory("so101_moveit2_config"),
        "config",
        "ros2_controllers.yaml",
    )
    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[ros2_controllers_path],
        remappings=[
            ("/controller_manager/robot_description", "/robot_description"),
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
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

    # Warehouse mongodb server
    db_config = LaunchConfiguration("db")
    mongodb_server_node = Node(
        package="warehouse_ros_mongo",
        executable="mongo_wrapper_ros.py",
        parameters=[
            {"warehouse_port": 33829},
            {"warehouse_host": "localhost"},
            {"warehouse_plugin": "warehouse_ros_mongo::MongoDatabaseConnection"},
        ],
        output="screen",
        condition=IfCondition(db_config),
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
            ros2_control_node,
            joint_state_broadcaster_spawner,
            so101_arm_controller_spawner,
            so101_gripper_controller_spawner,
            mongodb_server_node,
        ]
    )
