FROM resin/rpi-raspbian

# Install dependencies
RUN apt-get update && apt-get install -y \
    vim \
    python3 \
    python3-pip \
    python3-pil \
    libjpeg8 \
    libjpeg8-dev \
    libfreetype6 \
    libfreetype6-dev \
    zlib1g \
    python3-picamera \
    fonts-lato

# Add local volume for code
ADD . /src