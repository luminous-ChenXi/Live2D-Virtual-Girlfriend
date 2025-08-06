import re
import os
import sys
import time
import json
import ctypes
import load_model
from queue import Queue
from openai import OpenAI
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtCore import Qt, QPoint
from threading import Thread
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QOpenGLWidget, QApplication, QLabel, QWidget
import live2d.v3 as live2d
from init import Global
from func_queue import FuncQueue
from GUIAnimator import *
from animator import *
from audio_record import speech_recognition
from tts import AudioQueue, gptsovits_audio, text_process

def terminate_thread(thread):
    if not thread.is_alive():
        return
    
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)

class Live2DCanvas(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ciallo～(∠・ω< )⌒★")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.t = None
        Global.sign1 = False
        Global.exist = True
        self.send_audio_text = None
        self.double_hit = [0, '']

        win_width, win_height = Global.win_width, Global.win_height
        self.resize(win_width, win_height)
        screen = QApplication.primaryScreen().geometry()
        self.screen_width, self.screen_height = screen.width(), screen.height()
        x = (self.screen_width - win_width) // 2
        y = (self.screen_height - win_height) // 2
        self.move(x, y)

        self.model: None | live2d.LAppModel = None
        self.dragging = False
        self.drag_position = QPoint()

        # 字幕控件
        self.subtitle_window = SubtitleWindow()
        self.subtitle_window.show()
        self.raise_timer = QTimer()
        self.raise_timer.timeout.connect(self.raise_subtitle)
        self.raise_timer.start(1000)

        Global.animator1 = SubtitleAnimator1(self.subtitle_window.subtitle_label)
        Global.animator2 = SubtitleAnimator2(self.subtitle_window.subtitle_label)
        Global.func_queue1 = FuncQueue(max_t=2)
        Global.func_queue2 = FuncQueue(Global.animator2.cancel_fade_out, Global.animator2.schedule_fade_out)

        self.create_tray_icon()

    def raise_subtitle(self):
        self.subtitle_window.raise_()
    
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = QIcon("icon.ico")
        self.tray_icon.setIcon(icon)
        tray_menu = QMenu()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Ciallo～(∠・ω< )⌒★")
        self.tray_icon.show()
    
    def quit_app(self):
        self.tray_icon.hide()
        os._exit(0)

    def initializeGL(self):
        live2d.glInit()
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(Global.character["live2d_model"])
        self.model.Resize(self.width(), self.height())
        self.model.SetAutoBlinkEnable(False)
        self.model.SetAutoBreathEnable(True)

        Global.audio_queue = AudioQueue(self.model)

        Global.live2d_animator = Live2dAnimator(self.model)
        blink_animator = BlinkAnimator()
        Global.live2d_animator.add(100, blink_animator)
        eyeball_animator = EyeBallAnimator()
        Global.live2d_animator.add(5, eyeball_animator)
        # angleXY_animator = AngleAnimator()
        # Global.live2d_animator.add(5, angleXY_animator)
        body_angleXZ_animator = BodyAngleAnimator()
        Global.live2d_animator.add(5, body_angleXZ_animator)
        Global.emotion_animator = EmotionAnimator()
        Global.live2d_animator.add(5, Global.emotion_animator)
        Global.expression_animator = ExpressionAnimator()
        Global.live2d_animator.add(5, Global.expression_animator)
        Global.appearance_animator = AppearanceAnimator(self)
        Global.live2d_animator.add(5, Global.appearance_animator)
        if Global.mixanimator_wait != -1:
            mix_animator = MixAnimator()
            Global.live2d_animator.add(6, mix_animator)
        
        self.startTimer(int(1000 / 60)) # 渲染帧率

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if self.model is None:
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.x(), event.y()
            hit_parts = self.model.HitPart(x, y)
            if hit_parts:
                hit_part = Global.parts[hit_parts[0]]
                if hit_part == self.double_hit[1] and time.time() - self.double_hit[0] < 0.4:
                    print('触摸了', hit_part)
                    if Global.func_queue1.t:
                        for t0 in Global.func_queue1.t:
                            terminate_thread(t0)
                        Global.func_queue1.__init__()
                    if Global.audio_queue.q:
                        Global.audio_queue.q = {} 
                    if self.t:
                        terminate_thread(self.t)
                        self.t = None
                    self.t = Thread(target=self.send_audio_text, args=(f'[触摸了你的{hit_part}]',))
                    self.t.start()
                self.double_hit = [time.time(), hit_part]

                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                self.dragging = True
            else:
                self.dragging = False
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
        super().mouseReleaseEvent(event)
        
    def timerEvent(self, _):
        Global.live2d_animator.update()
        self.update()

    def on_draw(self):
        live2d.clearBuffer()
        self.model.Draw()

    def paintGL(self):
        self.model.Update()
        self.on_draw()
    
    def closeEvent(self, event):
        os._exit(0)

class SubtitleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_window()
        self.setup_subtitle()
        
    def setup_window(self):
        self.setWindowTitle("字幕窗口")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
    def setup_subtitle(self):
        self.subtitle_label = QLabel(self)
        self.subtitle_label.setTextFormat(Qt.TextFormat.RichText)
        
        font_id = QFontDatabase.addApplicationFont("字体.ttf")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        else:
            font_family = "Arial"
            
        self.subtitle_label.setStyleSheet(f'''
            font-size: 96px; 
            font-family: "{font_family}";
            color: white;
            background-color: transparent;
            padding: 20px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 200);
        ''')
        
        screen_width = self.width()
        screen_height = self.height()
        label_width = screen_width - 200
        label_height = 150
        
        x = (screen_width - label_width) // 2
        y = screen_height - label_height - 100
        
        self.subtitle_label.setGeometry(x, y, label_width, label_height)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.subtitle_label.setText("")

class Agent:
    def __init__(self, win):
        with open(Global.character["system_prompt"], 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        self.win = win
        Global.exp_queue = Queue()
        if Global.character["exp"]:
            with open(Global.character["exp"], 'r', encoding='utf-8') as f:
                self.exp = json.load(f)
        else:
            self.exp = {}
        
        if "watermark" in Global.character:
            self.win.model.SetParameterValue(Global.character["watermark"], 1, 1)
    
        live2d_model = Global.character["live2d_model"]
        dirname = os.path.dirname(live2d_model)
        basename = os.path.basename(live2d_model)
        cdi3_path = os.path.join(dirname, basename.split('.')[0]+'.cdi3.json')
        with open(cdi3_path, 'r', encoding='utf-8') as f:
            cdi3_json = json.load(f)
        Global.parts = {}
        for i in cdi3_json["Parts"]:
            Global.parts[i["Id"]] = i["Name"]

        with open(live2d_model, 'r', encoding='utf-8') as f:
            live2d_json = json.load(f)
        
        Global.exp_params = {}
        if "Expressions" in live2d_json["FileReferences"]:
            for i in live2d_json["FileReferences"]["Expressions"]:
                exp_path = os.path.join(dirname, i["File"])
                with open(exp_path, 'r', encoding='utf-8') as f:
                    exp_json = json.load(f)
                Global.exp_params[i["Name"]] = [exp_json["Parameters"][0]["Id"], exp_json["Parameters"][0]["Value"]]
        
        self.exp['正常'] = '正常表情'
        self.speed_factor = Global.character["speed_factor"]
        self.prompt_text = Global.character["prompt_text"]
        self.prompt_lang = Global.character["prompt_lang"]
        self.ref_audio = os.path.realpath(Global.character["ref_audio"])

        language = {'zh':'中文', 'ja':'日文', 'en':'英文'}
        examples = {'zh':'你说的话。{"happy":5, "exp":"正常"}', 'ja':'あなたが言ったこと。{"happy":5, "exp":"正常"}', 'en':'what you say.{"happy":5, "exp":"正常"}'}
        self.messages = [{'role':'system', 'content':prompt+f'\nexpression = {self.exp}\n'+'\n每次都必须在输出的末尾加上: {"happy":int, "exp":str}。其中happy的值范围为[0, 10]，代表着你当前的开心值。其中exp请从expression中选择一个值，代表着你当前的表情。'+f'\n**最后请你必须保持只输出 {language[self.prompt_lang]}，即便用户用别的语言与你交流**\n你的输出格式示例: {examples[self.prompt_lang]}'}]
        self.client = OpenAI(
            base_url=Global.required['base_url'],
            api_key=Global.required['api_key']
        )

        self.memory_save = []
    
    def send_audio_text(self, text, img=None):
        self.t = time.time()
        results = Global.memory.semantic_search(text, top_k=Global.memory_top_k, similarity_threshold=Global.memory_similarity_threshold)
        print(f"\n记忆检索(耗时: {time.time()-self.t:.2f}s) {len(results)}")

        content = []
        if img:
            content.append({'type': 'image_url', 'image_url': {'url': f"data:image/png;base64,{img}"}, 'max_pixels': Global.required['max_pixels']})
        if results:
            memory_context = Global.memory.build_context(results)
            memory_prompt = f"以下是与当前对话相关的记忆片段，这些是你过往的经历和记忆，无关记忆请忽略：\n{memory_context}\n---\n用户消息：{text}"
            content.append({"type": "text", "text": memory_prompt})
        else:
            content.append({"type": "text", "text": text})
        self.messages.append({'role':'user', 'content':content})
        self.memory_save.append({'role':'user', 'content':text})

        self.t = time.time()

        response = self.client.chat.completions.create(
            model=Global.required['chat_model'],
            messages=self.messages,
            stream=True,
            temperature=Global.required['temperature'],
            top_p=Global.required['top_p'],
            max_tokens=Global.required['max_tokens'],
            extra_body={
                "thinking": {"type": "disabled"}
            },
        )

        temp = ''
        message_content = ''
        for chunk in response:
            if chunk.choices:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    for content_chr in content:
                        if len(temp) > Global.cut_length and content_chr in ['。', '，', '！', '？', '、', '~', '.', '…', '!', '?', '\n']:
                            print(f"\nLLM(耗时: {time.time()-self.t:.2f}s) {temp}")
                            self.t = time.time()

                            text, text_lang, pre_text = text_process(temp, Global.text_lang, self.prompt_lang)
                            if text:
                                Global.func_queue1.add(
                                    gptsovits_audio,
                                    (pre_text, text, text_lang, self.ref_audio, self.prompt_text, self.prompt_lang, self.speed_factor)
                                )
                            temp = ''
                        else:
                            temp += content_chr
                    message_content += content
                    
                    match = re.findall(r'\{[^)]*\}', message_content)
                    for i in match:
                        try:
                            json_data = json.loads(i)
                        except:
                            json_data = {}
                        print(json_data)
                        if 'happy' in json_data:
                            Global.emotion_animator.start(json_data['happy'])
                        if 'exp' in json_data:
                            if json_data['exp'] in self.exp.keys() and json_data['exp'] != '正常':
                                Global.exp_queue.put(json_data['exp'])

        if temp:
            print(f"\nLLM(耗时: {time.time()-self.t:.2f}s) {temp}")
            self.t = time.time()

            text, text_lang, pre_text = text_process(temp, Global.text_lang, self.prompt_lang)
            if text:
                Global.func_queue1.add(
                    gptsovits_audio,
                    (pre_text, text, text_lang, self.ref_audio, self.prompt_text, self.prompt_lang, self.speed_factor)
                )

        self.messages.append({'role':'assistant', 'content':message_content})
        if len(self.messages) >= Global.context_length:
            self.messages.pop(1)
            self.messages.pop(1)

        self.memory_save.append({'role':'assistant', 'content':message_content})
        if len(self.memory_save) >= Global.save_memory_steps:
            Thread(target=Global.memory.add_conversation, args=(self.memory_save.copy(),)).start()
            self.memory_save = []

if __name__ == '__main__':

    live2d.init()
    app = QApplication(sys.argv)
    win = Live2DCanvas()
    win.show()

    my_agent = Agent(win)
    win.send_audio_text = my_agent.send_audio_text
    Thread(target=speech_recognition, args=(my_agent.send_audio_text,), daemon=True).start()

    sys.exit(app.exec())