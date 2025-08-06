import time
import math
import noise
import random
from init import Global
from calculation import *
import numpy as np

class Live2dAnimator:
    def __init__(self, model):
        self.model = model
        self.priority_list = []
        self.params = {}
        self.blacklist = []
        for i in range(self.model.GetParameterCount()):
            param = self.model.GetParameter(i)
            self.params[param.id] = param.value
        print(self.params)
        
    def add(self, priority, animator):
        for i in range(len(self.priority_list)):
            if self.priority_list[i][0] >= priority:
                break
        else:
            i = len(self.priority_list)
        
        self.priority_list.insert(i, (priority, animator))
    
    def update(self):
        results = []
        for i in range(len(self.priority_list)-1, -1, -1):
            animator = self.priority_list[i][1]
            if animator.__class__.__name__ not in self.blacklist:
                result = animator.update()
                if result is None:
                    self.priority_list.pop(i)
                else:
                    results.extend(result)
        
        for param, value, weight in results:
            if param in self.params:
                self.params[param] = self.params[param] * (1 - weight) + value * weight
                self.model.SetParameterValue(param, value, weight)

class BlinkAnimator:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.flag = None
        self.k = None
        self.reset()
    
    def reset(self):
        self.k = min(1, random.uniform(0.7, 1.5))
        if random.random() > 0.3:
            self.flag = 0
        else:
            self.flag = 1
        self.flag1 = 0
        self.interval = 0.2
        self.timer = time.time()
        self.wait = False

    def update(self):
        t = (time.time() - self.timer) / self.interval
        if self.wait:
            if t > self.wait_time:
                self.reset()
        else:
            # 普通眨眼
            if self.flag == 0:
                if t <= 1:
                    eased_t = sine(t)
                    if self.flag1 == 0:
                        self.flag1 += 1
                        self.s1 = self.params['ParamEyeLOpen']
                        self.s2 = self.params['ParamEyeROpen']
                    return [
                        ('ParamEyeLOpen', round(linearScale1(eased_t, 0, 1, self.s1, 0), 2), 1),
                        ('ParamEyeROpen', round(linearScale1(eased_t, 0, 1, self.s2, 0), 2), 1),
                    ]
                elif 1 < t <= 2:
                    t -= 1
                    eased_t = sine(t)
                    if self.flag1 <= 1:
                        self.flag1 += 2 - self.flag1
                        self.s1 = self.params['ParamEyeLOpen']
                        self.s2 = self.params['ParamEyeROpen']
                    return [
                        ('ParamEyeLOpen', round(linearScale1(eased_t, 0, 1, self.s1, 1*self.k), 2), 1),
                        ('ParamEyeROpen', round(linearScale1(eased_t, 0, 1, self.s2, 1*self.k), 2), 1),
                    ]
                else:
                    self.wait = True
                    if random.random() > 0.3:
                        self.wait_time = random.randint(20, 40)
                    else:
                        self.wait_time = 0
                    self.timer = time.time()

            elif self.flag == 1:
                if t <= 1:
                    eased_t = sine(t)
                    if self.flag1 == 0:
                        self.flag1 += 1
                        self.s1 = self.params['ParamEyeLOpen']
                        self.s2 = self.params['ParamEyeROpen']
                    return [
                        ('ParamEyeLOpen', round(linearScale1(eased_t, 0, 1, self.s1, self.k), 2), 1),
                        ('ParamEyeROpen', round(linearScale1(eased_t, 0, 1, self.s2, self.k), 2), 1),
                    ]
                else:
                    self.wait = True
                    if random.random() > 0.3:
                        self.wait_time = random.randint(20, 40)
                    else:
                        self.wait_time = 0
                    self.timer = time.time()

        return []

