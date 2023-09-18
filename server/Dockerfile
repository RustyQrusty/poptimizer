# For more information, please refer to https://aka.ms/vscode-docker-python
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=":/home/root" \
    PATH="/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    NVIDIA_VISIBLE_DEVICES="all" \
    NVIDIA_DRIVER_CAPABILITIES="compute,utility" \
    LD_LIBRARY_PATH="/usr/local/nvidia/lib:/usr/local/nvidia/lib64" \
    PYTORCH_VERSION="v2.0.0" \
    CUBLAS_WORKSPACE_CONFIG=":4096:8"

RUN apt-get update && apt-get install sudo docker.io -y

COPY . /home/root
WORKDIR /home/root

RUN pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt