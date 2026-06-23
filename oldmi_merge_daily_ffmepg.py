import os
import shutil
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import argparse


def merge_videos(input_path, output_path, delete_old_videos, delete_source, before_date):
    # 检查输出路径是否存在，如果不存在则创建
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 按日期分组存储视频文件
    daily_videos = defaultdict(list)
    daily_source_folders = defaultdict(list)  # date_str -> [folder_path, ...]

    # 遍历输入路径中的所有文件夹
    for folder_name in os.listdir(input_path):
        folder_path = os.path.join(input_path, folder_name)

        # 确保是文件夹
        if os.path.isdir(folder_path):
            try:
                # 解析文件夹名称，提取日期和小时
                folder_date = datetime.strptime(folder_name, "%Y%m%d%H")
                date_str = folder_date.strftime("%Y%m%d")  # 日期字符串，用于分组
            except ValueError:
                # 如果文件夹名称不符合格式，跳过
                print(f"Skipping invalid folder name: {folder_name}")
                continue

            # 跳过 >= before_date 的视频
            if date_str >= before_date:
                print(f"Skipping {date_str} folder: {folder_name} (before cutoff: {before_date})")
                continue

            # 获取该文件夹内所有视频文件
            video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                           f.lower().endswith(('.mp4', '.avi', '.mov'))]

            # 提取时间戳并排序
            video_files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x).split('_')[-1])[0]))

            if not video_files:
                print(f"No video files found in folder: {folder_name}")
                continue

            # 将视频文件添加到对应日期的列表中
            daily_videos[date_str].extend(video_files)
            daily_source_folders[date_str].append(folder_path)

    # 如果启用删除旧视频功能，删除输出目录中一周前的合并文件
    if delete_old_videos:
        weeks_ago = datetime.now() - timedelta(weeks=1)
        for file_name in os.listdir(output_path):
            if file_name.endswith(('.mp4', '.avi', '.mov')):
                try:
                    # 从文件名中提取日期前缀（格式：{YYYYMMDD}_daily_merged.mp4）
                    file_date_str = file_name[:8]
                    file_date = datetime.strptime(file_date_str, "%Y%m%d")
                    if file_date < weeks_ago:
                        file_path = os.path.join(output_path, file_name)
                        os.remove(file_path)
                        print(f"Deleted old video: {file_path}")
                except (ValueError, IndexError):
                    print(f"Skipping file with invalid date format: {file_name}")

    # 合并每天的视频
    for date, video_list in daily_videos.items():
        daily_output_file = os.path.join(output_path, f"{date}_daily_merged.mp4")

        # 检查是否已经合并过
        if os.path.exists(daily_output_file):
            print(f"Skipping already merged file: {daily_output_file}")
            continue

        # 创建 FFmpeg 的输入文件列表
        daily_filelist_path = os.path.join(output_path, "daily_filelist.txt")
        with open(daily_filelist_path, "w") as filelist:
            for video_file in video_list:
                filelist.write(f"file '{video_file}'\n")

        merge_command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", daily_filelist_path,  # 使用 output_path 下的文件列表
            "-c:v", "copy", 
            "-c:a", "aac",
            "-b:a", "64k",
            "-ar", "16000",
            "-movflags","+faststart",
            daily_output_file
        ]

        # 调用 FFmpeg 合并视频
        result = subprocess.run(merge_command)

        # 只合并成功时才打印消息并清理临时文件
        if result.returncode == 0:
            print(f"Merged daily video saved to: {daily_output_file}")
            os.remove(daily_filelist_path)

            # 合并成功后删除源目录
            if delete_source:
                for folder_path in daily_source_folders[date]:
                    shutil.rmtree(folder_path)
                    print(f"Deleted source folder: {folder_path}")
        else:
            print(f"FFmpeg merge failed for {date}, return code: {result.returncode}")
            print(f"Temporary file retained: {daily_filelist_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge hourly video files into daily video files.")
    parser.add_argument("--input", type=str, help="Path to the input folder containing hourly video folders.")
    parser.add_argument("--output", type=str,
                        help="Path to the output folder where daily merged videos will be saved.")
    parser.add_argument("--delete-old-videos", action="store_true",
                        help="Delete videos older than one week from output folder (default: False)")
    parser.add_argument("--delete-source", action="store_true",
                        help="Delete source hour folders after successful merge (default: False)")
    parser.add_argument("--before-date", type=str,
                        help="Only merge videos before this date (YYYYMMDD, default: yesterday)")
    args = parser.parse_args()

    # 默认值：昨天
    before_date = args.before_date if args.before_date else (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    merge_videos(args.input, args.output, args.delete_old_videos, args.delete_source, before_date)