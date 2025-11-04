@echo off
echo Starting ML Repository Analysis Containers
echo ================================================

echo AUTOMATIC1111_stable-diffusion-webui -^> http://localhost:8888
echo huggingface_transformers -^> http://localhost:8889
echo keras-team_keras -^> http://localhost:8890
echo pytorch_pytorch -^> http://localhost:8891
echo rasbt_mlxtend -^> http://localhost:8892
echo tqdm_tqdm -^> http://localhost:8893

echo.
echo Building and starting all containers...
docker-compose -f docker-compose-modular.yml up --build -d

echo All containers started!
echo Access repositories at the URLs shown above
pause
