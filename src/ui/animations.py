"""8-bit game style pixel animation effects for OpenCode Helper v2."""
import random
import math
from .theme import COLORS

class CelebrationParticles:
    """Pixel block celebration — blocks explode from center, drift down with flicker."""

    def __init__(self, canvas, width, height):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.particles = []
        self._running = False
        self._frame = 0
        self._chars = ['█', '▓', '▒', '░', '▀', '▄', '■']
        self._colors = [COLORS['neon_green'], COLORS['yellow'], COLORS['red'],
                       COLORS['white'], COLORS['neon_green_dim']]

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _spawn_burst(self, count: int = 15):
        """Spawn a burst of pixel particles from random positions."""
        for _ in range(count):
            x = random.randint(20, self.width - 20)
            self.particles.append({
                'x': x, 'y': random.randint(-20, 0),
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(0.5, 2.5),
                'color': random.choice(self._colors),
                'char': random.choice(self._chars),
                'size': random.randint(3, 7),
                'life': random.randint(30, 80),
                'age': 0,
            })

    def _animate(self):
        if not self._running:
            return
        self.canvas.delete('all')
        self._frame += 1

        # Periodic burst
        if self._frame % 15 == 0:
            self._spawn_burst(12)

        # Also spawn center explosion periodically
        if self._frame % 60 == 0:
            cx, cy = self.width // 2, self.height // 2
            for _ in range(25):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(0.5, 3)
                self.particles.append({
                    'x': cx, 'y': cy,
                    'vx': math.cos(angle) * speed,
                    'vy': math.sin(angle) * speed - 1,
                    'color': random.choice(self._colors),
                    'char': '█',
                    'size': random.randint(4, 8),
                    'life': random.randint(20, 50),
                    'age': 0,
                })

        # Animate particles
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.03  # gravity
            p['age'] += 1
            if p['age'] > p['life'] or p['y'] > self.height + 20:
                self.particles.remove(p)
            else:
                alpha = 1 - (p['age'] / p['life'])
                self.canvas.create_text(p['x'], p['y'], text=p['char'],
                                       fill=p['color'], font=('Consolas', p['size']))

        self.canvas.after(50, self._animate)

class NeonFlicker:
    """Flickering neon text effect."""

    def __init__(self, label):
        self.label = label
        self._running = False
        self._base_color = COLORS['neon_green']

    def start(self):
        self._running = True
        self._flicker()

    def stop(self):
        self._running = False

    def _flicker(self):
        if not self._running:
            return
        import random
        if random.random() < 0.3:
            self.label.configure(fg=COLORS['yellow'])
            self.label.after(80, lambda: self.label.configure(fg=self._base_color))
        delay = random.randint(200, 800)
        self.label.after(delay, self._flicker)