class EyeBallAnimator:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.reset()
    
    def reset(self):
        self.flag = 0
        self.move_duration = 0.15
        self.fixation_time = random.uniform(1.5, 4.0)
        self.micro_movement_time = random.uniform(0.3, 0.8)
        
        self.X = self.params['ParamEyeBallX']
        self.Y = self.params['ParamEyeBallY']
        self.target_X = 0
        self.target_Y = 0
        self.start_X = 0
        self.start_Y = 0
        
        self.timer = time.time()
        self.micro_timer = time.time()
        
        self.micro_amplitude = 0.05
        self.drift_X = 0
        self.drift_Y = 0
    
    def generate_natural_target(self):
        angle = random.uniform(0, 2 * math.pi)
        
        h_range = random.uniform(0.3, 1.0)
        v_range = random.uniform(0.2, 0.6)
        
        self.target_X = h_range * math.cos(angle)
        self.target_Y = v_range * math.sin(angle)
        
        self.target_X = max(-1, min(1, self.target_X + random.uniform(-0.1, 0.1)))
        self.target_Y = max(-0.5, min(0.5, self.target_Y + random.uniform(-0.05, 0.05)))
    
    def add_micro_movements(self):
        current_time = time.time()
        
        if current_time - self.micro_timer > self.micro_movement_time:
            self.micro_movement_time = random.uniform(0.2, 0.6)
            self.micro_timer = current_time
            
            self.drift_X += random.uniform(-0.02, 0.02)
            self.drift_Y += random.uniform(-0.01, 0.01)
            
            self.drift_X = max(-self.micro_amplitude, min(self.micro_amplitude, self.drift_X))
            self.drift_Y = max(-self.micro_amplitude, min(self.micro_amplitude, self.drift_Y))
        
        tremor_X = math.sin(current_time * 30) * 0.005
        tremor_Y = math.cos(current_time * 25) * 0.003
        
        return tremor_X + self.drift_X, tremor_Y + self.drift_Y
    
    def update(self):
        current_time = time.time()
        elapsed = current_time - self.timer
        
        if self.flag == 0:
            if elapsed > self.fixation_time:
                self.flag = 2
                self.timer = current_time
                self.start_X = self.X
                self.start_Y = self.Y
                self.generate_natural_target()
                
                distance = math.sqrt((self.target_X - self.start_X)**2 + (self.target_Y - self.start_Y)**2)
                self.move_duration = 0.1 + distance * 0.1
                
        elif self.flag == 2:
            if elapsed <= self.move_duration:
                progress = elapsed / self.move_duration
                eased_progress = cubic(progress)
                
                self.X = self.start_X + (self.target_X - self.start_X) * eased_progress
                self.Y = self.start_Y + (self.target_Y - self.start_Y) * eased_progress
                
            else:
                self.X = self.target_X
                self.Y = self.target_Y
                self.flag = 1
                self.timer = current_time
                self.fixation_time = random.uniform(1.0, 3.5)
                
        elif self.flag == 1:
            if elapsed > self.fixation_time:
                self.flag = 0
                self.timer = current_time
                self.fixation_time = random.uniform(0.5, 1.0)
        
        micro_X, micro_Y = self.add_micro_movements()
        final_X = self.X + micro_X
        final_Y = self.Y + micro_Y
        
        return [
            ('ParamEyeBallX', round(final_X, 3), 1),
            ('ParamEyeBallY', round(final_Y, 3), 1)
        ]

