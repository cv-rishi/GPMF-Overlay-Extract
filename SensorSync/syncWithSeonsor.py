import json
import subprocess
from datetime import datetime, timedelta
import os


# Load telemetry data from SHUT.json
def load_shut_data(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data["samples"]


# Find the earliest common time across videos
def find_common_time(data_list):
    timestamps = [
        datetime.fromisoformat(sample["date"][:-1])
        for data in data_list
        for sample in data
    ]
    common_start = min(timestamps)
    return common_start


# Calculate offsets for each video
def calculate_offsets(data_list, common_start):
    offsets = []
    for data in data_list:
        first_time = datetime.fromisoformat(data[0]["date"][:-1])
        offset = (first_time - common_start).total_seconds()
        offsets.append(offset)
    return offsets


# Sync videos using ffmpeg
def sync_videos(video_paths, offsets, output_path):
    temp_files = []
    for i, (video, offset) in enumerate(zip(video_paths, offsets)):
        temp_file = f"temp_video_{i}.mp4"
        temp_files.append(temp_file)
        trim_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video,
            "-ss",
            str(max(0, offset)),  # Skip to offset
            "-c",
            "copy",
            temp_file,
        ]
        print(f"Running command to trim {video}: {trim_cmd}")
        subprocess.run(trim_cmd)

    # Dynamically generate the layout and inputs for the grid
    input_flags = []
    layout_str = ""
    num_videos = len(video_paths)

    # Construct the input flags (separate '-i' for each file)
    for i in range(num_videos):
        input_flags.append("-i")
        input_flags.append(temp_files[i])

    # Generate layout based on the number of videos
    if num_videos == 2:
        layout_str = "xstack=inputs=2:layout=0_0|w0_0"
    elif num_videos == 3:
        layout_str = "xstack=inputs=3:layout=0_0|w0_0|0_h0"
    elif num_videos == 4:
        layout_str = "xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0"
    else:
        print("Error: Unsupported number of videos.")
        return

    # Combine videos using ffmpeg
    combine_cmd = (
        [
            "ffmpeg",
            "-y",
        ]
        + input_flags
        + [
            "-filter_complex",
            layout_str,
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            output_path,
        ]
    )

    print(f"Running command to combine videos: {' '.join(combine_cmd)}")
    subprocess.run(combine_cmd)

    # Clean up temp files
    for file in temp_files:
        os.remove(file)


# Main function
def main():
    # File paths
    shut_files = ["front_View.json", "helmet_view.json"]
    video_files = [
        "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Front_view/GH019806.MP4",
        "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Helmet_view/GH019814.MP4",
    ]
    output_file = "synced_video.mp4"

    # Load SHUT data
    data_list = [load_shut_data(file) for file in shut_files]

    # Find common start time
    common_start = find_common_time(data_list)

    # Calculate offsets
    offsets = calculate_offsets(data_list, common_start)

    # Sync videos
    sync_videos(video_files, offsets, output_file)
    print(f"Synced video saved as {output_file}")


if __name__ == "__main__":
    main()
