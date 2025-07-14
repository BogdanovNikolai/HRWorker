import pyautogui
import time
import webbrowser
from config import conf
from utils.logger import setup_logger

logger = setup_logger(__name__)


class EStaffBot:
    def __init__(self):
        self.estaff_module_icon=conf.ESTAFF_MODULE_ICON
        self.estaff_module_icon_2=conf.ESTAFF_MODULE_ICON_2
        self.estaff_save=conf.ESTAFF_SAVE
        self.estaff_save_duble=conf.ESTAFF_SAVE_DUBLE
        self.base_url="https://www.hh.ru/resume/"

    def open_resume(self, resume_id):
        """Открывает резюме по указанному ID"""
        url = f"{self.base_url}{resume_id}"
        logger.info(f"Открываем ссылку: {url}")
        webbrowser.open(url)

        # Даем время на загрузку страницы
        time.sleep(7)

    def click_on_image(self, image_path, confidence=0.9):
        """
        Ищет изображение на экране и кликает по центру, если найдено.
        :param image_path: Путь к изображению для поиска
        :param confidence: Точность распознавания (0.0 - 1.0)
        :return: True, если кликнул, иначе False
        """
        time.sleep(5)
        logger.info(f"Ищем изображение: {image_path}...")
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                x, y = center
                logger.info(f"Нашли! Кликаем по координатам: x={x}, y={y}")
                pyautogui.click(x, y)
                return True
            else:
                logger.warning(f"Изображение не найдено: {image_path}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при поиске или клике по изображению '{image_path}': {e}")
            return False

    def process_resume(self, resume_id):
        """Полный процесс: открытие одного резюме и клики по двум изображениям"""
        logger.info(f"Обработка резюме с ID: {resume_id}")

        self.open_resume(resume_id)
        
        # Первый клик: пробуем основное изображение, если не получается — альтернативное
        clicked = self.click_on_image(self.estaff_module_icon)
        if not clicked:
            logger.info("Пробуем альтернативную иконку модуля...")
            clicked = self.click_on_image(self.estaff_module_icon_2)
        
        if not clicked:
            logger.error(f"Не удалось кликнуть по модулю для резюме {resume_id}.")
            return False

        # Второй клик: пробуем основной save, если не получается — дубликат
        clicked = self.click_on_image(self.estaff_save)
        if not clicked:
            logger.info("Пробуем второй вариант кнопки сохранения...")
            clicked = self.click_on_image(self.estaff_save_duble)
            clicked = self.click_on_image(self.estaff_save)

        if not clicked:
            logger.error(f"Не удалось сохранить для резюме {resume_id}.")
            return False

        logger.info(f"Резюме {resume_id} успешно обработано.")
        return True

    def process_resumes(self, resume_ids):
        """
        Обрабатывает список резюме по одному
        :param resume_ids: список ID резюме
        :return: словарь с результатами {id: True/False}
        """
        results = {}
        for resume_id in resume_ids:
            success = self.process_resume(resume_id)
            results[resume_id] = success

        return results