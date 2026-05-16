"""
🎮 跳跃小鸟 (Flappy Bird) - Python 版
蓝色小鸟在前进，躲避绿色管道（类似马里奥管道）
碰到管道或上下边界则游戏结束
设置随机目标分数（20-30之间），到达即胜利！
"""

import pygame
import random
import sys
import math
import array

# ===== 游戏配置 =====
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
FPS = 60

# 颜色
SKY_BLUE = (135, 206, 235)      # 天空蓝
GREEN = (0, 180, 80)             # 管道绿
GREEN_DARK = (0, 140, 50)        # 管道深绿
BIRD_BLUE = (30, 144, 255)       # 小鸟蓝
BIRD_DARK = (20, 120, 220)       # 小鸟深蓝
GROUND_COLOR = (220, 190, 140)   # 地面棕色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GOLD = (255, 215, 0)             # 金色 - 胜利
PURPLE = (180, 50, 255)          # 紫色 - 目标分数

# 物理参数
GRAVITY = 0.5
JUMP_VELOCITY = -9
PIPE_SPEED = 4
PIPE_GAP = 180          # 管道间距
PIPE_WIDTH = 60
PIPE_FREQUENCY = 1500   # 生成管道间隔（毫秒）

# 胜利目标分数范围
TARGET_MIN = 20
TARGET_MAX = 30


def _make_sound_stereo(buf_mono):
    """将单声道 int16 数组转换为立体声 Sound 对象"""
    import numpy as np
    arr = np.array(buf_mono, dtype=np.int16)
    stereo = np.column_stack((arr, arr))
    return pygame.sndarray.make_sound(stereo)

def generate_sound(frequency, duration_ms, volume=0.3, wave_type="sine"):
    """
    用数学方法生成音效（不需要外部音频文件）
    frequency: 频率(Hz)
    duration_ms: 时长(毫秒)
    volume: 音量 0.0-1.0
    wave_type: 波形类型 "sine" / "square" / "noise" / "sweep"
    """
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000)
    max_amp = int(32767 * volume)
    
    buf = array.array('h', [0] * n_samples)
    
    for i in range(n_samples):
        t = i / sample_rate
        if wave_type == "sine":
            sample = int(max_amp * math.sin(2 * math.pi * frequency * t))
        elif wave_type == "square":
            sample = max_amp if math.sin(2 * math.pi * frequency * t) > 0 else -max_amp
        elif wave_type == "noise":
            sample = random.randint(-max_amp, max_amp)
        elif wave_type == "sweep":
            f = frequency * (1 - t / (duration_ms / 1000) * 0.5)
            sample = int(max_amp * math.sin(2 * math.pi * f * t))
        else:
            sample = 0
        buf[i] = sample
    
    return _make_sound_stereo(buf)


class SoundManager:
    """音效管理器"""
    def __init__(self):
        # 先退出再以单声道重新初始化
        pygame.mixer.quit()
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        self.sounds = {}
        self._create_sounds()
        # 背景音乐（循环播放的简单旋律）
        self.bgm = None
        self._create_bgm()
    
    def _create_sounds(self):
        """生成所有音效"""
        # 跳跃音 - 短促上升
        self.sounds["jump"] = generate_sound(500, 80, 0.2, "sweep")
        # 得分音 - 清脆叮声
        self.sounds["score"] = generate_sound(880, 120, 0.25, "sine")
        # 游戏结束音 - 低沉下降
        self.sounds["game_over"] = generate_sound(300, 400, 0.3, "sweep")
        # 胜利音 - 欢快上升
        self.sounds["victory"] = generate_sound(660, 500, 0.35, "sine")
        # 管道碰撞音
        self.sounds["hit"] = generate_sound(100, 200, 0.4, "noise")
    
    def _create_bgm(self):
        """生成简单的背景音乐（循环播放）"""
        sample_rate = 22050
        duration = 2.0  # 2秒循环
        n_samples = int(sample_rate * duration)
        
        buf = array.array('h', [0] * n_samples)
        max_amp = int(32767 * 0.08)  # 音量小一点
        
        # 简单旋律：C E G C' E' G'
        notes = [262, 330, 392, 523, 659, 784]
        note_len = n_samples // len(notes)
        
        for ni, freq in enumerate(notes):
            start = ni * note_len
            for i in range(note_len):
                t = i / sample_rate
                # 渐入渐出避免爆音
                env = min(i / (note_len * 0.1), 1, (note_len - i) / (note_len * 0.1))
                sample = int(max_amp * env * math.sin(2 * math.pi * freq * t))
                if start + i < n_samples:
                    buf[start + i] = sample
        
        self.bgm = _make_sound_stereo(buf)
    
    def play(self, name):
        """播放音效"""
        if name in self.sounds:
            self.sounds[name].play()
    
    def start_bgm(self):
        """开始背景音乐"""
        if self.bgm:
            self.bgm.play(-1)  # 无限循环
    
    def stop_bgm(self):
        """停止背景音乐"""
        if self.bgm:
            self.bgm.stop()


