FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

RUN apt-get update && \
    apt-get install --no-install-recommends -y python3 python3-pip python3-virtualenv && \
    apt-get install --no-install-recommends -y libopencv-dev python3-opencv && \
    rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN virtualenv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install packaging

WORKDIR /app
COPY . /app/
RUN python3 prepare.py
RUN mv config.txt.bak config.txt
CMD python3 main.py --host 0.0.0.0 --port 8888
