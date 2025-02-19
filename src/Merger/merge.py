from pathlib import Path
import subprocess
import os


def get_sorted_video_files(
    directory: Path, extensions=(".MP4", ".mov", ".avi", ".mkv")
):
    """
    Lists files in the directory, filters by extension, and sorts them by modified time.
    The input 'directory' should be a Path object (e.g. PosixPath).

    Returns a list of Path objects.
    """
    ext_set = {ext.upper() for ext in extensions}

    files = [p for p in directory.iterdir() if p.suffix.upper() in ext_set]

    files.sort(key=lambda p: p.stat().st_mtime)
    return files


class VideoMerger:
    def __init__(self, temp_file_path="filelist.txt"):
        """
        Initialize the VideoMerger class
        Args:
            temp_file_path: Path to the temporary file list for ffmpeg
        """
        self.temp_file_path = temp_file_path

    def create_ffmpeg_file_list(self, video_files):
        """
        Creates a file list for FFmpeg concat demuxer.
        Each line will be of the format: file 'path/to/video.mp4'
        Args:
            video_files: List of video file paths
        Returns:
            Path to the created file list
        """
        with open(self.temp_file_path, "w") as f:
            for video in video_files:
                f.write(f"file '{str(video)}'\n")
        return self.temp_file_path

    def merge_videos(self, video_files, output_filename):
        """
        Merges multiple video files into a single output file
        Args:
            video_files: List of video file paths to merge
            output_filename: Path to the output merged video file
        Returns:
            True if merge was successful, False otherwise
        """
        if not video_files:
            print("No video files provided for merging")
            return False

        # Create the ffmpeg file list
        file_list = self.create_ffmpeg_file_list(video_files)

        # Build the ffmpeg command
        command = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            file_list,
            "-c",
            "copy",
            str(output_filename),
        ]

        # Execute the command
        try:
            subprocess.run(command, check=True)
            print(f"Successfully merged videos into {output_filename}")
            # Clean up the temporary file list
            os.remove(file_list)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error during merging videos with FFmpeg: {e}")
            return False

    def merge_camera_videos(self, trimmed_video, additional_videos, output_path):
        """
        Merges a trimmed video with additional videos from the same camera
        Args:
            trimmed_video: Path to the trimmed video
            additional_videos: List of paths to additional videos to append
            output_path: Path to save the merged video
        Returns:
            Path to the merged video if successful, None otherwise
        """
        # Ensure trimmed_video is first in the list
        all_videos = [trimmed_video]
        all_videos.extend(additional_videos)

        print(f"Merging videos in the following order:")
        for idx, video in enumerate(all_videos):
            print(f"{idx+1}. {video}")

        # Create output directory if it doesn't exist
        output_dir = Path(output_path).parent
        os.makedirs(output_dir, exist_ok=True)

        # Perform the merge
        success = self.merge_videos(all_videos, output_path)
        if success:
            return Path(output_path)
        return None
