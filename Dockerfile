FROM resin/rpi-raspbian

# Install dependencies
RUN apt-get update && apt-get install -y \
    vim \
    python3 \
    python-pip \
    python-pil \
    libjpeg8 \
    libjpeg8-dev \
    libfreetype6 \
    libfreetype6-dev \
    zlib1g \
    python-imaging \
    python-picamera

# Install pip modules
RUN pip3 install pillow

# Install picamera
RUN pip3 install picamera
RUN pip3 install --user picamera

# Add local volume for code
ADD . /src