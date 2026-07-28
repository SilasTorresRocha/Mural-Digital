#!/bin/bash

echo "Construindo a imagem do Mural Digital ASCOM..."
docker build -t mural_digital_ascom .
echo ""
echo "Parando container antigo (se existir)..."
docker stop mural_digital_container 2>/dev/null
docker rm mural_digital_container 2>/dev/null
echo ""
echo "Iniciando o container na porta 8000..."
echo "Os dados persistentes serao salvos na pasta $(pwd)/dados"
docker run -d --restart=always --name mural_digital_container -p 8000:8000 -v "$(pwd)/dados:/aplicacao/dados" mural_digital_ascom
echo ""
echo "Mural Digital iniciado! Acesse:"
echo "TV: http://localhost:8000"
echo "Admin: http://localhost:8000/config"
