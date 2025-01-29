from typing import List, Dict, Tuple
import json
import subprocess
import numpy as np
from dataclasses import dataclass
from enum import Enum
import os


class ActionType(Enum):
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    ACCELERATE = "accelerate"
    BRAKE = "brake"
    OVERTAKE_LEFT = "overtake_left"
    OVERTAKE_RIGHT = "overtake_right"
    SUDDEN_LEFT = "sudden_left"
    SUDDEN_RIGHT = "sudden_right"


@dataclass
class DetectionConfig:
    # Turn detection parameters
    turn_threshold: float = 0.3
    # Controls how easily turns are detected
    # INCREASE: Requires stronger rotational movement to detect turns (more selective)
    # DECREASE: Detects more subtle turning movements (more sensitive)
    # Unit: radians/second of rotation around z-axis

    min_turn_duration: float = 0.5
    # Minimum time a turn must last to be counted
    # INCREASE: Only detects longer, more deliberate turns
    # DECREASE: Allows detection of quicker turns
    # Unit: seconds

    min_turn_angle: float = 10
    # Minimum angle change required to count as a turn
    # INCREASE: Only detects more complete turns
    # DECREASE: Detects smaller turning movements
    # Unit: degrees

    # Acceleration detection parameters
    accel_threshold: float = 2.0
    # Controls how easily acceleration is detected
    # INCREASE: Requires stronger forward acceleration (more selective)
    # DECREASE: Detects more subtle acceleration (more sensitive)
    # Unit: meters/second²

    brake_threshold: float = -1.5
    # Controls how easily braking is detected
    # INCREASE (toward 0): Requires lighter braking to detect (more sensitive)
    # DECREASE (more negative): Requires harder braking to detect (more selective)
    # Unit: meters/second²

    min_accel_duration: float = 0.3
    # Minimum time acceleration/braking must last
    # INCREASE: Only detects longer acceleration/braking events
    # DECREASE: Detects shorter acceleration/braking events
    # Unit: seconds

    min_speed_change: float = 2.0
    # Minimum speed change required for acceleration/braking event
    # INCREASE: Requires larger speed changes (more selective)
    # DECREASE: Detects smaller speed changes (more sensitive)
    # Unit: meters/second

    # Overtake detection parameters
    overtake_turn_window: float = 2.0
    # Time window to look for turns after acceleration starts
    # INCREASE: Allows more time between turn and acceleration in overtake
    # DECREASE: Requires turn and acceleration to be closer together
    # Unit: seconds

    overtake_accel_window: float = 3.0
    # Time window to look for acceleration after turn starts
    # INCREASE: Allows more time to complete overtaking maneuver
    # DECREASE: Requires quicker overtaking maneuvers
    # Unit: seconds

    min_overtake_duration: float = 1.0
    # Minimum duration for complete overtaking maneuver
    # INCREASE: Only detects longer overtaking sequences
    # DECREASE: Allows detection of quicker overtakes
    # Unit: seconds

    # Sudden movement detection parameters
    sudden_turn_threshold: float = 0.5
    # Threshold for detecting sudden/sharp turns
    # INCREASE: Requires more aggressive turns to be considered "sudden"
    # DECREASE: More turns will be classified as "sudden"
    # Unit: radians/second

    sudden_accel_threshold: float = 3.0
    # Threshold for detecting sudden acceleration/braking
    # INCREASE: Requires more aggressive acceleration to be "sudden"
    # DECREASE: More acceleration events will be classified as "sudden"
    # Unit: meters/second²

    max_sudden_duration: float = 1.0
    # Maximum duration for sudden movements
    # INCREASE: Allows longer movements to be considered "sudden"
    # DECREASE: Only very quick movements are considered "sudden"
    # Unit: seconds


