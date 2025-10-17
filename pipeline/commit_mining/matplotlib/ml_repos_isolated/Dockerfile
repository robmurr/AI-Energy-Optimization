
# Dockerfile for ML Repository Analysis
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install base tools for dependency management
RUN pip install --no-cache-dir \
    pip \
    setuptools \
    wheel \
    toml \
    pyyaml \
    requests \
    jupyter \
    notebook

# Create working directory
WORKDIR /workspace

# Copy repositories
COPY successful_clones/ /workspace/repos/

# Copy dependency installation script
COPY install_dependencies.py /workspace/

# Install all repository dependencies
RUN python install_dependencies.py

# Set up Jupyter
EXPOSE 8888
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
