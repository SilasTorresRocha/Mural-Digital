# Infraestrutura e Modificação: Fully Kiosk Browser

Este diretório contém as ferramentas, os scripts e a versão modificada do **Fully Kiosk Browser** necessários para a implantação do Mural Digital nos dispositivos Amazon Fire TV Stick.

## O Problema do "Fantasma" do icone Microfone
Nas versões recentes do Fire OS, o sistema operacional possui um monitor de privacidade agressivo. Como o aplicativo original do Fully Kiosk declara a permissão de Áudio/Microfone em seu código-fonte (para a função de detecção acústica), o Fire OS força a exibição permanente de um ícone de alerta de microfone no canto superior direito da tela assim que o app é iniciado.

Esse ícone sobrepõe a interface do Mural Digital. Comandos ADB padrão (`appops deny` ou `pm revoke`) e a desativação de notificações do sistema **não** resolvem o problema, pois o gatilho visual do Fire OS é acionado pela mera existência da declaração no arquivo `AndroidManifest.xml`.

##  A Solução: APK Modificado
Para contornar, o arquivo de instalação original foi modificado.
1. **Descompilação:** O APK foi descompilado usando o `apktool`.
2. **Edição do Manifesto:** Todas as tags `<uses-permission>` e `<uses-feature>` referentes a `CAMERA` e `RECORD_AUDIO` foram sumariamente removidas do `AndroidManifest.xml`.
3. **Correção de Compressão (Erro -124):** Para compatibilidade com Android 11+ (API 30+), o arquivo `apktool.yml` foi ajustado para **não comprimir** o `resources.arsc`, inserindo a flag no campo `doNotCompress`. E a flag `android:extractNativeLibs` foi ajustada para `true` no manifesto.
4. **Recompilação e Assinatura:** O pacote foi reconstruído e assinado via `uber-apk-signer`, aplicando o alinhamento de 4-bytes (`zipalign`) obrigatório.

---

##  Estrutura do Diretório

* `/adb/`: Contém os binários do Android Debug Bridge (`adb.exe`, etc.) para envio de comandos via rede para o Fire TV, além do instalador final do Kiosk (`fully_silas_uncompressed-aligned-debugSigned.apk`).
* `/apktool/`: Contém as ferramentas de descompilação/assinatura (`apktool.jar`, `uber-apk-signer-1.3.0.jar`) e o histórico de APKs gerados.
* `/apktool/fully/`: Contém os arquivos de configuração editados (`AndroidManifest.xml`, `apktool.yml`) que serviram de base para o mod.

---

##  Roteiro de Implantação

Siga este passo a passo estrito para padronizar a instalação nos novos Fire TV Sticks.

### 1. Preparação Manual (Controle Remoto)
Na interface padrão da Amazon, realize os seguintes bloqueios:
* Vá em **Configurações > Preferências > Conteúdo em destaque** e **desative** a reprodução automática de vídeo e áudio.
* Vá em **Configurações > Tela e Sons > Protetor de Tela** e altere o Tempo de Início para **Nunca**.
* Vá em **Configurações > Meu Fire TV > Informações** e clique 7 vezes no nome do dispositivo para ativar o modo desenvolvedor.
* Retorne, entre em **Opções para desenvolvedores** e ative a **Depuração ADB**.
* Em **Rede**, anote o endereço IP do Fire TV.

### 2. Execução do Script de Limpeza (Via Terminal do PC)
Abra o PowerShell dentro da pasta `/adb/` e execute os comandos abaixo em sequência. Substitua `[IP_DA_TV]` pelo IP anotado:

```powershell
# Conectar à TV (Aceite o prompt na tela da TV marcando "Sempre permitir")
.\adb connect [IP_DA_TV]:5555

# Instalar o Fully Kiosk Modificado e Assinado
.\adb -s [IP_DA_TV]:5555 install fully_silas_uncompressed-aligned-debugSigned.apk

# Conceder permissão de sobreposição de tela e remover otimização de bateria
.\adb -s [IP_DA_TV]:5555 shell appops set de.ozerov.fully SYSTEM_ALERT_WINDOW allow
.\adb -s [IP_DA_TV]:5555 shell dumpsys deviceidle whitelist +de.ozerov.fully

# Desativar Serviços da Alexa (Evitar que o controle remoto acione a assistente (Tentativa))
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.vizzini
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.alexadirectivebrokerservice
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.tv.alexanotifications
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.tv.alexaalerts
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.alexamediaplayer.runtime.ftv
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.alexa.externalmediaplayer.fireos
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.alexa.datastore.app

# Desativar Bloatware, Protetores de Tela e Anúncios Nativos
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.tv.ftvambient
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.ftv.screensaver
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.media.recommendations
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.shoptv.client
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.shoptv.firetv.client
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.kso.blackbird
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.ftvads.deeplinking

# Desativar Notificações do Sistema Operacional
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.tv.notificationcenter
.\adb -s [IP_DA_TV]:5555 shell pm disable-user --user 0 com.amazon.systemnotices
```
**Importante:** Após rodar os comandos, reinicie o Fire TV retirando da energia.

### 3. Configuração do Fully Kiosk Browser
Ao iniciar a TV, abra o aplicativo Fully Kiosk e acesse as `Settings`:

1. **Start URL:**

- `Web Content Settings` > `Start URL`: Insira o IP ou Domínio do Mural Digital.
2. **Correção do Player de Vídeo**:

- `Advanced Web Settings` > `Graphics Acceleration Mode`: Alterar para **None**.
3. **Modo Quiosque**:

- `Device Management` > **Keep Screen On**: **Ativar**.
- `Device Management` > **Launch on Boot**: **Ativar**.
- `Kiosk Mode` > **Enable Kiosk Mode**: **Ativar** (Configurar um PIN, caso queira).

### 4. Finalização Física
Remova as pilhas do controle remoto. Como o sistema está programado para auto-boot e travado no Modo Quiosque, a ausência física de hardware de input garante que nenhum evento inesperado quebre a experiência do Mural Digital.

## Como recriar o Mod
Caso seja necessário atualizar a versão do Fully Kiosk no futuro, repita o processo utilizando o terminal na pasta `/apktool/`:

1. **Descompilar o APK original:**
`java -jar apktool.jar d fuly.apk`
2. Modificar o arquivo `AndroidManifest.xml` (remoção de tags de gravação de áudio e alteração da flag `extractNativeLibs` para `true`).
3. Modificar o arquivo `apktool.yml` (Adicionar `resources.arsc` na lista `doNotCompress`).
4. **Recompilar a pasta:**
`java -jar apktool.jar b fully -o fully_compilado.apk`
5. **Assinar e alinhar o APK final:**
`java -jar uber-apk-signer-1.3.0.jar -a fully_compilado.apk`

## Links Oficiais para Download 

Para replicar este processo em novas telas ou atualizar a versão do aplicativo, você precisará baixar as ferramentas oficiais diretamente de seus desenvolvedores.

*   **Fully Kiosk Browser (APK Original):**
    [Site Oficial - Download Box](https://www.fully-kiosk.com/en/#download-box)
*   **ADB (Android SDK Platform-Tools):**
    [Google Developers - Platform Tools](https://developer.android.com/studio/releases/platform-tools)
*   **APKTool (Para descompilar/recompilar o APK):**
    [Site Oficial / Instalação](https://apktool.org/docs/install) | [Releases no GitHub](https://github.com/iBotPeaches/Apktool/releases)
*   **Uber APK Signer (Para assinar APK):**
    [Releases no GitHub](https://github.com/patrickfav/uber-apk-signer/releases)