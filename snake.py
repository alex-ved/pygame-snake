"""Classic wraparound Snake. Run with Python and pygame."""

from array import array
from datetime import date
import json
import math
import os
from pathlib import Path
import random
from tempfile import NamedTemporaryFile
from time import perf_counter

import pygame

COLS, ROWS, CELL = 24, 18, 27
LEFT, TOP = 24, 96
WIDTH, HEIGHT = 960, 630
STEP = 1 / 8
CELLS = [(x, y) for y in range(ROWS) for x in range(COLS)]
SAVE_PATH = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Snake" / "history.json"

BACKGROUND = "#10181b"
PANEL = "#172326"
GRID = "#1d2a2d"
TEXT = "#eef6ec"
MUTED = "#afc1bc"
GREEN = "#aff17b"
FOOD = "#ff826c"

KEYS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}


class History:
    def __init__(self, path):
        self.path = path
        self.scores = []
        self.muted = False
        self.save_failed = False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            self.muted = data.get("muted") is True
            scores = data.get("scores", [])
            if isinstance(scores, list):
                for entry in scores:
                    if not isinstance(entry, dict):
                        continue
                    score, day = entry.get("score"), entry.get("date")
                    if type(score) is int and 0 <= score <= len(CELLS) - 3 and isinstance(day, str):
                        try:
                            self.scores.append({"score": score, "date": date.fromisoformat(day).isoformat()})
                        except ValueError:
                            continue
                self.rank()
        except (OSError, ValueError):
            pass

    def rank(self):
        self.scores.sort(key=lambda entry: -entry["score"])
        del self.scores[5:]

    def record(self, score):
        entry = {"score": score, "date": date.today().isoformat()}
        self.scores.append(entry)
        self.rank()
        self.save()
        return entry

    def save(self):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                    delete=False) as file:
                temporary = Path(file.name)
                json.dump({"scores": self.scores, "muted": self.muted}, file)
            temporary.replace(self.path)
            self.save_failed = False
        except OSError:
            self.save_failed = True
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


class Run:
    def __init__(self):
        self.body = [(12, 9), (11, 9), (10, 9)]
        self.direction = (1, 0)
        self.pending = None
        self.score = 0
        self.spawn_food()

    def spawn_food(self):
        occupied = set(self.body)
        free = [cell for cell in CELLS if cell not in occupied]
        self.food = random.choice(free) if free else None

    def turn(self, direction):
        dx, dy = self.direction
        if self.pending is None and direction not in (self.direction, (-dx, -dy)):
            self.pending = direction

    def step(self):
        if self.pending is not None:
            self.direction, self.pending = self.pending, None
        x, y = self.body[0]
        dx, dy = self.direction
        head = ((x + dx) % COLS, (y + dy) % ROWS)
        eating = head == self.food
        occupied = self.body if eating else self.body[:-1]
        if head in occupied:
            return "crash"
        self.body.insert(0, head)
        if not eating:
            self.body.pop()
            return None
        self.score += 1
        self.spawn_food()
        return "win" if self.food is None else "eat"


def make_sounds():
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=1, allowedchanges=0)
        effects = {
            "eat": [(680, 0.055), (980, 0.07)],
            "crash": [(210, 0.08), (120, 0.21)],
            "win": [(523, 0.10), (659, 0.10), (784, 0.10), (1047, 0.24)],
        }
        sounds = {}
        for event, notes in effects.items():
            samples = array("h")
            for frequency, duration in notes:
                count = int(44100 * duration)
                for sample in range(count):
                    envelope = min(1, sample / 150, (count - sample) / 750)
                    samples.append(int(8200 * envelope * math.sin(math.tau * frequency * sample / 44100)))
            sounds[event] = pygame.mixer.Sound(buffer=samples)
        return sounds
    except pygame.error:
        return {}


