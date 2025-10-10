# Base Ubuntu image
FROM ubuntu:24.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    net-tools \
    curl \
    wget \
    nano \
    sudo \
    python3 \
    python3-pip \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy server code and initial files
COPY serverweb.py /app/
COPY cache_manager.py /app/
COPY cache /app/cache

# Expose HTTP port (server will bind to this when you run it)
EXPOSE 80

# Start with bash shell (you run server manually)
CMD ["bash"]

