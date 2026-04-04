import sys, os, json, asyncio, threading, pygame, pytchat, edge_tts, shutil, time, re, signal, random, webbrowser
from google import genai 
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                             QLabel, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QTabWidget, QHeaderView, QListWidget, QSpinBox, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

# Função essencial para o EXE encontrar os arquivos internos
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BotSignals(QObject):
    log = pyqtSignal(str)
    status_api = pyqtSignal(bool)
    status_yt = pyqtSignal(str, str)

class TubeVoiceAI(QMainWindow): # Nome da classe definido corretamente
    def __init__(self):
        super().__init__()
        self.version = "9.4.0"
        self.repo_url = "https://github.com/seu-usuario/repositorio"
        
        self.config_file = "tube_voice_pro_data.json"
        self.sounds_dir = "meus_sons_bot"
        
        self.bot_running = False
        self.last_request_time = 0 
        self.sound_mappings = {}
        self.forbidden_words = []
        self.announcements = []
        self.custom_commands = {}
        self.giveaway_list = set()
        self.is_giveaway_open = False
        
        self.bot_mood = "Você é o TubeVoice AI, um assistente de live super inteligente e descolado."
        self.selected_model = "gemini-2.0-flash"
        self.ai_cooldown = 5
        self.voice_selected = "pt-BR-AntonioNeural"
        self.voice_rate = "+0%"

        if not os.path.exists(self.sounds_dir): os.makedirs(self.sounds_dir)
        self.signals = BotSignals()
        
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except: pass
        
        self.init_ui()
        self.load_config()
        
        self.signals.log.connect(self.update_log)
        self.signals.status_api.connect(self.update_api_status)
        self.signals.status_yt.connect(self.update_yt_status)

    def init_ui(self):
        self.setWindowTitle(f"TubeVoice AI Pro - v{self.version}")
        self.setMinimumSize(900, 850) # Largura de 900px
        
        if os.path.exists(resource_path("bot_icon.ico")):
            self.setWindowIcon(QIcon(resource_path("bot_icon.ico")))

        self.setStyleSheet("""
            QMainWindow { background-color: #0d0d0d; }
            QTabWidget::pane { border: 1px solid #333; background-color: #0d0d0d; }
            QTabBar::tab { 
                background: #1a1a1a; color: #888; padding: 10px 18px; 
                min-width: 95px; font-weight: bold; font-size: 11px;
                border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; 
            }
            QTabBar::tab:selected { background: #27ae60; color: white; }
            QLabel { color: #bbbbbb; font-size: 11px; font-weight: bold; margin-top: 6px; }
            QLineEdit, QSpinBox, QTextEdit, QListWidget, QComboBox { 
                background-color: #1a1a1a; color: white; border: 1px solid #333; padding: 8px; border-radius: 4px; 
            }
            QTextEdit { background-color: #000; color: #00ff41; font-family: 'Consolas'; font-size: 12px; }
            QPushButton { background-color: #27ae60; color: white; padding: 10px; border-radius: 4px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton#btn_purple { background-color: #8e44ad; }
            QPushButton#btn_purple:hover { background-color: #9b59b6; }
            QPushButton#btn_danger { background-color: #c0392b; }
            QPushButton#btn_danger:hover { background-color: #e74c3c; }
        """)
        
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)

        # --- ABA 1: PAINEL ---
        self.tab_main = QWidget(); lay_m = QVBoxLayout(self.tab_main)
        st_lay = QHBoxLayout()
        st_lay.addWidget(QLabel("IA STATUS:")); self.lbl_api = QLabel("🔴 Off"); st_lay.addWidget(self.lbl_api)
        st_lay.addSpacing(50)
        st_lay.addWidget(QLabel("YOUTUBE STATUS:")); self.lbl_yt = QLabel("🔴 Off"); st_lay.addWidget(self.lbl_yt)
        st_lay.addStretch(); lay_m.addLayout(st_lay)
        
        lay_m.addWidget(QLabel("CHAVE API DO GEMINI (Google AI Studio):"))
        self.input_key = QLineEdit(); self.input_key.setEchoMode(QLineEdit.EchoMode.Password); lay_m.addWidget(self.input_key)
        lay_m.addWidget(QLabel("LINK OU ID DA LIVE DO YOUTUBE (O ID são os 11 caracteres finais):"))
        self.input_id = QLineEdit(); lay_m.addWidget(self.input_id)
        lay_m.addWidget(QLabel("LINK DO SEU SERVIDOR DISCORD (A IA enviará quando pedirem):"))
        self.input_discord = QLineEdit(); lay_m.addWidget(self.input_discord)
        lay_m.addWidget(QLabel("LOG DE OPERAÇÕES DO SISTEMA:"))
        self.log_output = QTextEdit(); lay_m.addWidget(self.log_output)
        self.btn_start = QPushButton("🚀 INICIAR OPERAÇÃO COMPLETA"); self.btn_start.clicked.connect(self.toggle_bot); lay_m.addWidget(self.btn_start)

        # --- ABA 2: ALERTAS ---
        self.tab_s = QWidget(); lay_s = QVBoxLayout(self.tab_s)
        lay_s.addWidget(QLabel("CONFIGURAR ALERTA SONORO (Palavra gatilho | Arquivo de áudio):"))
        row_s = QHBoxLayout(); self.in_word = QLineEdit(); btn_br = QPushButton("📁 Escolher Som"); btn_br.clicked.connect(self.browse_sound)
        btn_add_s = QPushButton("➕ Adicionar"); btn_add_s.clicked.connect(self.add_sound_manually)
        row_s.addWidget(self.in_word); row_s.addWidget(btn_br); row_s.addWidget(btn_add_s); lay_s.addLayout(row_s)
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["Gatilho", "Arquivo"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); lay_s.addWidget(self.table)

        # --- ABA 3: FILTRO ---
        self.tab_sec = QWidget(); lay_f = QVBoxLayout(self.tab_sec)
        lay_f.addWidget(QLabel("FILTRO DE SEGURANÇA (Termos que o bot não lerá e dará bronca):"))
        row_f = QHBoxLayout(); self.in_f = QLineEdit(); btn_f = QPushButton("🚫 Bloquear Termo"); btn_f.setObjectName("btn_danger"); btn_f.clicked.connect(self.add_f)
        row_f.addWidget(self.in_f); row_f.addWidget(btn_f); lay_f.addLayout(row_f)
        self.list_f = QListWidget(); lay_f.addWidget(self.list_f)
        btn_rem_f = QPushButton("🗑️ Remover Termo"); btn_rem_f.setObjectName("btn_danger"); btn_rem_f.clicked.connect(self.rem_f); lay_f.addWidget(btn_rem_f)

        # --- ABA 4: SORTEIO ---
        self.tab_g = QWidget(); lay_g = QVBoxLayout(self.tab_g)
        lay_g.addWidget(QLabel("COMANDO PARA ENTRAR NO SORTEIO (Ex: !entrar):")); self.in_give_cmd = QLineEdit(); self.in_give_cmd.setText("!entrar"); lay_g.addWidget(self.in_give_cmd)
        row_g = QHBoxLayout()
        self.btn_start_g = QPushButton("🟢 ABRIR ENTRADAS"); self.btn_start_g.clicked.connect(self.start_giveaway)
        self.btn_pick_g = QPushButton("💜 SORTEAR GANHADOR AGORA"); self.btn_pick_g.setObjectName("btn_purple"); self.btn_pick_g.clicked.connect(self.pick_winner)
        row_g.addWidget(self.btn_start_g); row_g.addWidget(self.btn_pick_g); lay_g.addLayout(row_g)
        lay_g.addWidget(QLabel("PARTICIPANTES COLETADOS:")); self.list_p = QListWidget(); lay_g.addWidget(self.list_p)

        # --- ABA 5: TIMERS ---
        self.tab_c = QWidget(); lay_c = QVBoxLayout(self.tab_c)
        lay_c.addWidget(QLabel("MENSAGEM AUTOMÁTICA (O bot falará sozinho no tempo definido):"))
        row_t = QHBoxLayout(); self.in_tt = QLineEdit(); self.in_tt.setPlaceholderText("Mensagem..."); self.in_ti = QSpinBox(); self.in_ti.setRange(1,60); btn_at = QPushButton("➕ Agendar")
        btn_at.clicked.connect(self.add_announcement); row_t.addWidget(self.in_tt); row_t.addWidget(self.in_ti); row_t.addWidget(btn_at); lay_c.addLayout(row_t)
        self.list_t = QListWidget(); lay_c.addWidget(self.list_t)
        lay_c.addWidget(QLabel("RESPOSTA RÁPIDA (Gatilho direto de voz sem IA):"))
        row_cmd = QHBoxLayout(); self.in_ck = QLineEdit(); self.in_ck.setPlaceholderText("!insta"); self.in_cv = QLineEdit(); self.in_cv.setPlaceholderText("Chave..."); btn_ac = QPushButton("➕ Criar")
        btn_ac.clicked.connect(self.add_custom_cmd); row_cmd.addWidget(self.in_ck); row_cmd.addWidget(self.in_cv); row_cmd.addWidget(btn_ac); lay_c.addLayout(row_cmd)

        # --- ABA 6: PERSONA ---
        self.tab_p = QWidget(); lay_p = QVBoxLayout(self.tab_p)
        lay_p.addWidget(QLabel("PERSONA DA IA (Como o bot deve se comportar):")); self.in_mood = QTextEdit(); self.in_mood.setPlainText(self.bot_mood); lay_p.addWidget(self.in_mood)
        btn_save_p = QPushButton("✅ Aplicar Persona no Sistema"); btn_save_p.clicked.connect(self.save_config); lay_p.addWidget(btn_save_p)

        # --- ABA 7: CONFIGS ⚙️ ---
        self.tab_settings = QWidget(); lay_set = QVBoxLayout(self.tab_settings)
        lay_set.addWidget(QLabel("MODELO DA IA:")); self.combo_model = QComboBox(); self.combo_model.addItems(["gemini-2.0-flash", "gemini-1.5-flash"]); lay_set.addWidget(self.combo_model)
        lay_set.addWidget(QLabel("SINTETIZADOR:")); self.combo_voice = QComboBox(); self.combo_voice.addItems(["Masculino", "Feminino"]); lay_set.addWidget(self.combo_voice)
        lay_set.addWidget(QLabel("VELOCIDADE:")); self.combo_rate = QComboBox(); self.combo_rate.addItems(["Normal", "+20%", "+50%", "-20%"]); lay_set.addWidget(self.combo_rate)
        lay_set.addWidget(QLabel("COOLDOWN IA (Segundos):")); self.spin_cooldown = QSpinBox(); self.spin_cooldown.setRange(1, 60); self.spin_cooldown.setValue(5); lay_set.addWidget(self.spin_cooldown)
        lay_set.addSpacing(30); lay_set.addWidget(QLabel("SOFTWARE E ATUALIZAÇÕES:"))
        self.btn_update = QPushButton("💜 VERIFICAR ATUALIZAÇÕES NO GITHUB"); self.btn_update.setObjectName("btn_purple")
        self.btn_update.clicked.connect(lambda: webbrowser.open(self.repo_url)); lay_set.addWidget(self.btn_update)
        lay_set.addStretch(); btn_save_all = QPushButton("💾 SALVAR CONFIGURAÇÕES"); btn_save_all.clicked.connect(self.save_config); lay_set.addWidget(btn_save_all)

        self.tabs.addTab(self.tab_main, "Painel"); self.tabs.addTab(self.tab_s, "Alertas"); self.tabs.addTab(self.tab_sec, "Filtro")
        self.tabs.addTab(self.tab_g, "Sorteio"); self.tabs.addTab(self.tab_c, "Timers"); self.tabs.addTab(self.tab_p, "Persona"); self.tabs.addTab(self.tab_settings, "⚙️")

    # --- LÓGICA DO SISTEMA ---
    def update_log(self, t): self.log_output.append(t)
    def update_api_status(self, c): self.lbl_api.setText("🟢 On" if c else "🔴 Off"); self.lbl_api.setStyleSheet(f"color: {'#2ecc71' if c else '#e74c3c'}; font-weight: bold;")
    def update_yt_status(self, t, c): self.lbl_yt.setText(t); self.lbl_yt.setStyleSheet(f"color: {c}; font-weight: bold;")

    def extract_id(self, text):
        match = re.search(r"(?:v=|\/live\/|youtu\.be\/|\/v\/|\/embed\/|shorts\/|&v=|^)([^#&?\/\s]{11})", text)
        return match.group(1) if match else text.strip()

    def start_giveaway(self):
        self.is_giveaway_open = True; self.giveaway_list.clear(); self.list_p.clear()
        self.update_log("<font color='yellow'>Sorteio iniciado!</font>")

    def pick_winner(self):
        if not self.giveaway_list: return
        winner = random.choice(list(self.giveaway_list)); self.is_giveaway_open = False
        self.update_log(f"<font color='#8e44ad'>Vencedor: {winner}</font>")
        threading.Thread(target=lambda: asyncio.run(self.speak(f"O vencedor do sorteio é {winner}!")), daemon=True).start()

    def add_custom_cmd(self):
        k, v = self.in_ck.text().lower().strip(), self.in_cv.text().strip()
        if k and v: self.custom_commands[k] = v; self.save_config(); self.in_ck.clear(); self.in_cv.clear()

    def add_announcement(self):
        t, i = self.in_tt.text().strip(), self.in_ti.value()
        if t: self.announcements.append({"text": t, "interval": i, "last_time": time.time()}); self.list_t.addItem(f"[{i}m] {t}"); self.save_config(); self.in_tt.clear()

    def add_f(self):
        w = self.in_f.text().lower().strip(); self.forbidden_words.append(w); self.list_f.addItem(w); self.save_config(); self.in_f.clear()

    def rem_f(self):
        it = self.list_f.currentItem()
        if it: self.forbidden_words.remove(it.text()); self.list_f.takeItem(self.list_f.row(it)); self.save_config()

    def browse_sound(self):
        p, _ = QFileDialog.getOpenFileName(self, "Som", "", "Audio (*.wav *.mp3)"); self.temp_p = p

    def add_sound_manually(self):
        w = self.in_word.text().lower().strip()
        if w and hasattr(self, 'temp_p'):
            dest = os.path.join(self.sounds_dir, os.path.basename(self.temp_p))
            shutil.copy2(self.temp_p, dest); self.sound_mappings[w] = dest; self.update_table(); self.save_config(); self.in_word.clear()

    def update_table(self):
        self.table.setRowCount(0)
        for w, p in self.sound_mappings.items():
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(w)); self.table.setItem(r, 1, QTableWidgetItem(os.path.basename(p)))

    def save_config(self):
        self.selected_model = self.combo_model.currentText()
        self.voice_selected = "pt-BR-AntonioNeural" if self.combo_voice.currentIndex() == 0 else "pt-BR-FranciscaNeural"
        rates = ["+0%", "+20%", "+50%", "-20%"]; self.voice_rate = rates[self.combo_rate.currentIndex()]
        self.ai_cooldown = self.spin_cooldown.value(); self.bot_mood = self.in_mood.toPlainText()
        c = {"key": self.input_key.text(), "id": self.input_id.text(), "discord": self.input_discord.text(), "sounds": self.sound_mappings, "forbidden": self.forbidden_words, "timers": self.announcements, "mood": self.bot_mood, "model": self.selected_model, "voice": self.voice_selected, "rate": self.voice_rate, "cooldown": self.ai_cooldown, "cmds": self.custom_commands}
        with open(self.config_file, 'w') as f: json.dump(c, f, indent=4)

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                c = json.load(f); self.input_key.setText(c.get("key", "")); self.input_id.setText(c.get("id", "")); self.input_discord.setText(c.get("discord", ""))
                self.sound_mappings = c.get("sounds", {}); self.forbidden_words = c.get("forbidden", []); self.announcements = c.get("timers", []); self.custom_commands = c.get("cmds", {})
                self.bot_mood = c.get("mood", self.bot_mood); self.selected_model = c.get("model", "gemini-2.0-flash")
                self.voice_selected = c.get("voice", "pt-BR-AntonioNeural"); self.ai_cooldown = c.get("cooldown", 5); self.voice_rate = c.get("rate", "+0%")
                self.in_mood.setPlainText(self.bot_mood); self.combo_model.setCurrentText(self.selected_model); self.spin_cooldown.setValue(self.ai_cooldown)
                self.combo_voice.setCurrentIndex(0 if "Antonio" in self.voice_selected else 1); self.update_table()
                for w in self.forbidden_words: self.list_f.addItem(w)
                for a in self.announcements: self.list_t.addItem(f"[{a['interval']}m] {a['text']}")

    def toggle_bot(self):
        if not self.bot_running:
            self.bot_running = True; self.btn_start.setText("⛔ ENCERRAR OPERAÇÃO"); self.btn_start.setStyleSheet("background-color: #c0392b;")
            threading.Thread(target=lambda: asyncio.run(self.run_bot_logic()), daemon=True).start()
        else: self.bot_running = False; self.btn_start.setText("🚀 INICIAR OPERAÇÃO COMPLETA"); self.btn_start.setStyleSheet("background-color: #27ae60;")

    async def speak(self, t):
        try:
            pygame.mixer.music.unload()
            f = f"v_{int(time.time())}.mp3"
            c = edge_tts.Communicate(t, self.voice_selected, rate=self.voice_rate)
            await c.save(f); pygame.mixer.music.load(f); pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): await asyncio.sleep(0.1)
            pygame.mixer.music.unload(); os.remove(f)
        except: pass

    async def run_bot_logic(self):
        try:
            self.client = genai.Client(api_key=self.input_key.text().strip())
            self.chat_session = self.client.chats.create(model=self.selected_model)
            self.signals.status_api.emit(True); self.signals.log.emit("<font color='#2ecc71'>Conexão IA bem sucedida!</font>")
        except: self.signals.log.emit("Erro IA"); self.bot_running = False; return
        l_id = self.extract_id(self.input_id.text().strip())
        orig_sig = signal.signal; signal.signal = lambda s, h: None
        chat = pytchat.create(video_id=l_id); signal.signal = orig_sig
        if not chat.is_alive(): self.signals.status_yt.emit("🔴 Erro", ""); self.bot_running = False; return
        self.signals.status_yt.emit("🟢 On", "#2ecc71"); self.signals.log.emit("<font color='#2ecc71'>Conexão YouTube bem sucedida!</font>")
        while self.bot_running and chat.is_alive():
            ct = time.time()
            for a in self.announcements:
                if ct - a['last_time'] > (a['interval'] * 60): await self.speak(a['text']); a['last_time'] = ct
            for c in chat.get().sync_items():
                u, m = c.author.name, c.message; m_l = m.lower()
                self.signals.log.emit(f"<b>{u}:</b> {m}")
                if self.is_giveaway_open and self.in_give_cmd.text().lower() in m_l:
                    self.giveaway_list.add(u); self.list_p.clear(); self.list_p.addItems(list(self.giveaway_list))
                await self.speak(f"{u} disse {m}")
                for w, p in self.sound_mappings.items():
                    if w in m_l:
                        som = pygame.mixer.Sound(p); canal = som.play()
                        while canal.get_busy(): await asyncio.sleep(0.1)
                res = None; pode_ia = (ct - self.last_request_time) > self.ai_cooldown
                if any(w in m_l for w in self.forbidden_words):
                    if pode_ia: self.last_request_time = ct; res = self.chat_session.send_message(f"Bronca em {u}.").text
                elif m_l in self.custom_commands: res = self.custom_commands[m_l]
                elif "discord" in m_l: res = f"Link do Discord: {self.input_discord.text()}"
                elif pode_ia:
                    self.last_request_time = ct
                    try: res = self.chat_session.send_message(f"{self.bot_mood}\n\nEspectador {u} disse: {m}").text
                    except: res = None
                if res: await self.speak(res)
            await asyncio.sleep(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TubeVoiceAI() # CORREÇÃO: Nome da classe ajustado aqui
    win.show()
    sys.exit(app.exec())
