import sys, os, json, asyncio, threading, pygame, pytchat, edge_tts, shutil, time, re, signal, random, webbrowser
from google import genai 
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                             QLabel, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QTabWidget, QHeaderView, QListWidget, QSpinBox, 
                             QComboBox, QGridLayout, QScrollArea, QSlider, QFrame, QCheckBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

# Função para encontrar arquivos dentro do EXE (Ícone/Sons)
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BotSignals(QObject):
    log = pyqtSignal(str)
    status_api = pyqtSignal(bool)
    status_yt = pyqtSignal(str, str)

class TubeVoiceAI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- DEFINIÇÃO DE VARIÁVEIS ANTES DA UI (ESTABILIDADE) ---
        self.version = "13.7.0"
        self.repo_url = "https://github.com/seu-usuario/repositorio"
        self.config_file = "tube_voice_pro_v137.json"
        self.sounds_dir = "meus_sons_bot"
        
        self.bot_running = False
        self.last_request_time = 0 
        self.is_giveaway_open = False
        
        self.sound_mappings = {} 
        self.announcements = []
        self.custom_commands = {}
        self.giveaway_list = set()
        self.loyalty_data = {} 
        
        self.bot_mood = "Você é o TubeVoice AI, um assistente de live super inteligente e descolado."
        self.selected_model = "gemini-2.0-flash"
        self.voice_selected = "pt-BR-AntonioNeural"
        self.voice_rate = "+0%"
        self.voice_volume = 1.0
        self.master_sfx_volume = 1.0
        self.ai_cooldown = 5

        if not os.path.exists(self.sounds_dir): os.makedirs(self.sounds_dir)
        self.signals = BotSignals()
        try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except: pass
        
        # --- INICIAR INTERFACE ---
        self.init_ui()
        self.load_config()
        
        self.signals.log.connect(self.update_log_display)
        self.signals.status_api.connect(self.update_ia_status_label)
        self.signals.status_yt.connect(self.update_youtube_status_label)

    def init_ui(self):
        self.setWindowTitle(f"TubeVoice AI Pro - Software Oficial")
        self.setMinimumSize(900, 850) # LARGURA 900PX
        
        if os.path.exists(resource_path("bot_icon.ico")):
            self.setWindowIcon(QIcon(resource_path("bot_icon.ico")))

        self.setStyleSheet("""
            QMainWindow { background-color: #0d0d0d; }
            QTabWidget::pane { border: 1px solid #333; background-color: #0d0d0d; }
            QTabBar::tab { background: #1a1a1a; color: #888; padding: 10px 18px; min-width: 95px; font-weight: bold; font-size: 11px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #27ae60; color: white; }
            QLabel { color: #bbbbbb; font-size: 11px; font-weight: bold; margin-top: 6px; }
            QLineEdit, QSpinBox, QTextEdit, QListWidget, QComboBox { background-color: #1a1a1a; color: white; border: 1px solid #333; padding: 8px; border-radius: 4px; }
            QTextEdit { background-color: #000; color: #00ff41; font-family: 'Consolas'; font-size: 12px; }
            QPushButton { background-color: #27ae60; color: white; padding: 10px; border-radius: 4px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton#btn_purple { background-color: #8e44ad; }
            QPushButton#btn_purple:hover { background-color: #9b59b6; }
            QPushButton#btn_danger { background-color: #c0392b; }
            QFrame#MixerChannel { background-color: #161616; border: 2px solid #222; border-radius: 10px; min-width: 130px; padding: 8px; }
        """)
        
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)

        # ABA 1: PAINEL
        self.tab_main = QWidget(); lay_m = QVBoxLayout(self.tab_main)
        st_lay = QHBoxLayout(); st_lay.addWidget(QLabel("IA STATUS:")); self.lbl_api = QLabel("🔴 Off"); st_lay.addWidget(self.lbl_api); st_lay.addSpacing(40); st_lay.addWidget(QLabel("YOUTUBE STATUS:")); self.lbl_yt = QLabel("🔴 Off"); st_lay.addWidget(self.lbl_yt); st_lay.addStretch(); lay_m.addLayout(st_lay)
        lay_m.addWidget(QLabel("CHAVE API DO GEMINI (Google AI Studio):")); self.input_key = QLineEdit(); self.input_key.setEchoMode(QLineEdit.EchoMode.Password); self.input_key.setPlaceholderText("Cole sua chave aqui..."); lay_m.addWidget(self.input_key)
        lay_m.addWidget(QLabel("LINK OU ID DA LIVE DO YOUTUBE:")); self.input_id = QLineEdit(); self.input_id.setPlaceholderText("Link completo ou ID de 11 caracteres..."); lay_m.addWidget(self.input_id)
        lay_m.addWidget(QLabel("LINK DO SEU DISCORD (A IA dirá quando alguém pedir):")); self.input_discord = QLineEdit(); self.input_discord.setPlaceholderText("Ex: https://discord.gg/convite"); lay_m.addWidget(self.input_discord)
        self.log_output = QTextEdit(); lay_m.addWidget(QLabel("CONSOLE DE OPERAÇÕES:")); lay_m.addWidget(self.log_output)
        self.btn_start = QPushButton("🚀 INICIAR OPERAÇÃO COMPLETA"); self.btn_start.clicked.connect(self.toggle_bot); lay_m.addWidget(self.btn_start)

        # ABA 2: ALERTAS
        self.tab_s = QWidget(); lay_s = QVBoxLayout(self.tab_s); lay_s.addWidget(QLabel("CONFIGURAR ALERTA (Gatilho toca Som):")); row_s = QHBoxLayout(); self.in_word = QLineEdit(); self.in_word.setPlaceholderText("Gatilho (ex: susto)"); btn_br = QPushButton("📁 Buscar Som"); btn_br.clicked.connect(self.browse_sound); btn_add_s = QPushButton("➕ Add"); btn_add_s.clicked.connect(self.add_sound_manually); row_s.addWidget(self.in_word); row_s.addWidget(btn_br); row_s.addWidget(btn_add_s); lay_s.addLayout(row_s); self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["Gatilho", "Arquivo"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); lay_s.addWidget(self.table)

        # ABA 3: MESA (MIXER RACK)
        self.tab_mixer = QWidget(); lay_mix = QVBoxLayout(self.tab_mixer); lay_mix.addWidget(QLabel("MIXER DE ÁUDIO (Controles individuais por canal):")); self.scroll_mix = QScrollArea(); self.scroll_mix.setWidgetResizable(True); self.container_mix = QWidget(); self.layout_rack = QHBoxLayout(self.container_mix); self.layout_rack.setAlignment(Qt.AlignmentFlag.AlignLeft); self.scroll_mix.setWidget(self.container_mix); lay_mix.addWidget(self.scroll_mix); btn_sync = QPushButton("🔄 Sincronizar Mixer"); btn_sync.clicked.connect(self.update_mixer_rack); lay_mix.addWidget(btn_sync)

        # ABA 4: SORTEIO
        self.tab_g = QWidget(); lay_g = QVBoxLayout(self.tab_g); lay_g.addWidget(QLabel("COMANDO PARA SORTEIO:")); self.in_give_cmd = QLineEdit(); self.in_give_cmd.setText("!entrar"); lay_g.addWidget(self.in_give_cmd); row_g = QHBoxLayout(); btn_st_g = QPushButton("🟢 ABRIR"); btn_st_g.clicked.connect(self.start_giveaway); self.btn_pick_g = QPushButton("💜 SORTEAR AGORA"); self.btn_pick_g.setObjectName("btn_purple"); self.btn_pick_g.clicked.connect(self.pick_winner); row_g.addWidget(btn_st_g); row_g.addWidget(self.btn_pick_g); lay_g.addLayout(row_g); self.list_p = QListWidget(); lay_g.addWidget(self.list_p)

        # ABA 5: TIMERS/CMDS
        self.tab_c = QWidget(); lay_c = QVBoxLayout(self.tab_c); lay_c.addWidget(QLabel("CONFIGURAR ANÚNCIO OU RESPOSTA (Dois cliques para editar):")); row_t = QHBoxLayout(); self.in_tt = QLineEdit(); self.in_tt.setPlaceholderText("Mensagem..."); self.in_ti = QSpinBox(); self.in_ti.setRange(1,60); btn_at = QPushButton("➕ Timer"); btn_at.clicked.connect(self.add_announcement); row_t.addWidget(self.in_tt); row_t.addWidget(self.in_ti); row_t.addWidget(btn_at); lay_c.addLayout(row_t); row_cmd = QHBoxLayout(); self.in_ck = QLineEdit(); self.in_ck.setPlaceholderText("!comando"); self.in_cv = QLineEdit(); self.in_cv.setPlaceholderText("Resposta..."); btn_ac = QPushButton("➕ Criar"); btn_ac.clicked.connect(self.add_custom_cmd); row_cmd.addWidget(self.in_ck); row_cmd.addWidget(self.in_cv); row_cmd.addWidget(btn_ac); lay_c.addLayout(row_cmd); self.list_t = QListWidget(); self.list_t.itemDoubleClicked.connect(self.edit_item); lay_c.addWidget(self.list_t)

        # ABA 6: PERSONA
        self.tab_p = QWidget(); lay_p = QVBoxLayout(self.tab_p); lay_p.addWidget(QLabel("PERSONA DA IA (Como o bot deve se comportar):")); self.in_mood = QTextEdit(); self.in_mood.setPlainText(self.bot_mood); lay_p.addWidget(self.in_mood); btn_save_p = QPushButton("✅ Aplicar Persona"); btn_save_p.clicked.connect(self.save_config); lay_p.addWidget(btn_save_p)

        # ABA 7: FIDELIDADE
        self.tab_loyalty = QWidget(); lay_l = QVBoxLayout(self.tab_loyalty); lay_l.addWidget(QLabel("RANKING DE PARTICIPAÇÃO (Top 20 Usuários):")); self.table_loyalty = QTableWidget(0, 2); self.table_loyalty.setHorizontalHeaderLabels(["Usuário", "Msgs Env."]); self.table_loyalty.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); lay_l.addWidget(self.table_loyalty); row_l = QHBoxLayout(); btn_salve = QPushButton("🎤 MANDAR SALVE (Voz)"); btn_salve.clicked.connect(self.send_shoutout); btn_export = QPushButton("📁 Exportar txt"); btn_export.clicked.connect(self.export_loyalty); row_l.addWidget(btn_salve); row_l.addWidget(btn_export); lay_l.addLayout(row_l)

        # ABA 8: CONFIGURAÇÕES ⚙️
        self.tab_set = QWidget(); lay_set = QVBoxLayout(self.tab_set)
        lay_set.addWidget(QLabel("VOLUME DA IA:")); self.slider_ia = QSlider(Qt.Orientation.Horizontal); self.slider_ia.setRange(0, 100); self.slider_ia.setValue(100); self.slider_ia.valueChanged.connect(self.change_ia_vol); lay_set.addWidget(self.slider_ia)
        lay_set.addWidget(QLabel("MODELO DA IA:")); self.combo_model = QComboBox(); self.combo_model.addItems(["gemini-2.0-flash", "gemini-1.5-flash"]); lay_set.addWidget(self.combo_model)
        lay_set.addWidget(QLabel("SINTETIZADOR DE VOZ:")); self.combo_voice = QComboBox(); self.combo_voice.addItems(["Masculino (Antonio)", "Feminino (Francisca)"]); lay_set.addWidget(self.combo_voice)
        lay_set.addWidget(QLabel("VELOCIDADE DA FALA:")); self.combo_rate = QComboBox(); self.combo_rate.addItems(["Normal", "+20%", "+50%", "-20%"]); lay_set.addWidget(self.combo_rate)
        lay_set.addWidget(QLabel("COOLDOWN IA (Segundos):")); self.spin_cd = QSpinBox(); self.spin_cd.setRange(1, 60); self.spin_cd.setValue(5); lay_set.addWidget(self.spin_cd)
        lay_set.addSpacing(20); btn_update = QPushButton("💜 VERIFICAR ATUALIZAÇÕES NO GITHUB"); btn_update.setObjectName("btn_purple"); btn_update.clicked.connect(lambda: webbrowser.open(self.repo_url)); lay_set.addWidget(btn_update)
        lay_set.addStretch(); btn_save_all = QPushButton("💾 SALVAR TUDO"); btn_save_all.clicked.connect(self.save_config_with_msg); lay_set.addWidget(btn_save_all)

        self.tabs.addTab(self.tab_main, "Painel"); self.tabs.addTab(self.tab_s, "Alertas"); self.tabs.addTab(self.tab_mixer, "Mesa")
        self.tabs.addTab(self.tab_g, "Sorteio"); self.tabs.addTab(self.tab_c, "Timers"); self.tabs.addTab(self.tab_p, "Persona"); self.tabs.addTab(self.tab_loyalty, "Fidelidade"); self.tabs.addTab(self.tab_set, "⚙️")

    # ==============================================================================
    # MOTOR DE EXECUÇÃO (SINCRONIZADO V9.6)
    # ==============================================================================
    async def run_bot_logic(self):
        try:
            api_key = self.input_key.text().strip()
            self.client = genai.Client(api_key=api_key)
            self.chat_session = self.client.chats.create(model=self.combo_model.currentText())
            self.signals.status_api.emit(True)
            # MENSAGEM PEDIDA EM VERDE
            self.signals.log.emit("<font color='#2ecc71'><b>IA TubeVoice conectada com sucesso!</b></font>")
        except Exception as e:
            self.signals.log.emit(f"Erro IA: {e}"); self.bot_running = False; return
        
        l_in = self.input_id.text().strip(); l_id = re.search(r"([^#&?\/\s]{11})", l_in).group(1) if re.search(r"([^#&?\/\s]{11})", l_in) else l_in
        orig_sig = signal.signal; signal.signal = lambda s, h: None; chat = pytchat.create(video_id=l_id); signal.signal = orig_sig
        
        if not chat.is_alive():
            self.signals.status_yt.emit("🔴 Erro", ""); self.bot_running = False; return
        
        self.signals.status_yt.emit("🟢 On", "#2ecc71")
        # MENSAGEM PEDIDA EM VERDE
        self.signals.log.emit("<font color='#2ecc71'><b>Conexão bem sucedida com o YouTube!</b></font>")
        
        while self.bot_running and chat.is_alive():
            ct = time.time()
            for a in self.announcements:
                if ct - a['last_time'] > (a['interval'] * 60): await self.speak(a['text']); a['last_time'] = ct
            for c in chat.get().sync_items():
                u, m = c.author.name, c.message; m_l = m.lower(); self.signals.log.emit(f"<b>{u}:</b> {m}")
                self.loyalty_data[u] = self.loyalty_data.get(u, 0) + 1
                self.update_loyalty_ui()
                if self.is_giveaway_open and "!entrar" in m_l: self.giveaway_list.add(u); self.list_p.clear(); self.list_p.addItems(list(self.giveaway_list))
                await self.speak(f"{u} disse {m}")
                for w, d in self.sound_mappings.items():
                    if w in m_l:
                        v_val = d.get('vol', 100)/100.0; s = pygame.mixer.Sound(d['path']); s.set_volume(v_val); s.play()
                        while pygame.mixer.get_busy(): await asyncio.sleep(0.1)
                res = None; pode = (ct - self.last_request_time) > self.spin_cd.value()
                if m_l in self.custom_commands: res = self.custom_commands[m_l]
                elif "discord" in m_l: res = f"Link: {self.input_discord.text()}"
                elif pode:
                    self.last_request_time = ct
                    try: res = self.chat_session.send_message(f"{self.in_mood.toPlainText()}\n\n{u} disse: {m}").text
                    except: res = None
                if res: await self.speak(res)
            await asyncio.sleep(1)

    # --- AUXILIARES ---
    def update_log_display(self, t): self.log_output.append(t)
    def update_ia_status_label(self, c): self.lbl_api.setText("🟢 On" if c else "🔴 Off"); self.lbl_api.setStyleSheet(f"color: {'#2ecc71' if c else '#ff4444'}; font-weight: bold;")
    def update_youtube_status_label(self, t, c): self.lbl_yt.setText(t); self.lbl_yt.setStyleSheet(f"color: {c}; font-weight: bold;")
    def change_ia_vol(self, val): self.voice_volume = val / 100.0; pygame.mixer.music.set_volume(self.voice_volume)
    def save_config_with_msg(self): self.save_config(); QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso!")
    def update_loyalty_ui(self):
        self.table_loyalty.setRowCount(0); sorted_d = sorted(self.loyalty_data.items(), key=lambda x: x[1], reverse=True)
        for u, c in sorted_d[:20]:
            r = self.table_loyalty.rowCount(); self.table_loyalty.insertRow(r); self.table_loyalty.setItem(r, 0, QTableWidgetItem(u)); self.table_loyalty.setItem(r, 1, QTableWidgetItem(str(c)))
    def send_shoutout(self):
        it = self.table_loyalty.selectedItems()
        if it:
            u = it[0].text(); c = self.loyalty_data.get(u, 0)
            threading.Thread(target=lambda: asyncio.run(self.speak(f"Um salve para {u}, já mandou {c} msgs!")), daemon=True).start()
    def export_loyalty(self):
        with open("ranking.txt", "w") as f:
            for u, c in self.loyalty_data.items(): f.write(f"{u}: {c}\n")
        QMessageBox.information(self, "OK", "Exportado!")
    def browse_sound(self): p, _ = QFileDialog.getOpenFileName(self, "Som", "", "Audio (*.wav *.mp3)"); self.temp_p = p
    def add_sound_manually(self):
        w = self.in_word.text().lower().strip()
        if w and hasattr(self, 'temp_p'):
            dest = os.path.join(self.sounds_dir, os.path.basename(self.temp_p))
            try: shutil.copy2(self.temp_p, dest)
            except: pass
            self.sound_mappings[w] = {"path": dest, "vol": 100}; self.update_table(); self.update_mixer_rack(); self.save_config(); self.in_word.clear()
    def update_table(self):
        self.table.setRowCount(0)
        for w, d in self.sound_mappings.items():
            r = self.table.rowCount(); self.table.insertRow(r); self.table.setItem(r, 0, QTableWidgetItem(w)); self.table.setItem(r, 1, QTableWidgetItem(os.path.basename(d['path'])))
    def update_mixer_rack(self):
        while self.layout_rack.count(): self.layout_rack.takeAt(0).widget().deleteLater()
        for w, d in self.sound_mappings.items():
            rack = QFrame(); rack.setObjectName("MixerChannel"); lay = QVBoxLayout(rack); lay.addWidget(QLabel(w.upper(), alignment=Qt.AlignmentFlag.AlignCenter))
            sld = QSlider(Qt.Orientation.Vertical); sld.setRange(0, 100); sld.setValue(d.get('vol', 100)); sld.setMinimumHeight(150); sld.valueChanged.connect(lambda v, x=w: self.update_sound_vol(x, v)); lay.addWidget(sld, alignment=Qt.AlignmentFlag.AlignHCenter)
            btn = QPushButton("TESTE"); btn.clicked.connect(lambda ch, p=d['path'], x=w: (pygame.mixer.Sound(p).play())); lay.addWidget(btn); self.layout_rack.addWidget(rack)
    def update_sound_vol(self, w, v): self.sound_mappings[w]["vol"] = v; self.save_config()
    def add_announcement(self):
        t, i = self.in_tt.text().strip(), self.in_ti.value()
        if t: self.announcements.append({"text": t, "interval": i, "last_time": time.time()}); self.refresh_list(); self.save_config(); self.in_tt.clear()
    def add_custom_cmd(self):
        k, v = self.in_ck.text().lower().strip(), self.in_cv.text().strip()
        if k and v: self.custom_commands[k] = v; self.refresh_list(); self.save_config(); self.in_ck.clear(); self.in_cv.clear()
    def refresh_list(self):
        self.list_t.clear()
        for a in self.announcements: self.list_t.addItem(f"[Timer: {a['interval']}m] {a['text']}")
        for k, v in self.custom_commands.items(): self.list_t.addItem(f"[CMD: {k}] {v}")
    def edit_item(self, item):
        txt = item.text()
        if "[Timer:" in txt:
            match = re.match(r"\[Timer: (\d+)m\] (.*)", txt)
            if match: self.in_ti.setValue(int(match.group(1))); self.in_tt.setText(match.group(2)); self.announcements = [x for x in self.announcements if f"[Timer: {x['interval']}m] {x['text']}" != txt]
        else:
            match = re.match(r"\[CMD: (.*?)\] (.*)", txt)
            if match: self.in_ck.setText(match.group(1)); self.in_cv.setText(match.group(2)); del self.custom_commands[match.group(1)]
        self.refresh_list(); self.save_config()
    def start_giveaway(self): self.is_giveaway_open = True; self.giveaway_list.clear(); self.list_p.clear(); self.update_log_display("<font color='yellow'>Sorteio aberto!</font>")
    def pick_winner(self):
        if not self.giveaway_list: return
        w = random.choice(list(self.giveaway_list)); self.is_giveaway_open = False; self.update_log_display(f"<font color='#8e44ad'>VENCEDOR: {w}</font>"); threading.Thread(target=lambda: asyncio.run(self.speak(f"O vencedor é {w}!"))).start()
    def toggle_bot(self):
        if not self.bot_running:
            self.save_config(); self.bot_running = True; self.btn_start.setText("⛔ ENCERRAR OPERAÇÃO"); self.btn_start.setStyleSheet("background-color: #c0392b;"); threading.Thread(target=lambda: asyncio.run(self.run_bot_logic()), daemon=True).start()
        else:
            self.bot_running = False; self.btn_start.setText("🚀 INICIAR OPERAÇÃO COMPLETA"); self.btn_start.setStyleSheet("background-color: #27ae60;"); self.update_ia_status_label(False); self.update_youtube_status_label("🔴 Off", "#ff4444")
    def save_config(self):
        v = self.combo_voice.currentText()
        c = {"key": self.input_key.text(), "id": self.input_id.text(), "discord": self.input_discord.text(), "sounds": self.sound_mappings, "timers": self.announcements, "cmds": self.custom_commands, "mood": self.in_mood.toPlainText(), "voice": v, "vol": self.slider_ia.value(), "cd": self.spin_cd.value(), "model": self.combo_model.currentText(), "loyalty": self.loyalty_data}
        with open(self.config_file, 'w') as f: json.dump(c, f, indent=4)
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    c = json.load(f); self.input_key.setText(c.get("key", "")); self.input_id.setText(c.get("id", "")); self.input_discord.setText(c.get("discord", ""))
                    self.sound_mappings = c.get("sounds", {}); self.announcements = c.get("timers", []); self.custom_commands = c.get("cmds", {})
                    self.bot_mood = c.get("mood", self.bot_mood); self.slider_ia.setValue(c.get("vol", 100)); self.spin_cd.setValue(c.get("cd", 5)); self.combo_model.setCurrentText(c.get("model", "gemini-2.0-flash"))
                    self.loyalty_data = c.get("loyalty", {}); self.combo_voice.setCurrentText(c.get("voice", "Masculino (Antonio)")); self.update_table(); self.update_mixer_rack(); self.refresh_list(); self.in_mood.setPlainText(self.bot_mood); self.update_loyalty_ui()
            except: pass
    async def speak(self, t):
        try:
            pygame.mixer.music.unload(); f = f"v_{int(time.time())}.mp3"
            v = "pt-BR-AntonioNeural" if "Antonio" in self.combo_voice.currentText() else "pt-BR-FranciscaNeural"
            await edge_tts.Communicate(t, v).save(f)
            pygame.mixer.music.load(f); pygame.mixer.music.set_volume(self.voice_volume); pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): await asyncio.sleep(0.1)
            pygame.mixer.music.unload(); os.remove(f)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv); win = TubeVoiceAI(); win.show(); sys.exit(app.exec())