class AngleAnimator:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.reset()
    
    def reset(self):
        self.flag = 0
        self.interval = random.uniform(1.5, 3.0)
        self.wait = random.uniform(3, 8)
        self.target_X = self.params['ParamAngleX']
        self.target_Y = self.params['ParamAngleY']
        self.timer = time.time()

        self.noise_offset_x = random.uniform(0, 1000)
        self.noise_offset_y = random.uniform(0, 1000)
        self.micro_movement_scale = 0.02
        self.last_update_time = time.time()
        
        self.easing_functions = [
            cubic,
            quart,
            sine
        ]
        self.current_easing = random.choice(self.easing_functions)
    
    def add_micro_movement(self, base_x, base_y):
        current_time = time.time()
        noise_x = noise.pnoise1(current_time * 0.5 + self.noise_offset_x) * self.micro_movement_scale
        noise_y = noise.pnoise1(current_time * 0.5 + self.noise_offset_y) * self.micro_movement_scale
        
        return base_x + noise_x * 30, base_y + noise_y * 30
    
    def update(self):
        current_time = time.time()
        
        if self.flag == 1:
            t = (current_time - self.timer) / self.interval
            
            if t >= 1.0:
                self.flag = 0
                self.timer = current_time
                self.wait = random.uniform(2, 6)

                current_x = self.params['ParamAngleX']
                current_y = self.params['ParamAngleY']
                self.target_X = current_x + random.uniform(-2, 2)
                self.target_Y = current_y + random.uniform(-2, 2)

                self.target_X = max(-30, min(30, self.target_X))
                self.target_Y = max(-30, min(30, self.target_Y))
            else:
                eased_t = self.current_easing(t)
                
                base_x = linearScale1(eased_t, 0, 1, self.pre_X, self.target_X)
                base_y = linearScale1(eased_t, 0, 1, self.pre_Y, self.target_Y)
                
                final_x, final_y = self.add_micro_movement(base_x, base_y)
                
                return [
                    ('ParamAngleX', round(final_x, 2), 1),
                    ('ParamAngleY', round(final_y, 2), 1)
                ]
                
        elif self.flag == 0:
            if current_time - self.timer > self.wait:
                self.flag = 1
                self.timer = current_time
                self.interval = random.uniform(1.2, 2.8)
                self.current_easing = random.choice(self.easing_functions)
                
                self.pre_X = self.params['ParamAngleX']
                self.pre_Y = self.params['ParamAngleY']
                
                eye_influence = 0.7
                random_influence = 0.3
                
                eye_offset_x = self.params['ParamEyeBallX'] * eye_influence * 20
                eye_offset_y = self.params['ParamEyeBallY'] * eye_influence * 20
                random_offset_x = random.uniform(-6, 6) * random_influence
                random_offset_y = random.uniform(-4, 4) * random_influence
                
                self.target_X = self.pre_X + eye_offset_x + random_offset_x
                self.target_Y = self.pre_Y + eye_offset_y + random_offset_y
                
                self.target_X = max(-30, min(30, self.target_X))
                self.target_Y = max(-30, min(30, self.target_Y))
            else:
                current_x = self.params['ParamAngleX']
                current_y = self.params['ParamAngleY']
                final_x, final_y = self.add_micro_movement(current_x, current_y)
                return [
                    ('ParamAngleX', round(final_x, 2), 1),
                    ('ParamAngleY', round(final_y, 2), 1)
                ]
        
        return []

class BodyAngleAnimator:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.flag = None
        self.k = None
        self.reset()
    
    def reset(self):
        self.wait = False
        if self.k is None or self.k and random.random() > 0.3:
            self.k = random.uniform(-0.8, 0.8)
        if self.flag is None or self.flag and random.random() > 0.7:
            self.wait = True
            self.flag = random.choice(['x', 'y', 'z'])
        self.flag1 = 0
        self.wait_time = random.randint(0, 5)
        self.timer = time.time()
        self.interval = 0.5

    def update(self):
        t = (time.time() - self.timer) / self.interval
        if self.wait:
            if t > self.wait_time:
                self.wait = False
                self.reset()
        else:
            if self.flag == 'x':
                if t <= 1:
                    eased_t = sine(t)
                    if self.flag1 == 0:
                        self.flag1 += 1
                        self.s1 = self.params['ParamBodyAngleX']
                        self.s2 = self.params['ParamAngleX']
                    return [
                        ('ParamBodyAngleX', round(linearScale1(eased_t, 0, 1, self.s1, 10*self.k), 2), 1),
                        ('ParamAngleX', round(linearScale1(eased_t, 0, 1, self.s2, 30*self.k), 2), 1),
                    ]
                elif 1 < t <= 2:
                    t -= 1
                    eased_t = sine(t)
                    if self.flag1 == 1:
                        self.flag1 += 1
                        self.s1 = self.params['ParamBodyAngleX']
                        self.s2 = self.params['ParamAngleX']
                    return [
                        ('ParamBodyAngleX', round(linearScale1(eased_t, 0, 1, self.s1, 0), 2), 1),
                        ('ParamAngleX', round(linearScale1(eased_t, 0, 1, self.s2, 0), 2), 1),
                    ]
                else:
                    self.reset()
                    
            elif self.flag == 'y':
                if t <= 1:
                    eased_t = sine(t)
                    if self.flag1 == 0:
                        self.flag1 += 1
                        self.s1 = self.params['ParamBodyAngleY']
                        self.s2 = self.params['ParamAngleY']
                    return [
                        ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s1, 10*self.k), 2), 1),
                        ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s2, 30*self.k), 2), 1),
                    ]
                elif 1 < t <= 2:
                    t -= 1
                    eased_t = sine(t)
                    if self.flag1 == 1:
                        self.flag1 += 1
                        self.s1 = self.params['ParamBodyAngleY']
                        self.s2 = self.params['ParamAngleY']
                    return [
                        ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s1, 0), 2), 1),
                        ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s2, 0), 2), 1),
                    ]
                else:
                    self.reset()
                    
            elif self.flag == 'z':
                if t <= 1:
                    eased_t = sine(t)
                    if self.flag1 == 0:
                        self.flag1 += 1
                        self.s1 = self.params['ParamBodyAngleZ']
                        self.s2 = self.params['ParamAngleZ']
                    return [
                        ('ParamBodyAngleZ', round(linearScale1(eased_t, 0, 1, self.s1, 10*self.k), 2), 1),
                        ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s2, 30*self.k), 2), 1),
                    ]
                elif 1 < t <= 2:
                    t -= 1
                    eased_t = sine(t)
                    if self.flag1 == 1:
                        self.flag1 += 1
                        self.s1 = self.params['ParamBodyAngleZ']
                        self.s2 = self.params['ParamAngleZ']
                    return [
                        ('ParamBodyAngleZ', round(linearScale1(eased_t, 0, 1, self.s1, 0), 2), 1),
                        ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s2, 0), 2), 1),
                    ]
                else:
                    self.reset()
        
        return []

