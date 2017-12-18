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
RUN pip install pillow

# Install picamera
RUN pip install picamera
RUN pip install --user picamera

# Add local volume for code
ADD . /src