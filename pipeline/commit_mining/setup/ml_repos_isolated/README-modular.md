# Modular ML Repository Analysis

This setup provides individual Docker containers for each ML repository.

## Available Repositories (6 total):

- **AUTOMATIC1111_stable-diffusion-webui**: http://localhost:8888
- **huggingface_transformers**: http://localhost:8889
- **keras-team_keras**: http://localhost:8890
- **pytorch_pytorch**: http://localhost:8891
- **rasbt_mlxtend**: http://localhost:8892
- **tqdm_tqdm**: http://localhost:8893

## Usage:

### Start All Containers:
```bash
# Linux/Mac
./start_all_repos.sh

# Windows
start_all_repos.bat

# Or manually
docker-compose -f docker-compose-modular.yml up --build -d
```

### Start Individual Container:
```bash
docker-compose -f docker-compose-modular.yml up --build -d <service-name>
```

### Stop All Containers:
```bash
docker-compose -f docker-compose-modular.yml down
```

### View Logs:
```bash
docker-compose -f docker-compose-modular.yml logs -f <service-name>
```

## Container Structure:
- Each container runs Jupyter on its own port
- Repository code is mounted at `/workspace/repo/`
- Analysis notebooks can be saved to `/workspace/analysis/`
- Dependencies are installed automatically during build