class AppearanceAnimator:
    def __init__(self, win):
        self.params = Global.live2d_animator.params
        self.win = win
        self.flag = 1
    
    def reset(self, k):
        self.k = k
        self.flag1 = 0
        if self.k == 1:
            Global.exist = True
            self.win.show()
            self.interval = 1
        else:
            self._y = self.win.pos().y()
            self.interval = 2
        self.timer = time.time()
        self.flag = 0
    
    def update(self):
        if self.flag == 0:
            t = (time.time() - self.timer) / self.interval
            if t <= 1:
                eased_t = sine(t)
                x = self.win.pos().x()
                if self.k == 1:
                    y = int(linearScale1(eased_t, 0, 1, self.win.screen_height, self._y))
                else:
                    y = int(linearScale1(eased_t, 0, 1, self._y, self.win.screen_height))
                self.win.move(x, y)

                if self.flag1 == 0:
                    self.flag1 += 1
                    self.s1 = self.params['ParamBodyAngleY']
                    self.s2 = self.params['ParamAngleY']
                    self.s3 = self.params['ParamEyeBallY']
                return [
                    ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s1, 10*self.k), 2), 1),
                    ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s2, 30*self.k), 2), 1),
                    ('ParamEyeBallY', round(linearScale1(eased_t, 0, 1, self.s3, -1*self.k), 2), 1),
                ]
            if 1 < t <= 2:
                t -= 1
                eased_t = sine(t)
                if self.flag1 == 1:
                    self.flag1 += 1
                    self.s1 = self.params['ParamBodyAngleY']
                    self.s2 = self.params['ParamAngleY']
                    self.s3 = self.params['ParamEyeBallY']
                return [
                    ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s1, 0), 2), 1),
                    ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s2, 0), 2), 1),
                    ('ParamEyeBallY', round(linearScale1(eased_t, 0, 1, self.s3, 0), 2), 1),
                ]
            else:
                if self.k != 1:
                    Global.exist = False
                    self.win.hide()
                self.flag = 1
        
        return []

class ExpressionAnimator:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.tasks = []

    def update(self):
        if self.tasks:
            result = []
            for i in range(len(self.tasks)-1, -1, -1):
                (param_id, param_max), timer, fadeout = self.tasks[i]
                fadeout /= 0.5
                t = (time.time() - timer) / 0.5
                if t <= 1:
                    result.append((param_id, linearScale1(t, 0, 1, 0, param_max), 1))
                elif 1 < t <= 1 + fadeout:
                    pass
                elif 1 + fadeout < t <= 2 + fadeout:
                    t -= fadeout
                    result.append((param_id, linearScale1(t, 1, 2, param_max, 0), 1))
                else:
                    result.append((param_id, 0, 1))
                    self.tasks.pop(i)

            return result

        return []
    
    def add(self, param, fadeout):
        self.tasks.append((param, time.time(), fadeout))

