#!/bin/bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="apisilas.ddns.net"
PORT="8000"

echo "Gerando Caddyfile..."
cat <<EOF > "$DIR/Caddyfile"
$DOMAIN {
    reverse_proxy host.docker.internal:$PORT
}
EOF

echo "Limpando containers antigos..."
docker stop caddy-mural >/dev/null 2>&1
docker rm caddy-mural >/dev/null 2>&1

echo "Iniciando Caddy para obter SSL da Let's Encrypt..."
docker run -d \
  --name caddy-mural \
  --restart unless-stopped \
  -p 80:80 \
  -p 443:443 \
  --add-host host.docker.internal:host-gateway \
  -v "$DIR/Caddyfile":/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy

echo ""
echo "========================================================"
echo "Servidor rodando!"
echo "O Caddy esta solicitando o certificado [pode levar alguns segundos]"
echo "Acesso: https://$DOMAIN"
echo "========================================================"

read -p "Pressione [Enter] para sair..."  