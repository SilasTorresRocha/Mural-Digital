@echo off
echo Gerando Caddyfile
echo apisilas.ddns.net { > "%~dp0Caddyfile"
echo     reverse_proxy host.docker.internal:8000 >> "%~dp0Caddyfile"
echo } >> "%~dp0Caddyfile"

echo Iniciando Caddy para obter SSL da Let's Encrypt...
docker stop caddy-mural
docker rm caddy-mural

docker run -d ^
  --name caddy-mural ^
  -p 80:80 ^
  -p 443:443 ^
  --add-host host.docker.internal:host-gateway ^
  -v "%~dp0Caddyfile":/etc/caddy/Caddyfile ^
  -v caddy_data:/data ^
  -v caddy_config:/config ^
  caddy

echo.
echo ========================================================
echo Servidor rodando! 
echo O Caddy esta solicitando o certificado [pode levar alguns segundos]
echo https://apisilas.ddns.net
echo ========================================================
pause