class EmotionAnimator:
    def __init__(self):
        self.params = Global.live2d_animator.params

        self.ParamMouthForm = 0
        self.ParamBrowLForm = 0
        self.ParamBrowRForm = 0

        self.interval = 1
        self.flag = False
        self.flag1 = 0
    
    def update(self):
        if self.flag:
            t = (time.time() - self.timer) / self.interval
            if t > 1.0:
                self.flag = False
            else:
                eased_t = sine(t)
                if self.flag1 == 0:
                    self.flag1 += 1
                    self.s1 = self.params['ParamMouthForm']
                    self.s2 = self.params['ParamBrowLForm']
                    self.s3 = self.params['ParamBrowRForm']
                return [
                    ('ParamMouthForm', round(linearScale1(eased_t, 0, 1, self.s1, self.ParamMouthForm), 2), 1),
                    ('ParamBrowLForm', round(linearScale1(eased_t, 0, 1, self.s2, self.ParamBrowLForm), 2), 1),
                    ('ParamBrowRForm', round(linearScale1(eased_t, 0, 1, self.s3, self.ParamBrowRForm), 2), 1)
                ]

        return []
    
    def start(self, happy):
        self.ParamMouthForm = linearScale1(happy, 0, 10, -1, 1)
        self.ParamBrowLForm = linearScale1(happy, 0, 10, -1, 1)
        self.ParamBrowRForm = linearScale1(happy, 0, 10, -1, 1)

        self.timer = time.time()
        self.flag = True

class MixAnimator:
    def __init__(self):
        self.flag = False
        self.timer = time.time()
        self.animators_sample = []

        self.wait = Global.mixanimator_wait
        self.animators = {
            Animator1: ['ParamBrowLY', 'ParamBrowLAngle', 'ParamBrowRY', 'ParamBrowRAngle', 'Param51'],
            Animator2: ['ParamBodyAngleY', 'ParamAngleY', 'ParamEyeBallY'],
            Animator3: ['ParamBodyAngleZ', 'ParamAngleZ'],
            Animator4: ['ParamMouthOpenY'],
            Animator5: ['ParamBodyAngleX', 'ParamAngleX'],
            Animator6: ['ParamBrowLY', 'ParamBrowLAngle', 'ParamBrowRY', 'ParamBrowRAngle'],
            Animator7: ['ParamEyeLOpen', 'ParamEyeROpen'],
            Animator8: ['ParamAngleZ'],
        }

        weight_sum = sum(Global.mixanimator_weight)
        self.p = [i / weight_sum for i in Global.mixanimator_weight]
        self.params = Global.live2d_animator.params
        for i in self.animators.values():
            for j in i:
                if j not in self.params:
                    self.params[j] = 0

        self.max_sample = Global.mixanimator_max_sample
        self.max_sample = min(len(self.animators), self.max_sample)
    
    def update(self):
        if self.flag:
            flag1 = False
            results = []
            for animator in self.animators_sample:
                result = animator.update()
                if not result is None:
                    flag1 = True
                    results += result
            
            if not flag1:
                self.flag = False
                self.timer = time.time()
                self.wait = 0

                for attr_name in dir(Global):
                    attr_value = getattr(Global, attr_name)
                    if attr_value.__class__.__name__ in Global.live2d_animator.blacklist:
                        attr_value.reset()

                Global.live2d_animator.blacklist = []
                return []
            return results

        elif time.time() - self.timer > self.wait:
            self.flag = True
            self.animators_sample = np.random.choice(
                list(self.animators.keys()), 
                size=random.randint(1, self.max_sample), 
                p=self.p, 
                replace=False
            ).tolist()

            related_params = set([])
            for i in range(len(self.animators_sample)-1, -1, -1):
                key = self.animators_sample[i]
                for param in self.animators[key]:
                    if param in related_params:
                        self.animators_sample.pop(i)
                        break
                    else:
                        related_params.add(param)
            
            for key in self.animators_sample:
                for i in self.animators[key]:
                    a = ''
                    if i in ['ParamBodyAngleX', 'ParamBodyAngleY', 'ParamBodyAngleZ', 'ParamAngleX', 'ParamAngleY', 'ParamAngleZ']:
                        a = 'BodyAngleAnimator'
                    elif i in ['ParamEyeBallX', 'ParamEyeBallY']:
                        a = 'EyeBallAnimator'
                    elif i in ['ParamEyeLOpen', 'ParamEyeROpen']:
                        a = 'BlinkAnimator'

                    if a and a not in Global.live2d_animator.blacklist:
                        Global.live2d_animator.blacklist.append(a)
            
            self.animators_sample = [animator() for animator in self.animators_sample]
        
        return []

