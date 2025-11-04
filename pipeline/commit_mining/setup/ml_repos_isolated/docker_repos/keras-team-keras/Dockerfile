# Dockerfile template for individual ML repository analysis
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
    notebook \
    scalene

# Create working directory
WORKDIR /workspace

# Copy single repository
COPY successful_clones/keras-team_keras/ /workspace/repo/

# Copy dependency installation script
COPY install_single_repo_dependencies.py /workspace/

# Install repository dependencies
RUN python /workspace/install_single_repo_dependencies.py --repo-dir /workspace/repo --output /workspace/dependency_install_report.json

# Set up Jupyter with repository-specific port
EXPOSE 8890
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8890", "--no-browser", "--allow-root", "--notebook-dir=/workspace/repo"]
