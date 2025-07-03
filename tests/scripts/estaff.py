import pyautogui
import time
import webbrowser


class EStaffBot:
    def __init__(self, 
                 base_url="https://www.hh.ru/resume/",
                 estaff_module_icon="C:\\Users\\bogdanov.na\\Work\\HRWorker\\tests\\scripts\\estaff_module_icon.png",
                 estaff_module_icon_2="C:\\Users\\bogdanov.na\\Work\\HRWorker\\tests\\scripts\\estaff_module_icon_2.png",
                 estaff_save="C:\\Users\\bogdanov.na\\Work\\HRWorker\\tests\\scripts\\estaff_save.png",
                 estaff_save_duble="C:\\Users\\bogdanov.na\\Work\\HRWorker\\tests\\scripts\\estaff_save_duble.png",
                ):
        self.base_url = base_url
        self.estaff_module_icon = estaff_module_icon
        self.estaff_module_icon_2 = estaff_module_icon_2
        self.estaff_save = estaff_save
        self.estaff_save_duble = estaff_save_duble

    def open_resume(self, resume_id):
        """Открывает резюме по указанному ID"""
        url = f"{self.base_url}{resume_id}"
        print(f"Открываем ссылку: {url}")
        webbrowser.open(url)

        # Даем время на загрузку страницы
        time.sleep(5)

    def click_on_image(self, image_path, confidence=0.9):
        """
        Ищет изображение на экране и кликает по центру, если найдено.
        :param image_path: Путь к изображению для поиска
        :param confidence: Точность распознавания (0.0 - 1.0)
        :return: True, если кликнул, иначе False
        """
        print(f"Ищем изображение: {image_path}...")
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                x, y = center
                print(f"Нашли! Кликаем по координатам: x={x}, y={y}")
                pyautogui.click(x, y)
                return True
            else:
                print(f"Изображение не найдено: {image_path}")
                return False
        except Exception as e:
            print(f"Ошибка при поиске или клике по изображению '{image_path}': {e}")
            return False

    def process_resume(self, resume_id):
        """Полный процесс: открытие одного резюме и клики по двум изображениям"""
        print(f"Обработка резюме с ID: {resume_id}")
        self.open_resume(resume_id)

        time.sleep(2)
        
        # Первый клик: пробуем основное изображение, если не получается — альтернативное
        clicked = self.click_on_image(self.estaff_module_icon)
        if not clicked:
            print("Пробуем альтернативную иконку модуля...")
            clicked = self.click_on_image(self.estaff_module_icon_2)
        
        if not clicked:
            print(f"Не удалось кликнуть по модулю для резюме {resume_id}.")
            return False

        time.sleep(2)

        # Второй клик: пробуем основной save, если не получается — дубликат
        clicked = self.click_on_image(self.estaff_save)
        if not clicked:
            print("Пробуем второй вариант кнопки сохранения...")
            clicked = self.click_on_image(self.estaff_save_duble)
            time.sleep(1)
            clicked = self.click_on_image(self.estaff_save)

        if not clicked:
            print(f"Не удалось сохранить для резюме {resume_id}.")
            return False

        print(f"Резюме {resume_id} успешно обработано.")
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