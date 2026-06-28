import argparse
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta

# 设置日志配置为INFO级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validate_video_file(filepath):
    """用 ffprobe 快速检测视频文件是否可读（仅读头部，不解码）。
    返回 (is_valid, error_message)
    """
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    # 即使头部可读，也校验 duration 是否大于 0
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return False, f"ffprobe returned non-numeric duration: {result.stdout.strip()}"
    if duration <= 0:
        return False, f"Duration is {duration}s (file may contain no valid frames)"
    return True, None


def extract_date_from_filename(file_name):
    match = re.search(r"(\d{8})", file_name)
    if match:
        return match.group(1)
    return None

def extract_start_time_from_filename(file_name):
    match = re.search(r"(\d{14})", file_name)
    if match:
        return match.group(1)
    return None

def merge_videos(input_folder, output_folder, delete_old_videos, delete_source, before_date):
    input_folder = input_folder.encode('gbk').decode('gb2312')
    logging.info(f"Starting video merging process..., input is {input_folder}")
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.info(f"Created output directory at {output_folder}")

    # 存储视频文件的字典，键为文件名最前面的日期，值为视频文件路径列表
    videos_dict = {}
    exist_videos_dict = {}
    for file_name in os.listdir(output_folder):
        if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov')):  # 检查文件扩展名
            date_prefix = extract_date_from_filename(file_name)
            if date_prefix:
                logging.info(f"Found exist video {file_name} with date prefix {date_prefix}")
                video_path = os.path.join(output_folder, file_name)
                if date_prefix in exist_videos_dict:
                    exist_videos_dict[date_prefix].append(video_path)
                else:
                    exist_videos_dict[date_prefix] = [video_path]

    # 从输出路径中最近的日期开始合并新的文件
    max_date = None  # 用于存储最大日期的键
    for key in exist_videos_dict:
        try:
            # 尝试将键解析为日期
            current_file_date = datetime.strptime(key, "%Y%m%d")
            # 更新最大日期
            if max_date is None or current_file_date > max_date:
                max_date = current_file_date
        except ValueError:
            logging.warning(f"Invalid date format in key: {key}")

    if max_date:
        max_date_str = max_date.strftime("%Y%m%d")
        print(f"最大日期是: {max_date_str}")
    else:
        print("未找到有效的日期键。")

    if delete_old_videos:
        # 删除一周之前的视频
        logging.info("Cleaning up videos older than two weeks...")
        weeks_ago = datetime.now() - timedelta(weeks=1)
        for file_name in os.listdir(output_folder):
            if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov')):  # delete-old-videos section
                try:
                    old_file_date = extract_date_from_filename(file_name)
                    if old_file_date:
                        video_date = datetime.strptime(old_file_date, "%Y%m%d")
                        if video_date < weeks_ago:
                            video_path = os.path.join(output_folder, file_name)
                            os.remove(video_path)
                            logging.info(f"Deleted old video: {video_path}")
                except ValueError:
                    logging.warning(f"Invalid date format in file name: {file_name}")

    # 收集需要合并的小视频列表
    for file_name in os.listdir(input_folder):
        if file_name.endswith(('.mp4', '.avi', '.mov')):  # 检查文件扩展名
            key = extract_date_from_filename(file_name)
            if key:
                # 跳过 >= before_date 的视频
                if key >= before_date:
                    logging.info(f"Skipping {key} video {file_name} (before cutoff: {before_date})")
                    continue
                current_file_date = datetime.strptime(key, "%Y%m%d")
                if key not in exist_videos_dict and ( max_date is None or current_file_date > max_date):
                    video_path = os.path.join(input_folder, file_name)
                    logging.info(f"Found video {file_name} with prefix {key}")
                    if key in videos_dict:
                        videos_dict[key].append(video_path)
                    else:
                        videos_dict[key] = [video_path]
                else:
                    print('Skip merge video ', file_name, 'due to already exist. ')

    # 对每个日期的视频列表按时间戳排序
    for key, video_paths in videos_dict.items():
        # 提取文件名中的开始时间戳并排序
        sorted_video_paths = sorted(video_paths, key=lambda x: extract_start_time_from_filename(os.path.basename(x)))
        videos_dict[key] = sorted_video_paths
        logging.info(f"Sorted video paths for date {key}: {sorted_video_paths}")

    # 合并视频
    for key, video_paths in videos_dict.items():
        logging.info(f"Merging videos with prefix {key}...")
        # 创建一个临时文件列表（先用 ffprobe 过滤损坏文件）
        valid_paths = []
        invalid_paths = []
        for video_path in video_paths:
            is_valid, err_msg = validate_video_file(video_path)
            if is_valid:
                valid_paths.append(video_path)
            else:
                invalid_paths.append((video_path, err_msg))
                logging.warning(f"Corrupt file excluded: {video_path}")
                logging.warning(f"  ffprobe: {err_msg}")

        if invalid_paths:
            logging.warning(f"Excluded {len(invalid_paths)} corrupt file(s) for {key}, "
                            f"{len(valid_paths)} valid file(s) remaining")

        if not valid_paths:
            logging.error(f"No valid video files for {key}, skipping merge")
            continue

        tmp_file = os.path.join(output_folder, f"tmp_{key}.txt")
        with open(tmp_file, 'w') as f:
            for video_path in valid_paths:
                f.write(f"file '{video_path}'\n")

        # 使用ffmpeg合并视频（先输出到临时文件，成功后再改名）
        output_path = os.path.join(output_folder, f"{key}_merged.mkv")
        tmp_output_path = os.path.join(output_folder, f"{key}_merged.mkv.tmp")
        merge_command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", tmp_file,
            "-c", "copy",
            "-fflags", "+genpts",
            "-avoid_negative_ts", "make_zero",
            "-f", "matroska",
            "-y",
            tmp_output_path
        ]
        result = subprocess.run(merge_command, capture_output=True, text=True)

        # 检查 stderr 中是否有跳文件 / 文件损坏等关键错误
        # ffmpeg 的 concat demuxer 在跳过损坏文件后仍可能返回 0，需要自行判断
        stderr_output = result.stderr if result.stderr else ""
        critical_errors = [
            "Impossible to open",
            "moov atom not found",
            "Error during demuxing",
            "Invalid data found when processing input",
        ]
        has_critical_error = any(err in stderr_output for err in critical_errors)

        # 只合并成功时才打印消息并清理临时文件
        if result.returncode == 0 and not has_critical_error:
            # 原子改名：避免中断导致残留不完整文件
            os.rename(tmp_output_path, output_path)
            logging.info(f"Merged video saved to {output_path}")
            os.remove(tmp_file)
            logging.info(f"Temporary file {tmp_file} deleted")

            # 合并成功后删除源文件
            if delete_source:
                for video_path in video_paths:
                    os.remove(video_path)
                    logging.info(f"Deleted source file: {video_path}")
        else:
            if has_critical_error:
                logging.error(f"FFmpeg merge may be incomplete for {key}: critical errors detected in stderr")
                logging.error(f"FFmpeg stderr: {stderr_output}")
            else:
                logging.error(f"FFmpeg merge failed for {key}, return code: {result.returncode}")
                logging.error(f"FFmpeg stderr: {stderr_output}")
            if os.path.exists(tmp_output_path):
                os.remove(tmp_output_path)
            logging.error(f"Temporary file retained: {tmp_file}")

    logging.info("Video merging process completed.")

def main():
    parser = argparse.ArgumentParser(description="Merge videos with the same prefix using ffmpeg.")
    parser.add_argument("--input", type=str, help="Input folder path containing videos", required=True)
    parser.add_argument("--output", type=str, help="Output folder path for merged videos", required=True)
    parser.add_argument("--delete-old-videos", action="store_true", help="Delete videos older than one week (default: False)")
    parser.add_argument("--delete-source", action="store_true",
                        help="Delete source video files after successful merge (default: False)")
    parser.add_argument("--before-date", type=str,
                        help="Only merge videos before this date (YYYYMMDD, default: yesterday)")
    args = parser.parse_args()

    before_date = args.before_date if args.before_date else (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    merge_videos(args.input, args.output, args.delete_old_videos, args.delete_source, before_date)

if __name__ == "__main__":
    main()