# SmartCool 3.5" Monitor (TARRASGA Edition)

Aplicação própria em Python para controlar o ecrã USB secundário de **3.5 polegadas (480x320)** sem necessidade do AIDA64.

---

## Estrutura da Aplicação

```
E:\Gravi\SmartCoolApp\
├── app.py               # Interface Gráfica (GUI) com pré-visualização ao vivo
├── screen_driver.py     # Driver de comunicação USB Série (Protocolo Turing / SmartCool Rev A)
├── hardware_monitor.py  # Módulo de recolha de temperaturas, ventiladores, CPU e RAM
├── assets/
│   └── background.png   # Imagem de fundo ROG personalizada (480x320)
├── requirements.txt     # Bibliotecas necessárias (pyserial, pillow, psutil, wmi)
├── iniciar.bat          # Ficheiro de arranque com verificação automática
└── LEIA-ME.md           # Este manual
```

---

## Como Executar a Aplicação

1. Dê um duplo clique no ficheiro:
   **`E:\Gravi\INICIAR_APP_SMARTCOOL.bat`** (ou `iniciar.bat` dentro da pasta `SmartCoolApp`);
2. Se ainda não tiver o Python instalado, o ficheiro abrirá automaticamente a página de transferência oficial do [Python.org](https://www.python.org/downloads/):
   - *Atenção:* Durante a instalação do Python, marque obrigatoriamente a opção:
     `[X] Add Python to PATH`
3. O programa instalará as dependências necessárias automaticamente e abrirá a janela da aplicação!

---

## Funcionalidades da Sua Aplicação

1. **Pré-visualização em Tempo Real (Live Preview)**:
   - A janela mostra exatamente o que está a ser renderizado antes e durante o envio para o ecrã físico.
2. **Deteção Automática de Portas COM**:
   - Deteta todas as portas USB do PC e permite escolher a porta do ecrã com um clique.
3. **Seletor de Imagens de Fundo**:
   - Pode trocar de imagem de fundo sempre que quiser sem ter de reprogramar nada.
4. **Controlo de Brilho**:
   - Ajuste o brilho do visor físico através de uma barra deslizante (0 a 100%).
5. **Sensores Inteligentes**:
   - Se tiver uma placa gráfica NVIDIA, a aplicação lê automaticamente as temperaturas e velocidade das ventoinhas via `nvidia-smi`.
   - Se abrir o [Libre Hardware Monitor](https://librehardwaremonitor.net/) em segundo plano, a aplicação lê todos os sensores da motherboard e CPU automaticamente!

---

## Como Criar um Executável Único (.EXE)

Se no futuro quiser ter apenas um ficheiro `.exe` que corre em qualquer computador sem precisar de ter o Python visível:

1. Abra a Linha de Comandos na pasta `SmartCoolApp`;
2. Instale o PyInstaller:
   ```cmd
   pip install pyinstaller
   ```
3. Compile o programa:
   ```cmd
   pyinstaller --noconsole --onefile --add-data "assets;assets" app.py
   ```
4. O seu `.exe` independente será criado dentro da subpasta `dist`!
