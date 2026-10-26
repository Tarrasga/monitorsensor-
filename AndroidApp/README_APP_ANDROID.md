# 📱 SmartCool Mobile // Aplicação Android Dedicada

Este projeto contém a aplicação Android nativa para transformar qualquer telemóvel ou tablet num **monitor de telemetria dedicado 24/7** para o teu PC.

---

## 🌟 2 Maneiras Fáceis de Usar no Telemóvel

### Método 1: Instalar Diretamente via Chrome (Mais Rápido - 10 Segundos)
Não precisas de compilar código nem ligar cabos:
1. Abre o Chrome no teu telemóvel e acede a:  
   👉 **`http://192.168.1.65:8080`**  
   *(Ou lê o QR Code na app do PC).*
2. Clica nos **3 pontinhos no topo do Chrome** (ou espera surgir o aviso no fundo).
3. Seleciona **"Instalar aplicação"** ou **"Adicionar ao ecrã principal"**.
4. O Android instala a aplicação **SmartCool Mobile** com o logótipo da Garra Monster!
5. Abre o ícone a partir do teu ecrã: corre em ecrã inteiro nativo e com o motor **NoSleep ativo** (o ecrã NUNCA desliga enquanto estiver aberta!).

---

### Método 2: Compilar o APK Nativo no Android Studio
Se quiseres gerar o ficheiro `.apk` independente:
1. Abre o **Android Studio**.
2. Escolhe **Open** e seleciona esta pasta: `E:\Gravi\AndroidApp`.
3. O Android Studio carrega o projeto Gradle automaticamente.
4. Vai ao menu: **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
5. Copia o ficheiro gerado (`app-debug.apk`) para o teu telemóvel e instala!

---

## ⚙️ Características Técnicas do Código Nativo

* **`FLAG_KEEP_SCREEN_ON`**: O ecrã do Android mantém-se ligado 24/7 ao nível do hardware e do sistema operativo.
* **Modo Imersivo Sticky**: Esconde a barra de notificações e os botões de navegação para aproveitamento total do ecrã.
* **Configuração de IP Fácil**: Um toque longo no ecrã (ou no ícone da roda dentada) permite alterar o IP do PC facilmente caso a rede mude.
* **Aceleração por Hardware**: Renderização ultra suave a 60 FPS com baixo consumo de bateria.
