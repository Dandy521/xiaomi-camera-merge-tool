FROM python:3.12

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone

WORKDIR /app

# 替换为国内镜像源（兼容传统 .list 和新版 .sources 格式）
RUN find /etc/apt -type f \( -name '*.sources' -o -name '*.list' \) \
    -exec sed -i \
        -e 's|http://deb.debian.org|http://mirrors.aliyun.com|g' \
        -e 's|http://security.debian.org|http://mirrors.aliyun.com|g' \
    {} \;

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*


COPY ./*.py /app/


ENV PYTHONUNBUFFERED=1


CMD ["python", "all_in_one_merger.py", "--input", "/app/input", "--output", "/app/output"]
