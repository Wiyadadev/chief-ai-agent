import json
from pathlib import Path


class MemoryManager:
    def __init__(self, memory_dir="memory"):
        self.memory_dir = Path(memory_dir)

    def load(self, filename):
        file = self.memory_dir / filename

        if not file.exists():
            return {}

        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, filename, data):
        file = self.memory_dir / filename

        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)