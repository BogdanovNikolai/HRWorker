from datetime import datetime
import requests
import time
import logging
from pprint import pprint
from utils.logger import setup_logger
from config import conf

# Создаем базовый логгер
logger = setup_logger(__name__)

class AvitoAPIClient:
    def __init__(self):
        self.client_id = conf.AVITO_API_CLIENT
        self.client_secret = conf.AVITO_CLIENT_SECRET
        self.token_url = "https://api.avito.ru/token"
        self.api_base_url = "https://api.avito.ru"

        # Кэширование токена
        self.access_token = None
        self.token_expiry = 0

    def get_access_token(self):
        """Получение или обновление access token с кэшированием"""
        current_time = time.time()
        if self.access_token and current_time < self.token_expiry:
            return self.access_token

        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        response = requests.post(self.token_url, data=data)

        if response.status_code == 200:
            json_response = response.json()
            self.access_token = json_response['access_token']
            self.token_expiry = current_time + json_response.get('expires_in', 3600)
            logger.info("Токен AVITO успешно обновлён")
            return self.access_token
        else:
            logger.error(f"Ошибка получения токена: {response.status_code}, {response.text}")
            raise Exception(f"Ошибка получения токена: {response.status_code}, {response.text}")

    def per_pager(self, total: int, per_page: int = 25):
        """
        Генератор для пагинации.
        :param total: общее количество записей
        :param per_page: количество записей на странице (max 100)
        :yield: page, per_page
        """
        per_page = min(per_page, 100)  # Ограничение максимального количества на странице
        pages = (total + per_page - 1) // per_page  # Округление вверх
        for page in range(1, pages + 1):
            yield page, per_page

    def make_api_request(self, endpoint, method='GET', params=None, data=None,
                        retries=3, delay=5, total=None, per_page=25, expected_list_key: bool = True):
        """
        Выполнение запроса к API с поддержкой пагинации и агрегацией total результатов.

        :param endpoint: Путь к API (без базового URL)
        :param method: HTTP метод (GET, POST и т.д.)
        :param params: Параметры запроса
        :param data: Тело запроса (для POST)
        :param retries: Количество попыток при ошибках сети или 429
        :param delay: Задержка между повторными попытками
        :param total: Общее количество элементов, которые нужно собрать
        :param per_page: Кол-во элементов на странице (максимум 100)
        :return: dict с ключами 'found' и 'items'
        """
        url = f"{self.api_base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json'
        }

        if total is None:
            time.sleep(1.1)
            # Обычный однократный запрос, но всегда возвращаем dict
            for attempt in range(retries):
                time.sleep(1.1)
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=data
                    )
                    if response.status_code == 200:
                        json_data = response.json()

                        # Находим первое поле со списком — например, resumes, items, results
                        if expected_list_key:
                            key = next((k for k in json_data if isinstance(json_data[k], list)), None)
                            
                            if not key:
                                logger.warning("Не найден список в ответе API.")
                                return {"found": 0, "items": []}
                            
                            items = json_data[key]
                            
                            for item in items:
                                item['url'] = f"https://avito.ru{item['url']}"
                                
                            result = {
                                "found": len(items),
                                "items": items,
                            }
                        else:
                            resume = json_data

                            if not resume:
                                logger.warning("Не найдено резюме в ответе API.")
                                return {"found": 0, "items": []}

                            resume['id'] = str(resume['id'])
                            resume['url'] = f"https://avito.ru{resume['url']}"
                            result = resume
                                             
                        return result

                    elif response.status_code == 429:
                        logger.warning("Rate limit exceeded. Waiting...")
                        time.sleep(delay * (attempt + 1))
                    else:
                        logger.error(f"Ошибка API: {response.status_code}, {response.text}")
                        return {"found": 0, "items": []}
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error: {e}")
                    if attempt < retries - 1:
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise
            return {"found": 0, "items": []}

        # Если задан total — агрегируем результат с постраничными запросами
        aggregated_results = []
        page = 1
        per_page = min(per_page, 100)

        while len(aggregated_results) < total:
            time.sleep(1.1)
            actual_params = params.copy() if params else {}
            actual_params.update({
                'page': page,
                'perPage': per_page
            })

            success = False
            for attempt in range(retries):
                time.sleep(1.1)
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=actual_params,
                        json=data
                    )
                    if response.status_code == 200:
                        json_data = response.json()

                        # Находим первое поле со списком — например, resumes, items, results
                        key = next((k for k in json_data if isinstance(json_data[k], list)), None)
                        if not key:
                            logger.warning("Не найден список в ответе API.")
                            return {"found": len(aggregated_results), "items": aggregated_results}

                        batch = json_data[key]
                        aggregated_results.extend(batch)

                        if len(batch) < per_page:
                            # Последняя страница
                            break

                        page += 1
                        success = True
                        break
                    elif response.status_code == 429:
                        logger.warning("Rate limit exceeded. Waiting...")
                        time.sleep(delay * (attempt + 1))
                    else:
                        logger.error(f"Ошибка API: {response.status_code}, {response.text}")
                        break
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error: {e}")
                    if attempt < retries - 1:
                        time.sleep(delay * (attempt + 1))
                    else:
                        raise

            if not success:
                logger.error(f"Не удалось получить страницу {page}")
                
        result = {
            "found": len(aggregated_results),
            "items": aggregated_results[:total]
        }

        return result

    # --- Работа с резюме ---
    def resumes(self, query="Программист", location=107620, total=1, experience=None, salary_min=None, schedule=None):
        """Поиск резюме по заданным параметрам"""
        endpoint = "/job/v1/resumes/"
        params = {'query': query, 'location': location}
        if experience:
            params['experience'] = experience
        if salary_min:
            params['salaryMin'] = salary_min
        if schedule:
            params['schedule'] = schedule

        return self.make_api_request(endpoint, params=params, total=total, per_page=100)
    
    def resume(self, resume_id):
        """Получение данных резюме по resume_id"""
        endpoint = f"/job/v2/resumes/{resume_id}/"
        
        logger.debug(f"Ищем резюме из Avito с ID = {resume_id}")
        
        return self.make_api_request(endpoint, expected_list_key=False)
    
    def contacts(self, resume_id):
        """Получение контактов по resume_id"""
        endpoint = f"/job/v1/resumes/{resume_id}/contacts/"
        
        return self.make_api_request(endpoint)
    
    def format_salary(self, salary):
        """
        Приводит зарплату к формату:
        {
            "amount": 100000,
            "currency": "RUR"
        }
        :param salary: может быть int, float, str, None
        :return: dict
        """
        try:
            amount = int(float(salary))  # Поддержка чисел и строк с числами
        except (TypeError, ValueError, Exception):
            amount = None

        return {
            "amount": amount if amount is not None else None,
            "currency": "RUR"  # Всегда RUR для Avito
        }

    # --- Работа с вакансиями ---
    def get_company_vacancies(self):
        """Получение списка вакансий компании"""
        endpoint = "/job/v1/vacancies/"
        params = {}
        
        logger.debug("Получаем список вакансий компании с Avito")
        
        return self.make_api_request(endpoint, params=params, total=None, per_page=100)
    
    def get_vacancy_by_id(self, vacancy_id):
        """Получение данных вакансии по vacancy_id"""
        endpoint = f"/job/v1/vacancies/{vacancy_id}/"
        
        logger.debug(f"Получаем вакансию из Avito с ID = {vacancy_id}")
        
        return self.make_api_request(endpoint, expected_list_key=False)
    
    def get_vacancy_responses(self, vacancy_id, per_page=50):
        """Получение откликов на вакансию по vacancy_id"""
        endpoint = f"/job/v1/vacancies/{vacancy_id}/responses/"
        params = {'perPage': per_page}
        
        logger.debug(f"Получаем отклики на вакансию Avito с ID = {vacancy_id}")
        
        return self.make_api_request(endpoint, params=params, total=None, per_page=per_page)
    
    def get_new_vacancy_responses(self, vacancy_id, per_page=50):
        """Получение новых откликов на вакансию по vacancy_id"""
        endpoint = f"/job/v1/vacancies/{vacancy_id}/responses/"
        params = {'perPage': per_page, 'status': 'new'}  # Предполагаем, что есть фильтр по статусу
        
        logger.debug(f"Получаем новые отклики на вакансию Avito с ID = {vacancy_id}")
        
        return self.make_api_request(endpoint, params=params, total=None, per_page=per_page)
    
    def mark_responses_as_read(self, vacancy_id, response_ids):
        """Отметить отклики как прочитанные"""
        endpoint = f"/job/v1/vacancies/{vacancy_id}/responses/read/"
        data = {'response_ids': response_ids}
        
        logger.debug(f"Отмечаем отклики как прочитанные для вакансии Avito с ID = {vacancy_id}")
        
        return self.make_api_request(endpoint, method='POST', data=data, expected_list_key=False)

    def get_vacancies(self):
        """
        Получение списка вакансий через новый Avito API.
        """
        endpoint = "/core/v1/items"
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}'
        }
        url = f"{self.api_base_url}{endpoint}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Ошибка получения вакансий: {response.status_code}, {response.text}")
            return {"items": []}

    def get_application_ids(self, updated_at_from=None):
        """
        Получение всех ID откликов по вакансиям.
        """
        endpoint = "/job/v1/applications/get_ids"
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}'
        }
        params = {}
        if updated_at_from:
            params['updatedAtFrom'] = updated_at_from
        url = f"{self.api_base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Ошибка получения ID откликов: {response.status_code}, {response.text}")
            return {"applies": []}

    def get_applications_by_ids(self, app_ids):
        """
        Получение информации об откликах по их ID.
        """
        endpoint = "/job/v1/applications/get_by_ids"
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json'
        }
        url = f"{self.api_base_url}{endpoint}"
        payload = {"ids": app_ids}
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Ошибка получения деталей откликов: {response.status_code}, {response.text}")
            return {"applies": []}


if __name__ == "__main__":
    avito = AvitoAPIClient()
    
    resumes_data = avito.resumes(query="Python разработчик", location=107620)

    if resumes_data and 'items' in resumes_data:
        for resume in resumes_data['items']:
            resume_id = resume.get('id')
            if resume_id:
                candidate_info = avito.resume(resume_id)

                if candidate_info:
                    title = candidate_info.get('title')
                    params = candidate_info.get('params', {})
                    age = params.get('age')
                    location = params.get('address')
                    exp_time = params.get('experience')
                    exp_desc = params.get('experience_list')
                    salary = candidate_info.get('salary')
                    url = f"avito.ru{candidate_info.get('url')}"
                
                    answer = {
                        'id': resume_id,
                        'title': title,
                        'age': age,
                        'location': location,
                        'salary': salary,
                        'experience': exp_desc,
                        'total_experience': exp_time * 12 if exp_time else 0,
                        'link': url,
                        'received_at': datetime.utcnow(),
                    }

                    logger.info(answer)