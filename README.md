# Mural Digital
Sistema para transmitir conteúdo institucional, baseado em tecnologias web (FastAPI, Python e Docker).

## Estrutura de Diretórios e Persistência

- **Pasta `dados`**: É o diretório de armazenamento persistente do sistema. Aqui ficam armazenados:
  - O banco de dados (SQLite);
  - As mídias enviadas (imagens e vídeos);
  - Os logs e registros de auditoria.

## Requisitos de Certificado (HTTPS)

Para o correto funcionamento nos navegadores e dispositivos (sem alertas de segurança bloqueando o conteúdo), **o sistema requer um certificado SSL/TLS válido**, emitido por uma Autoridade Certificadora (CA) reconhecida. Certificados autoassinados (self-signed) geralmente causam bloqueios e os navegadores reclamam.

- **Ambiente de Desenvolvimento/Testes**: Na pasta `HTTPS` do projeto, foi utilizado o proxy [Caddy](https://caddyserver.com/) durante o desenvolvimento para lidar com a configuração de certificados.
- **Ambiente de Produção**: Para implementações definitivas, pode-se continuar utilizando o Caddy, ou optar por Nginx com Certbot, Traefik, ou qualquer outro formatoda sua preferência para garantir o certificado válido.

## Configuração das TVs / Clientes

A ideia principal do sistema é atuar como um mural digital. Para exibir o painel nas TVs, TV Box ou tablets,recomendo o uso do aplicativo **Fully Kiosk Browser**.

### Setup (Fully Kiosk Browser)
1. Instale o aplicativo [Fully Kiosk Browser](https://www.fully-kiosk.com/) no dispositivo alvo.
2. Configure o aplicativo para **inicializar automaticamente** com o boot do sistema operacional.
3. Configure a **Start URL** apontando para o endereço de hospedagem do sistema, incluindo o ID da zona desejada (`https://endereco.com/?zona=1`)

### Fallback de Zona e Timeout
- Caso o dispositivo acesse a aplicação sem informar uma zona na URL, ou caso a zona informada esteja desativada, o sistema possui um fallback: ele exibirá um menu para que o usuário escolha uma das zonas existentes.
- **Timeout automático**: Como nas TVs ninguém interage (ninguém vai clicar em nada), se nenhuma escolha for feita no menu, o sistema aguarda um timeout e **entra automaticamente na primeira zona disponível**.

## Painel de Administração (`/config`)

O gerenciamento do Mural Digital é feito através da rota `/config`. A aplicação possui perfis de permissão distintos:

### Administradores Comuns
Podem realizar as tarefas diárias de gerenciamento de conteúdo:
- Adicionar ou remover mídias (vídeos e imagens);
- Gerenciar informações e mensagens de texto;
- Mudar sua própria senha.

### Usuário Mestre
O sistema conta com um usuário principal, cujas credenciais (usuário e senha) vêm definidas através do arquivo de ambiente (`env` ou variáveis de ambiente `USUARIO_ADMIN` e `SENHA_ADMIN`). **Recomenda-se fortemente alterar as credenciais**.
Além dos privilégios de administradores comuns, o **Usuário Mestre** tem permissão para:
- Alterar o layout principal da TV;
- Criar e editar Novas Zonas;
- Criar novos usuários;
- Revogar o acesso de usuários existentes.

## Como Executar

Este projeto é conteinerizado usando Docker. Para rodar:
1. Pode usar os scripts auxiliares disponibilizados no repositório: rode `executar.bat` (no Windows) ou `executar.sh` (no Linux/macOS).
2. Esses scripts irão compilar a imagem, parar containers antigos e iniciar o servidor na porta 8000, mapeando o volume da pasta `dados`.
