"""
Модуль AI-оценки соответствия кандидата вакансии через DeepSeek API.
"""

import requests
from utils.logger import setup_logger
import time
from typing import Tuple
from config import conf

# Настройка логгера
logger = setup_logger(__name__)


class AIEvaluator:
    """
    Класс для оценки соответствия кандидата вакансии на основе анализа опыта работы и описания вакансии.

    Methods:
        evaluate_candidate_match: возвращает оценку соответствия кандидата вакансии.
    """

    def evaluate_candidate_match(self, candidate_exp: str, vacancy_description: str) -> Tuple[float, str]:
        """
        Оценивает соответствие кандидата вакансии.

        Args:
            candidate_exp (str): опыт работы кандидата.
            vacancy_description (str): описание вакансии.

        Returns:
            Tuple[float, str]: процент соответствия и объяснение.
        """
        start_time = time.time()

        # Укорачиваем текст для логов, чтобы не перегружать вывод
        exp_short = (candidate_exp[:200] + '...') if len(candidate_exp) > 200 else candidate_exp
        desc_short = (vacancy_description[:200] + '...') if len(vacancy_description) > 200 else vacancy_description

        logger.debug(f"[AI] Начинаем оценку:\nВАКАНСИЯ: {desc_short}\nОПЫТ: {exp_short}")

        if not candidate_exp or not vacancy_description:
            logger.warning("[AI] Недостаточно данных для анализа")
            return 0.0, "Недостаточно данных для анализа."

        prompt = f"""
Проанализируй опыт работы кандидата и оцени, насколько он соответствует следующей вакансии:

ВАКАНСИЯ:
{vacancy_description}

ОПЫТ КАНДИДАТА:
{candidate_exp}

ИНСТРУКЦИЯ:
- Сначала выдели ключевые требования из описания vacancy_description.
- Затем оцени, насколько candidate_exp кандидата явно покрывает эти требования.
- Не делай предположений: если навык/опыт не указан — считай, что его нет.
- Используй шкалу:
  ∙ 90–100 — кандидат полностью соответствует;
  ∙ 70–89 — соответствует, но есть незначительные пробелы;
  ∙ 50–69 — частичное соответствие;
  ∙ менее 50 — слабое соответствие.
- Верни только одно число (процент соответствия) с знаком процента и краткое заключение (до 250 символов).
- Не добавляй лишних слов или форматирования.
- Заключение должно быть уникальным, лаконичным, информативным.

Пример:
75% Кандидат имеет опыт приготовления блюд, но не указано знание выпечки в тандыре. Указаны навыки ножевой обработки и работы на кухне — это плюс.

"""

        url = "https://api.deepseek.com/chat/completions" 
        headers = {
            "Authorization": f"Bearer {conf.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 100
        }

        try:
            logger.debug("[AI] Отправляем запрос к DeepSeek API")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            duration = time.time() - start_time
            logger.debug(f"[AI] Получен ответ за {duration:.2f} сек: {content}")

            parts = content.split(maxsplit=1)
            percent = float(parts[0].replace("%", "").strip())
            explanation = parts[1] if len(parts) > 1 else ""

            return round(percent, 1), explanation[:250]

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error(f"[AI] Ошибка запроса к API за {duration:.2f} сек: {e}", exc_info=True)
            return 0.0, "Ошибка при оценке соответствия."

        except (KeyError, IndexError, ValueError) as e:
            duration = time.time() - start_time
            logger.error(f"[AI] Ошибка разбора ответа от API за {duration:.2f} сек: {e}", exc_info=True)
            return 0.0, "Ошибка при обработке ответа от системы."

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[AI] Непредвиденная ошибка за {duration:.2f} сек: {e}", exc_info=True)
            return 0.0, "Ошибка при оценке соответствия."