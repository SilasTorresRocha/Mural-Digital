#!/bin/bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="serversilas.ddns.net"
TARGET_IP="192.168.0.101"
TARGET_PORT="8000"

echo "Gerando Caddyfile para acesso externo..."
cat <<EOF > "$DIR/Caddyfile"
$DOMAIN {
    reverse_proxy $TARGET_IP:$TARGET_PORT
}
EOF

echo "Limpando containers antigos..."
docker stop caddy-externo >/dev/null 2>&1
docker rm caddy-externo >/dev/null 2>&1

echo "Iniciando Caddy para obter SSL da Let's Encrypt e redirecionar para o PC..."
docker run -d \
  --name caddy-externo \
  --restart unless-stopped \
  -p 80:80 \
  -p 443:443 \
  -v "$DIR/Caddyfile":/etc/caddy/Caddyfile \
  -v caddy_data_externo:/data \
  -v caddy_config_externo:/config \
  caddy

echo ""
echo "========================================================"
echo "Servidor reverso rodando no server!"
echo "Redirecionando trafego de https://$DOMAIN para $TARGET_IP:$TARGET_PORT"
echo "O Caddy esta solicitando o certificado (pode levar alguns segundos)"
echo "========================================================"

read -p "Pressione [Enter] para sair..."