class Bird:
    """蓝色小鸟"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel_y = 0
        self.size = 18
        self.angle = 0
        self.wing_frame = 0
        self.wing_timer = 0

    def jump(self):
        """跳跃"""
        self.vel_y = JUMP_VELOCITY

    def update(self):
        """更新物理状态"""
        self.vel_y += GRAVITY
        self.y += self.vel_y

        # 翅膀动画
        self.wing_timer += 1
        if self.wing_timer > 8:
            self.wing_timer = 0
            self.wing_frame = (self.wing_frame + 1) % 3

        # 计算旋转角度（俯冲时向下转）
        if self.vel_y < 0:
            self.angle = min(30, -self.vel_y * 3)
        else:
            self.angle = max(-90, -self.vel_y * 3)

    def draw(self, screen):
        """绘制蓝色小鸟"""
        # 创建旋转前的表面
        surf_size = self.size * 3
        bird_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        cx, cy = surf_size // 2, surf_size // 2
        
        # 身体 - 椭圆
        body_rect = pygame.Rect(cx - self.size, cy - self.size//2, self.size * 1.8, self.size)
        pygame.draw.ellipse(bird_surf, BIRD_BLUE, body_rect)
        
        # 翅膀（根据帧变化位置）
        wing_offset = [0, -3, 3][self.wing_frame]
        wing_rect = pygame.Rect(cx - self.size//3 + wing_offset, cy - 2, self.size//2, self.size//2)
        pygame.draw.ellipse(bird_surf, BIRD_DARK, wing_rect)
        
        # 眼睛
        eye_x = cx + self.size//3 + 3
        eye_y = cy - self.size//4
        pygame.draw.circle(bird_surf, WHITE, (eye_x, eye_y), 5)
        pygame.draw.circle(bird_surf, BLACK, (eye_x + 2, eye_y), 2)
        
        # 嘴巴
        pygame.draw.polygon(bird_surf, (255, 200, 0),
                          [(eye_x + 4, eye_y), (eye_x + 12, eye_y + 2), (eye_x + 4, eye_y + 5)])

        # 旋转并绘制
        rotated = pygame.transform.rotate(bird_surf, self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        screen.blit(rotated, rect)

    def get_rect(self):
        """获取碰撞矩形"""
        return pygame.Rect(self.x - self.size//2, self.y - self.size//2,
                          self.size, self.size)


class Pipe:
    """管道（类似马里奥管道）"""
    def __init__(self, x):
        self.x = x
        self.width = PIPE_WIDTH
        self.gap = PIPE_GAP
        self.top_height = random.randint(80, SCREEN_HEIGHT - 250 - self.gap)
        self.bottom_y = self.top_height + self.gap
        self.passed = False  # 是否已被小鸟通过

    def update(self):
        """向左移动"""
        self.x -= PIPE_SPEED

    def draw(self, screen):
        """绘制管道"""
        # 上管道
        self._draw_pipe(screen, self.x, 0, self.width, self.top_height)
        # 下管道
        self._draw_pipe(screen, self.x, self.bottom_y, self.width,
                       SCREEN_HEIGHT - self.bottom_y)

    def _draw_pipe(self, screen, x, y, w, h):
        """绘制单个管道"""
        # 管道主体
        pygame.draw.rect(screen, GREEN, (x, y, w, h))
        pygame.draw.rect(screen, GREEN_DARK, (x, y, w, h), 3)
        
        # 管道口（马里奥风格）
        lip_h = 25
        lip_w = w + 16
        lip_x = x - 8
        if y == 0:  # 上管道口（向下）
            pygame.draw.rect(screen, GREEN, (lip_x, y + h - lip_h, lip_w, lip_h))
            pygame.draw.rect(screen, GREEN_DARK, (lip_x, y + h - lip_h, lip_w, lip_h), 3)
        else:  # 下管道口（向上）
            pygame.draw.rect(screen, GREEN, (lip_x, y, lip_w, lip_h))
            pygame.draw.rect(screen, GREEN_DARK, (lip_x, y, lip_w, lip_h), 3)
        
        # 管道内部阴影
        inner = pygame.Rect(x + 5, y + 5 if y == 0 else y + lip_h, w - 10, h - 10 - lip_h)
        pygame.draw.rect(screen, (0, 160, 70), inner)

    def get_rects(self):
        """获取碰撞矩形列表"""
        return [
            pygame.Rect(self.x, 0, self.width, self.top_height),
            pygame.Rect(self.x, self.bottom_y, self.width,
                       SCREEN_HEIGHT - self.bottom_y)
        ]

    def is_off_screen(self):
        """是否移出屏幕"""
        return self.x + self.width < 0


class Star:
    """胜利后飘落的星星装饰"""
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(-50, -10)
        self.speed = random.uniform(1, 3)
        self.size = random.randint(3, 8)
        self.color = random.choice([GOLD, WHITE, (255, 255, 100)])
    
    def update(self):
        self.y += self.speed
    
    def draw(self, screen):
        # 画四角星
        points = []
        for i in range(4):
            angle = math.pi / 2 * i - math.pi / 4
            points.append((self.x + math.cos(angle) * self.size,
                          self.y + math.sin(angle) * self.size))
            angle2 = math.pi / 2 * i
            points.append((self.x + math.cos(angle2) * self.size * 0.4,
                          self.y + math.sin(angle2) * self.size * 0.4))
        pygame.draw.polygon(screen, self.color, points)
    
    def is_off_screen(self):
        return self.y > SCREEN_HEIGHT + 10


class Game:
    """游戏主类"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("🎮 跳跃小鸟 - Flappy Bird")
        self.clock = pygame.time.Clock()
        
        # 字体
        self.font_small = pygame.font.Font(None, 28)
        self.font_med = pygame.font.Font(None, 36)
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 60)
        
        # 音效
        self.sound = SoundManager()
        
        # 装饰星星（胜利时用）
        self.stars = []
        self.star_timer = 0
        
        self.reset()

    def reset(self):
        """重置游戏"""
        self.bird = Bird(100, SCREEN_HEIGHT // 2)
        self.pipes = []
        self.score = 0
        self.game_over = False
        self.victory = False
        self.started = False
        self.last_pipe = 0
        
        # 随机生成胜利目标分数（20-30之间）
        self.target_score = random.randint(TARGET_MIN, TARGET_MAX)
        
        # 重置星星
        self.stars = []
        self.star_timer = 0
        
        # 停止背景音乐（等开始后再播放）
        self.sound.stop_bgm()

    def handle_events(self):
        """处理输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.victory or self.game_over:
                        self.reset()
                    elif not self.started:
                        self.started = True
                        self.sound.start_bgm()
                        self.bird.jump()
                        self.sound.play("jump")
                    else:
                        self.bird.jump()
                        self.sound.play("jump")
                if event.key == pygame.K_ESCAPE:
                    return False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.victory or self.game_over:
                    self.reset()
                elif not self.started:
                    self.started = True
                    self.sound.start_bgm()
                    self.bird.jump()
                    self.sound.play("jump")
                else:
                    self.bird.jump()
                    self.sound.play("jump")
        return True

    def update(self):
        """更新游戏状态"""
        if not self.started or self.game_over or self.victory:
            # 胜利时更新星星动画
            if self.victory:
                self.star_timer += 1
                if self.star_timer > 5:
                    self.star_timer = 0
                    self.stars.append(Star())
                for star in self.stars[:]:
                    star.update()
                    if star.is_off_screen():
                        self.stars.remove(star)
            return

        # 更新小鸟
        self.bird.update()

        # 生成新管道
        now = pygame.time.get_ticks()
        if now - self.last_pipe > PIPE_FREQUENCY:
            self.pipes.append(Pipe(SCREEN_WIDTH + 50))
            self.last_pipe = now

        # 更新管道
        for pipe in self.pipes[:]:
            pipe.update()
            if pipe.is_off_screen():
                self.pipes.remove(pipe)

        # 碰撞检测
        bird_rect = self.bird.get_rect()

        # 上下边界碰撞
        if self.bird.y < 0 or self.bird.y > SCREEN_HEIGHT - 60:
            self.game_over = True
            self.sound.stop_bgm()
            self.sound.play("hit")
            self.sound.play("game_over")

        # 管道碰撞
        for pipe in self.pipes:
            for pipe_rect in pipe.get_rects():
                if bird_rect.colliderect(pipe_rect):
                    self.game_over = True
                    self.sound.stop_bgm()
                    self.sound.play("hit")
                    self.sound.play("game_over")

            # 计分
            if not pipe.passed and pipe.x + pipe.width < self.bird.x:
                pipe.passed = True
                self.score += 1
                self.sound.play("score")
                
                # 检查是否达到胜利目标
                if self.score >= self.target_score:
                    self.victory = True
                    self.sound.stop_bgm()
                    self.sound.play("victory")

    def draw(self):
        """绘制画面"""
        self.screen.fill(SKY_BLUE)

        # 绘制云朵
        self._draw_clouds()

        # 绘制管道
        for pipe in self.pipes:
            pipe.draw(self.screen)

        # 绘制小鸟（胜利时也画）
        if not self.game_over or self.victory:
            self.bird.draw(self.screen)

        # 绘制星星（胜利时）
        if self.victory:
            for star in self.stars:
                star.draw(self.screen)

        # 绘制地面
        pygame.draw.rect(self.screen, GROUND_COLOR, (0, SCREEN_HEIGHT-50, SCREEN_WIDTH, 50))
        pygame.draw.line(self.screen, BLACK, (0, SCREEN_HEIGHT-50), (SCREEN_WIDTH, SCREEN_HEIGHT-50), 2)

        # 绘制分数和目标
        score_text = self.font_large.render(str(self.score), True, WHITE)
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, 50))
        
        # 显示目标分数
        target_text = self.font_small.render(f"目标: {self.target_score}", True, PURPLE)
        self.screen.blit(target_text, (SCREEN_WIDTH - target_text.get_width() - 15, 15))
        
        # 进度条 - 显示离目标还有多远
        if self.started and not self.game_over and not self.victory:
            progress = min(self.score / self.target_score, 1.0)
            bar_width = 200
            bar_height = 8
            bar_x = SCREEN_WIDTH // 2 - bar_width // 2
            bar_y = 85
            # 背景
            pygame.draw.rect(self.screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            # 进度
            fill_color = (255, 200, 0) if progress < 0.7 else (0, 255, 100)
            pygame.draw.rect(self.screen, fill_color, (bar_x, bar_y, int(bar_width * progress), bar_height), border_radius=4)
            # 边框
            pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1, border_radius=4)

        # 游戏状态提示
        if not self.started:
            self._draw_center_text("跳跃小鸟", self.font_huge, WHITE, -80)
            self._draw_center_text(f"目标得分: {self.target_score}", self.font_med, GOLD, -20)
            self._draw_center_text("按空格键 或 点击鼠标 开始", self.font_small, WHITE, 20)
            self._draw_center_text("空格/点击 = 跳跃  |  ESC = 退出", self.font_small, (200, 200, 200), 55)
        
        elif self.victory:
            # 胜利画面
            self._draw_center_text("🎉 胜利! 🎉", self.font_huge, GOLD, -100)
            self._draw_center_text(f"成功到达目标: {self.target_score} 分!", self.font_med, WHITE, -40)
            self._draw_center_text(f"最终得分: {self.score}", self.font_large, GOLD, 10)
            self._draw_center_text("按空格键 或 点击鼠标 重新开始", self.font_small, (200, 200, 200), 60)
        
        elif self.game_over:
            self._draw_center_text("游戏结束", self.font_huge, RED, -80)
            self._draw_center_text(f"得分: {self.score}  /  目标: {self.target_score}", self.font_med, WHITE, -20)
            self._draw_center_text("按空格键 或 点击鼠标 重新开始", self.font_small, WHITE, 30)

        pygame.display.flip()

    def _draw_clouds(self):
        """绘制装饰云朵"""
        for i in range(3):
            cloud_x = (i * 180 + pygame.time.get_ticks() // 60 % 720) - 240
            if cloud_x < SCREEN_WIDTH:
                base_y = 60 + i * 50
                pygame.draw.ellipse(self.screen, (200, 220, 240), (cloud_x, base_y, 65, 28))
                pygame.draw.ellipse(self.screen, (200, 220, 240), (cloud_x + 22, base_y - 5, 50, 25))

    def _draw_center_text(self, text, font, color, y_offset=0):
        """居中绘制文字"""
        text_surf = font.render(text, True, color)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + y_offset))
        self.screen.blit(text_surf, text_rect)

    def run(self):
        """游戏主循环"""
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        # 清理
        self.sound.stop_bgm()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