class Animator1:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = 1
        self.duration = random.uniform(0, 1)
        self.R_L = random.choice([-1, 1])
        self.flag1 = 0
        if self.R_L == 1:
            self.R = 'R'
            self.L = 'L'
        else:
            self.R = 'L'
            self.L = 'R'
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = cubic(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params[f'ParamBrow{self.L}Y']
                self.s2 = self.params[f'ParamBrow{self.L}Angle']
                self.s3 = self.params[f'ParamBrow{self.R}Y']
                self.s4 = self.params[f'ParamBrow{self.R}Angle']
                self.s5 = self.params['Param51']
            return [
                (f'ParamBrow{self.L}Y', round(linearScale1(eased_t, 0, 1, self.s1, 1), 2), 1),
                (f'ParamBrow{self.L}Angle', round(linearScale1(eased_t, 0, 1, self.s2, -1), 2), 1),
                (f'ParamBrow{self.R}Y', round(linearScale1(eased_t, 0, 1, self.s3, 0), 2), 1),
                (f'ParamBrow{self.R}Angle', round(linearScale1(eased_t, 0, 1, self.s4, 0), 2), 1),
                ('Param51', round(linearScale1(eased_t, 0, 1, self.s5, self.R_L), 2), 1),
            ]
        elif t < self.duration + 1:
            return []
        elif self.duration + 1 <= t < self.duration + 2:
            t -= self.duration + 1
            eased_t = cubic(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s6 = self.params['ParamBrowLY']
                self.s7 = self.params['ParamBrowLAngle']
                self.s8 = self.params['ParamBrowRY']
                self.s9 = self.params['ParamBrowRAngle']
                self.s10 = self.params['Param51']
            return [
                ('ParamBrowLY', round(linearScale1(eased_t, 0, 1, self.s6, 0), 2), 1),
                ('ParamBrowLAngle', round(linearScale1(eased_t, 0, 1, self.s7, 0), 2), 1),
                ('ParamBrowRY', round(linearScale1(eased_t, 0, 1, self.s8, 0), 2), 1),
                ('ParamBrowRAngle', round(linearScale1(eased_t, 0, 1, self.s9, 0), 2), 1),
                ('Param51', round(linearScale1(eased_t, 0, 1, self.s10, 0), 2), 1),
            ]
        else:
            return None

class Animator2:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = random.uniform(0.5, 2)
        self.k = random.uniform(-1, 1)
        self.flag1 = 0
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = sine(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamBodyAngleY']
                self.s2 = self.params['ParamAngleY']
                self.s3 = self.params['ParamEyeBallY']
            return [
                ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s1, 10*self.k), 2), 1),
                ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s2, 30*self.k), 2), 1),
                ('ParamEyeBallY', round(linearScale1(eased_t, 0, 1, self.s3, -1*self.k), 2), 1),
            ]
        elif 1 <= t < 2:
            t -= 1
            eased_t = sine(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s4 = self.params['ParamBodyAngleY']
                self.s5 = self.params['ParamAngleY']
                self.s6 = self.params['ParamEyeBallY']
            return [
                ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s4, -10*self.k*0.5), 2), 1),
                ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s5, -30*self.k*0.5), 2), 1),
                ('ParamEyeBallY', round(linearScale1(eased_t, 0, 1, self.s6, 1*self.k*0.5), 2), 1),
            ]
        elif 2 <= t < 3:
            t -= 2
            eased_t = sine(t)
            if self.flag1 == 2:
                self.flag1 += 1
                self.s7 = self.params['ParamBodyAngleY']
                self.s8 = self.params['ParamAngleY']
                self.s9 = self.params['ParamEyeBallY']
            return [
                ('ParamBodyAngleY', round(linearScale1(eased_t, 0, 1, self.s7, 0), 2), 1),
                ('ParamAngleY', round(linearScale1(eased_t, 0, 1, self.s8, 0), 2), 1),
                ('ParamEyeBallY', round(linearScale1(eased_t, 0, 1, self.s9, 0), 2), 1),
            ]
        else:
            return None
    
