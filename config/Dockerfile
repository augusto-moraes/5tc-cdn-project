# Base Ubuntu image
FROM ubuntu:24.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    nginx \
    net-tools \
    sudo \
    curl \
    vim \
    python3 \
    python3-pip \
 && apt-get clean

# Expose HTTP port (optional)
EXPOSE 80

# Start a shell by default
CMD ["bash"]
