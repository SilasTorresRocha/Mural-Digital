@echo off
setlocal enabledelayedexpansion

for /f "tokens=1,2 delims==" %%a in (%~dp0.env) do (
    set %%a=%%b
)

echo Gerando Caddyfile...
echo %DOMAIN% { > "%~dp0Caddyfile"
echo     reverse_proxy host.docker.internal:%PORT% >> "%~dp0Caddyfile"
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
echo Acesso: https://!DOMAIN!
echo ========================================================
pause