class Animator3:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = random.uniform(0.8, 2)
        self.k = random.uniform(-0.5, 0.5)
        self.flag1 = 0
        self.easing_functions = [
            cubic,
            quart,
            sine
        ]
        self.current_easing = random.choice(self.easing_functions)
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = self.current_easing(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamAngleZ']
                self.s2 = self.params['ParamBodyAngleZ']
            return [
                ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s1, 30*self.k), 2), 1),
                ('ParamBodyAngleZ', round(linearScale1(eased_t, 0, 1, self.s2, 10*self.k), 2), 1),
            ]
        elif 1 <= t < 3:
            t -= 1
            t /= 2
            eased_t = self.current_easing(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s3 = self.params['ParamAngleZ']
                self.s4 = self.params['ParamBodyAngleZ']
            return [
                ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s3, -30*self.k), 2), 1),
                ('ParamBodyAngleZ', round(linearScale1(eased_t, 0, 1, self.s4, -10*self.k), 2), 1),
            ]
        elif 3 <= t < 4:
            t -= 3
            eased_t = self.current_easing(t)
            if self.flag1 == 2:
                self.flag1 += 1
                self.s5 = self.params['ParamAngleZ']
                self.s6 = self.params['ParamBodyAngleZ']
            return [
                ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s5, 0), 2), 1),
                ('ParamBodyAngleZ', round(linearScale1(eased_t, 0, 1, self.s6, 0), 2), 1),
            ]
        else:
            return None

