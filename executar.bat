@echo off
echo Construindo a imagem do Mural Digital ASCOM...
docker build -t mural_digital_ascom .

echo.
echo Parando container antigo (se existir)...
docker stop mural_digital_container
docker rm mural_digital_container

echo.
echo Iniciando o container na porta 8000...
echo Os dados persistentes serao salvos na pasta "%cd%\dados"
docker run -d --name mural_digital_container -p 8000:8000 -v "%cd%\dados:/aplicacao/dados" mural_digital_ascom

echo.
echo Mural Digital iniciado! Acesse:
echo TV: http://localhost:8000
echo Admin: http://localhost:8000/config
pause