class ActionDetector:
    def __init__(
        self,
        video_path: str,
        gyro_data: Dict,
        accl_data: Dict,
        config: DetectionConfig = None,
    ):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.video_path = video_path
        self.config = config or DetectionConfig()

        # Convert timestamps to seconds and normalize data
        self.gyro_samples = self._preprocess_data(gyro_data["samples"])
        self.accl_samples = self._preprocess_data(accl_data["samples"])

    def _preprocess_data(self, samples: List[Dict]) -> List[Dict]:
        """Preprocess and normalize the sensor data"""
        processed = []
        for sample in samples:
            processed_sample = {
                "time": sample["cts"] / 1000.0,
                "value": np.array(sample["value"]),
                "date": sample["date"],
            }
            processed.append(processed_sample)

        # Apply smoothing
        window_size = 5
        smoothed = []
        for i in range(len(processed)):
            start = max(0, i - window_size // 2)
            end = min(len(processed), i + window_size // 2 + 1)
            window = processed[start:end]

            smoothed_sample = processed[i].copy()
            smoothed_sample["value"] = np.mean([s["value"] for s in window], axis=0)
            smoothed.append(smoothed_sample)

        return smoothed

    def _integrate_signal(
        self, samples: List[Dict], start_idx: int, end_idx: int, axis: int
    ) -> float:
        """Integrate signal between two indices using numpy's trapezoid function"""
        if start_idx >= end_idx:
            return 0.0

        times = [s["time"] for s in samples[start_idx : end_idx + 1]]
        values = [s["value"][axis] for s in samples[start_idx : end_idx + 1]]
        return np.trapezoid(values, times)  # Updated from trapz to trapezoid

    def detect_turns(self) -> List[Tuple[float, float, str]]:
        """Detect turning movements using gyroscope z-axis"""
        turns = []
        start_idx = None
        current_type = None

        for i in range(len(self.gyro_samples)):
            gyro_z = self.gyro_samples[i]["value"][2]

            if abs(gyro_z) > self.config.turn_threshold:
                turn_type = (
                    ActionType.TURN_RIGHT.value
                    if gyro_z > 0
                    else ActionType.TURN_LEFT.value
                )

                if abs(gyro_z) > self.config.sudden_turn_threshold:
                    turn_type = f"sudden_{turn_type.split('_')[1]}"

                if start_idx is None:
                    start_idx = i
                    current_type = turn_type
            elif start_idx is not None:
                duration = (
                    self.gyro_samples[i]["time"] - self.gyro_samples[start_idx]["time"]
                )
                integrated_angle = abs(
                    self._integrate_signal(self.gyro_samples, start_idx, i, 2)
                )

                if (
                    duration >= self.config.min_turn_duration
                    and integrated_angle >= np.radians(self.config.min_turn_angle)
                ):
                    turns.append(
                        (
                            self.gyro_samples[start_idx]["time"],
                            self.gyro_samples[i]["time"],
                            current_type,
                        )
                    )

                start_idx = None
                current_type = None

        return turns

    def detect_acceleration_events(self) -> List[Tuple[float, float, str]]:
        """Detect acceleration and braking events using accelerometer y-axis"""
        events = []
        start_idx = None
        current_type = None

        for i in range(len(self.accl_samples)):
            accl_y = self.accl_samples[i]["value"][1]

            if accl_y > self.config.accel_threshold:
                event_type = ActionType.ACCELERATE.value
                if accl_y > self.config.sudden_accel_threshold:
                    event_type = "sudden_accelerate"
                if start_idx is None:
                    start_idx = i
                    current_type = event_type
            elif accl_y < self.config.brake_threshold:
                event_type = ActionType.BRAKE.value
                if accl_y < -self.config.sudden_accel_threshold:
                    event_type = "sudden_brake"
                if start_idx is None:
                    start_idx = i
                    current_type = event_type
            elif start_idx is not None:
                duration = (
                    self.accl_samples[i]["time"] - self.accl_samples[start_idx]["time"]
                )
                speed_change = abs(
                    self._integrate_signal(self.accl_samples, start_idx, i, 1)
                )

                if (
                    duration >= self.config.min_accel_duration
                    and speed_change >= self.config.min_speed_change
                ):
                    events.append(
                        (
                            self.accl_samples[start_idx]["time"],
                            self.accl_samples[i]["time"],
                            current_type,
                        )
                    )

                start_idx = None
                current_type = None

        return events

    def detect_overtakes(self) -> List[Tuple[float, float, str]]:
        """Detect overtaking maneuvers by combining turns and acceleration"""
        overtakes = []
        turns = self.detect_turns()
        accelerations = self.detect_acceleration_events()

        for turn_start, turn_end, turn_type in turns:
            if not turn_type.startswith("sudden"):
                for accel_start, accel_end, accel_type in accelerations:
                    if (
                        accel_type == ActionType.ACCELERATE.value
                        and abs(accel_start - turn_end)
                        <= self.config.overtake_turn_window
                    ):

                        overtake_type = (
                            ActionType.OVERTAKE_RIGHT.value
                            if "right" in turn_type
                            else ActionType.OVERTAKE_LEFT.value
                        )

                        overtakes.append(
                            (
                                min(turn_start, accel_start),
                                max(turn_end, accel_end),
                                overtake_type,
                            )
                        )

        return overtakes

    def generate_clips(self, output_dir: str):
        """Generate video clips for all detected events"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        all_events = (
            self.detect_turns()
            # + self.detect_acceleration_events()
            # + self.detect_overtakes()
        )

        # Sort events by start time and remove overlapping events
        all_events.sort(key=lambda x: x[0])
        filtered_events = []
        last_end = 0

        for event in all_events:
            if event[0] >= last_end:
                filtered_events.append(event)
                last_end = event[1]

        print(f"We have found {len(filtered_events)} number of events")

        for idx, (start, end, event_type) in enumerate(filtered_events):
            output_file = f"{output_dir}/{event_type}_{idx}.mp4"
            duration = end - start

            # Add padding to the clip
            padded_start = max(0, start - 0.5)
            padded_end = end + 0.5

            # Try different video encoding options
            encoding_options = [
                ["-c:v", "h264_nvenc"],  # Try NVIDIA GPU encoding
                ["-c:v", "libx264"],  # Try CPU encoding first
                ["-c:v", "h264_amf"],  # Try AMD GPU encoding
                ["-c:v", "h264_qsv"],  # Try Intel GPU encoding
            ]

            success = False
            # for encode_opt in encoding_options:
            command = (
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    self.video_path,
                    "-ss",
                    f"{padded_start:.3f}",
                    "-to",
                    f"{padded_end:.3f}",
                    "-c:v",
                    "h264_nvenc",
                ]
                # + encode_opt
                + ["-preset", "fast", output_file]
            )

            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    text=True,
                )
                print(f"Generated: {output_file} ({duration:.1f}s {event_type})")
                success = True
            except subprocess.CalledProcessError as e:
                print(f"Encoder {encode_opt[1]} failed: {e.stderr}")
                continue

            if not success:
                print(
                    f"Failed to generate clip {output_file} with all available encoders"
                )


if __name__ == "__main__":
    # Load sensor data
    with open("./data/GH019806/GYRO.json") as f:
        gyro_data = json.load(f)
    with open("./data/GH019806/ACCL.json") as f:
        accl_data = json.load(f)

    video_path = (
        "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Front_view/GH019806.MP4"
    )

    # Create custom configuration with more sensitive thresholds
    config = DetectionConfig(
        # Turn detection
        turn_threshold=0.1,
        min_turn_duration=0.4,
        min_turn_angle=5,
        # Acceleration detection
        accel_threshold=0.5,
        brake_threshold=-1.0,
        min_accel_duration=0.2,
        min_speed_change=1.5,
        # Overtake detection
        overtake_turn_window=10,
        overtake_accel_window=10,
        min_overtake_duration=1.0,
        # Sudden movement detection
        sudden_turn_threshold=0.4,
        sudden_accel_threshold=2.0,
        max_sudden_duration=0.5,
    )

    try:
        detector = ActionDetector(video_path, gyro_data, accl_data, config)
        detector.generate_clips("output_clips")
    except Exception as e:
        print(f"Error: {str(e)}")
