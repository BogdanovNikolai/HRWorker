import json
import os

def collect_areas(data):
    """
    Рекурсивно собирает все регионы в плоский список {'id', 'name'}
    """
    areas = []

    def recursive_collect(items):
        for item in items:
            areas.append({
                'id': item['id'],
                'name': item['name']
            })
            if item.get('areas'):
                recursive_collect(item['areas'])

    recursive_collect(data)
    return areas


class AreaManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.areas = []

    def load_areas(self):
        """Загружает и парсит файл с регионами"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Файл не найден: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Если данные — список, используем его напрямую
        if isinstance(raw_data, list):
            self.areas = collect_areas(raw_data)
        else:
            # Иначе пытаемся взять "areas"
            data = raw_data.get("areas", raw_data)
            self.areas = collect_areas(data)

        return self.areas