class Display:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snake")
        self.fonts = {size: pygame.font.Font(None, size) for size in (19, 23, 28, 36, 56)}
        self.board = pygame.Surface((COLS * CELL, ROWS * CELL))
        self.board.fill(PANEL)
        for x in range(0, self.board.get_width(), CELL):
            pygame.draw.line(self.board, GRID, (x, 0), (x, self.board.get_height()))
        for y in range(0, self.board.get_height(), CELL):
            pygame.draw.line(self.board, GRID, (0, y), (self.board.get_width(), y))

    def label(self, content, size, x, y, color=TEXT, align="topleft"):
        image = self.fonts[size].render(content, True, color)
        self.screen.blit(image, image.get_rect(**{align: (x, y)}))

    def draw(self, run, state, history, latest, sounds_available):
        self.screen.fill(BACKGROUND)
        self.label("Snake", 56, LEFT, 25)
        self.label(f"Score  {run.score}", 36, LEFT + COLS * CELL, 42, GREEN, "topright")
        self.screen.blit(self.board, (LEFT, TOP))
        pygame.draw.rect(self.screen, MUTED, (LEFT - 1, TOP - 1, COLS * CELL + 2, ROWS * CELL + 2), 1)

        if run.food is not None:
            x, y = run.food
            center = (LEFT + x * CELL + CELL // 2, TOP + y * CELL + CELL // 2)
            pygame.draw.circle(self.screen, FOOD, center, 8)
            pygame.draw.circle(self.screen, "#ffbaaa", (center[0] - 2, center[1] - 3), 2)

        for index, (x, y) in reversed(list(enumerate(run.body))):
            tile = pygame.Rect(LEFT + x * CELL + 2, TOP + y * CELL + 2, CELL - 3, CELL - 3)
            pygame.draw.rect(self.screen, GREEN if index == 0 else "#69bc79", tile, border_radius=6)
            if index == 0:
                dx, dy = run.direction
                for side in (-1, 1):
                    eye = (tile.centerx + dx * 5 - dy * side * 4,
                           tile.centery + dy * 5 + dx * side * 4)
                    pygame.draw.circle(self.screen, BACKGROUND, eye, 2)

        pygame.draw.rect(self.screen, PANEL, (698, TOP, 238, 486), border_radius=12)
        self.label("Top 5 Scores", 28, 714, 117)
        if not history.scores:
            self.label("No scores yet", 23, 714, 168, MUTED)
        for rank, entry in enumerate(history.scores, start=1):
            y = 153 + (rank - 1) * 48
            color = GREEN if entry is latest else TEXT
            if entry is latest:
                pygame.draw.rect(self.screen, "#273c2d", (708, y - 4, 218, 40), border_radius=6)
            self.label(str(rank), 23, 717, y + 7, color)
            self.label(str(entry["score"]), 28, 752, y + 5, color)
            self.label(entry["date"], 19, 917, y + 9, color, "topright")
        pygame.draw.line(self.screen, "#42524f", (714, 413), (919, 413))
        self.label("Arrows / WASD   Steer", 23, 714, 433, MUTED)
        self.label("P   Pause / resume", 23, 714, 464, MUTED)
        self.label("M   Toggle sound", 23, 714, 495, MUTED)
        sound = "Unavailable" if not sounds_available else "Off" if history.muted else "On"
        self.label(f"Sound  {sound}", 23, 714, 545, GREEN if sound == "On" else MUTED)
        self.label("Wraparound board  /  8 cells per second", 19, LEFT, 601, MUTED)
        if history.save_failed:
            self.label("Could not save history", 19, 936, 601, FOOD, "topright")

        if state != "playing":
            title, prompt = {
                "ready": ("Ready?", "Enter to start"),
                "paused": ("Paused", "P to resume"),
                "crash": ("Game over", "Enter to play again"),
                "win": ("Board cleared!", "Enter to play again"),
            }[state]
            center_x = LEFT + COLS * CELL // 2
            box = pygame.Rect(center_x - 194, 260, 388, 158)
            pygame.draw.rect(self.screen, BACKGROUND, box, border_radius=14)
            pygame.draw.rect(self.screen, "#42524f", box, 1, border_radius=14)
            self.label(title, 56, center_x, 284, TEXT, "midtop")
            if state in ("crash", "win"):
                self.label(f"Final score  {run.score}", 23, center_x, 339, MUTED, "midtop")
            self.label(prompt, 28, center_x, 373, GREEN, "midtop")
        pygame.display.flip()


def main():
    pygame.display.init()
    pygame.font.init()
    display = Display()
    sounds = make_sounds()
    history = History(SAVE_PATH)
    run = Run()
    state = "ready"
    latest = None
    next_step = 0
    clock = pygame.time.Clock()

    try:
        while True:
            now = perf_counter()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.WINDOWFOCUSLOST and state == "playing":
                    state = "paused"
                    run.pending = None
                if event.type != pygame.KEYDOWN:
                    continue
                key = event.key
                if key == pygame.K_m:
                    history.muted = not history.muted
                    if history.muted and sounds:
                        pygame.mixer.stop()
                    history.save()
                elif key == pygame.K_RETURN and state in ("ready", "crash", "win"):
                    run = Run()
                    latest = None
                    state = "playing"
                    next_step = now + STEP
                elif key == pygame.K_p and state in ("playing", "paused"):
                    state = "paused" if state == "playing" else "playing"
                    run.pending = None
                    next_step = now + STEP
                elif state == "playing" and key in KEYS:
                    run.turn(KEYS[key])

            if state == "playing" and now >= next_step:
                event = run.step()
                next_step += STEP
                if next_step <= now:
                    next_step = now + STEP
                if event in sounds and not history.muted:
                    sounds[event].play()
                if event in ("crash", "win"):
                    state = event
                    latest = history.record(run.score)

            display.draw(run, state, history, latest, bool(sounds))
            clock.tick(60)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
