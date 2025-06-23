from .main import AreaManager
import os

# Путь к файлу с регионами (относительно корня проекта)
AREAS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "areas_cache.json")

area_manager = AreaManager(AREAS_FILE_PATH)
area_manager.load_areas()