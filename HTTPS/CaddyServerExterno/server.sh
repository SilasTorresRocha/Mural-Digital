#!/bin/bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN_VPN="apisilas.ddns.net"
PORT_VPN="8000"

DOMAIN_PC="serversilas.ddns.net"
IP_PC="192.168.0.101"
PORT_PC="8000"

echo "Gerando Caddyfile Unificado..."
cat <<EOF > "$DIR/Caddyfile"
{
    key_type rsa2048
}

$DOMAIN_VPN {
    reverse_proxy host.docker.internal:$PORT_VPN
}

$DOMAIN_PC {
    reverse_proxy $IP_PC:$PORT_PC
}
EOF

echo "Limpando containers antigos..."
docker stop caddy-VPN >/dev/null 2>&1
docker rm caddy-VPN >/dev/null 2>&1

echo "Iniciando Caddy para obter SSL da Let's Encrypt (VPN + PC)..."
docker run -d \
  --name caddy-VPN \
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
echo "Servidor rodando na base do RSA 2048!"
echo "Dominios ativos:"
echo " - $DOMAIN_VPN (Apontando para a VPN)"
echo " - $DOMAIN_PC (Apontando para seu PC: $IP_PC:$PORT_PC)"
echo "========================================================"
