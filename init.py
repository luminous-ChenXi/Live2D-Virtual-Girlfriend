import os
import ast
import toml
import json

with open('config.toml', 'r', encoding='utf-8-sig') as f:
    config_text = f.read()
config = toml.loads(config_text)

with open(config['character_json'], 'r', encoding='utf-8') as f:
    character = json.load(f)
dir = os.path.dirname(config['character_json'])
character["live2d_model"] = os.path.join(dir, character["live2d_model"])
character["ref_audio"] = os.path.join(dir, character["ref_audio"])
character["system_prompt"] = os.path.join(dir, character["system_prompt"])
character["exp"] = os.path.join(dir, character["exp"])

class Global:
    # 全局变量
    text_lang = 'zh'

setattr(Global, 'character', character)
for key, value in config.items():
    if key == 'hot_word':
        value = ast.literal_eval(value)
    setattr(Global, key, value)