class Animator4:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = random.uniform(0.5, 1)
        self.duration = random.uniform(0.5, 2)
        self.open = random.random()
        self.flag1 = 0
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = cubic(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamMouthOpenY']
            return [
                ('ParamMouthOpenY', round(linearScale1(eased_t, 0, 1, self.s1, self.open), 2), 1),
            ]
        elif t < self.duration + 1:
            return []
        elif self.duration + 1 <= t < self.duration + 2:
            t -= self.duration + 1
            eased_t = cubic(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s2 = self.params['ParamMouthOpenY']
            return [
                ('ParamMouthOpenY', round(linearScale1(eased_t, 0, 1, self.s2, -1), 2), 1),
            ]
        else:
            return None

class Animator5:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = random.uniform(0.8, 2)
        self.k = random.uniform(-0.5, 0.5)
        self.flag1 = 0
        self.easing_functions = [
            cubic,
            quart,
            sine
        ]
        self.current_easing = random.choice(self.easing_functions)
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = self.current_easing(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamAngleX']
                self.s2 = self.params['ParamBodyAngleX']
            return [
                ('ParamAngleX', round(linearScale1(eased_t, 0, 1, self.s1, 30*self.k), 2), 1),
                ('ParamBodyAngleX', round(linearScale1(eased_t, 0, 1, self.s2, 10*self.k), 2), 1),
            ]
        elif 1 <= t < 3:
            t -= 1
            t /= 2
            eased_t = self.current_easing(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s3 = self.params['ParamAngleX']
                self.s4 = self.params['ParamBodyAngleX']
            return [
                ('ParamAngleX', round(linearScale1(eased_t, 0, 1, self.s3, -30*self.k), 2), 1),
                ('ParamBodyAngleX', round(linearScale1(eased_t, 0, 1, self.s4, -10*self.k), 2), 1),
            ]
        elif 3 <= t < 4:
            t -= 3
            eased_t = self.current_easing(t)
            if self.flag1 == 2:
                self.flag1 += 1
                self.s5 = self.params['ParamAngleX']
                self.s6 = self.params['ParamBodyAngleX']
            return [
                ('ParamAngleX', round(linearScale1(eased_t, 0, 1, self.s5, 0), 2), 1),
                ('ParamBodyAngleX', round(linearScale1(eased_t, 0, 1, self.s6, 0), 2), 1),
            ]
        else:
            return None

class Animator6:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = 1
        self.duration = random.uniform(0, 1)
        self.BrowY = random.choice([-1, 0])
        self.flag1 = 0
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = cubic(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamBrowLY']
                self.s2 = self.params['ParamBrowLAngle']
                self.s3 = self.params['ParamBrowRY']
                self.s4 = self.params['ParamBrowRAngle']
            return [
                ('ParamBrowLY', round(linearScale1(eased_t, 0, 1, self.s1, self.BrowY), 2), 1),
                ('ParamBrowLAngle', round(linearScale1(eased_t, 0, 1, self.s2, -1), 2), 1),
                ('ParamBrowRY', round(linearScale1(eased_t, 0, 1, self.s3, self.BrowY), 2), 1),
                ('ParamBrowRAngle', round(linearScale1(eased_t, 0, 1, self.s4, -1), 2), 1),
            ]
        elif t < self.duration + 1:
            return []
        elif self.duration + 1 <= t < self.duration + 2:
            t -= self.duration + 1
            eased_t = cubic(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s5 = self.params['ParamBrowLY']
                self.s6 = self.params['ParamBrowLAngle']
                self.s7 = self.params['ParamBrowRY']
                self.s8 = self.params['ParamBrowRAngle']
            return [
                ('ParamBrowLY', round(linearScale1(eased_t, 0, 1, self.s5, 0), 2), 1),
                ('ParamBrowLAngle', round(linearScale1(eased_t, 0, 1, self.s6, 0), 2), 1),
                ('ParamBrowRY', round(linearScale1(eased_t, 0, 1, self.s7, 0), 2), 1),
                ('ParamBrowRAngle', round(linearScale1(eased_t, 0, 1, self.s8, 0), 2), 1),
            ]
        else:
            return None

class Animator7:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = 0.5
        self.duration = random.uniform(0, 1)
        self.k = random.choice([-1, 1])
        self.flag1 = 0
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = cubic(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamEyeLOpen']
                self.s2 = self.params['ParamEyeROpen']
            return [
                ('ParamEyeLOpen', round(linearScale1(eased_t, 0, 1, self.s1, max(0, self.k)), 2), 1),
                ('ParamEyeROpen', round(linearScale1(eased_t, 0, 1, self.s2, max(0, self.k*-1)), 2), 1),
            ]
        elif t < self.duration + 1:
            return []
        elif self.duration + 1 <= t < self.duration + 2:
            t -= self.duration + 1
            eased_t = cubic(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s3 = self.params['ParamEyeLOpen']
                self.s4 = self.params['ParamEyeROpen']
            return [
                ('ParamEyeLOpen', round(linearScale1(eased_t, 0, 1, self.s3, 1), 2), 1),
                ('ParamEyeROpen', round(linearScale1(eased_t, 0, 1, self.s4, 1), 2), 1),
            ]
        else:
            return None

class Animator8:
    def __init__(self):
        self.params = Global.live2d_animator.params
        self.timer = time.time()
        self.interval = random.uniform(1, 2)
        self.k = random.uniform(-1, 1)
        self.flag1 = 0
        self.easing_functions = [
            cubic,
            quart,
            sine
        ]
        self.current_easing = random.choice(self.easing_functions)
    
    def update(self):
        t = (time.time() - self.timer) / self.interval
        if t < 1:
            eased_t = self.current_easing(t)
            if self.flag1 == 0:
                self.flag1 += 1
                self.s1 = self.params['ParamAngleZ']
            return [
                ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s1, 15*self.k), 2), 1),
            ]
        elif 1 <= t < 3:
            t -= 1
            t /= 2
            eased_t = self.current_easing(t)
            if self.flag1 == 1:
                self.flag1 += 1
                self.s2 = self.params['ParamAngleZ']
            return [
                ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s2, -15*self.k), 2), 1),
            ]
        elif 3 <= t < 4:
            t -= 3
            eased_t = self.current_easing(t)
            if self.flag1 == 2:
                self.flag1 += 1
                self.s3 = self.params['ParamAngleZ']
            return [
                ('ParamAngleZ', round(linearScale1(eased_t, 0, 1, self.s3, 0), 2), 1),
            ]
        else:
            return None