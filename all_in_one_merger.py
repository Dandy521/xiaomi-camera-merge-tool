import argparse
import logging
from datetime import datetime, timedelta
from merge_daily_ffmepg import merge_videos as merge_new_cam_videos
from oldmi_merge_daily_ffmepg import merge_videos as merge_old_cam_videos

# 设置日志配置为INFO级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    parser = argparse.ArgumentParser(description="Merge videos with the same prefix using ffmpeg.")
    parser.add_argument("--input", type=str, help="Input folder path containing videos", required=True)
    parser.add_argument("--output", type=str, help="Output folder path for merged videos", required=True)
    parser.add_argument("--delete-old-videos", action="store_true",
                        help="Delete videos older than one week from output folder (default: False)")
    parser.add_argument("--delete-source", action="store_true",
                        help="Delete source video files/folders after successful merge (default: False)")
    parser.add_argument("--before-date", type=str,
                        help="Only merge videos before this date (YYYYMMDD, default: yesterday)")
    parser.add_argument("--old-cam", action="store_true",
                        help="Use old camera folder structure (YYYYMMDDHH subfolders, default: False)")
    args = parser.parse_args()

    # 默认值：昨天
    before_date = args.before_date if args.before_date else (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    if args.old_cam:
        logging.info("start merging with old camera.")
        merge_old_cam_videos(args.input, args.output, args.delete_old_videos, args.delete_source, before_date)
    else:
        logging.info("start merging with new camera.")
        merge_new_cam_videos(args.input, args.output, args.delete_old_videos, args.delete_source, before_date)


if __name__ == "__main__":
    main()
