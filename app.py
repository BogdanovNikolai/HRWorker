"""
Модуль Flask-приложения для работы с резюме из HeadHunter.

Содержит роуты:
- /search — поиск резюме по ключевым словам
- /vacancies — список вакансий нашей компании
- /vacancies/<vacancy_id> — отклики по вакансии
- /resumes/<task_id> — просмотр списка резюме
- /export/<task_id> — выгрузка выбранных резюме в формате CSV/XLSX
"""

import json
from typing import List
from flask import Flask, request, render_template, redirect, url_for, send_file, g
from data_manager import dm
from redis_manager import redis_manager
from utils.logger import setup_logger
from config import conf
from data_manager.exporters import CSVExporter, XLSXExporter
from ai import ai_evaluator
from helpers import area_manager

logger = setup_logger(__name__)
app = Flask(__name__)
regions = area_manager.areas


@app.route("/")
def index():
    """
    Главная страница.
    Перенаправляет на /search.
    """
    return redirect(url_for("search"))


@app.route("/search")
def search():
    """
    Страница поиска резюме по ключевым словам.
    После поиска перенаправляет на /resumes/<task_id>
    """
    keywords = request.args.get("keywords", "").strip()
    salary_to = request.args.get("salary_to", type=int)
    region = request.args.getlist('region')
    not_living = bool(request.args.get("not_living"))
    description = request.args.get("description", "").strip()
    total = request.args.get("total", default=20, type=int)

    logger.info(region)

    if not keywords:
        return render_template("search.html", error="Введите ключевые слова для поиска", regions=regions)

    if not region:
        return render_template("search.html", error="Выберите регион для поиска", regions=regions)

    # Ограничиваем максимальное количество на странице
    per_page = 50

    try:
        task_id = dm.search_resumes(
            keywords=keywords,
            salary_to=salary_to,
            region=region,
            not_living=not_living,
            total=total,
            per_page=per_page,
            description=description
        )
        return redirect(url_for("show_resumes", task_id=task_id))
    except ValueError as e:
        logger.warning(f"Ошибка валидации: {e}")
        return render_template("search.html", error=str(e), regions=regions)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при поиске: {e}")
        return render_template("search.html", error="Произошла ошибка при выполнении поиска", regions=regions)


@app.route("/vacancies")
def vacancies():
    """
    Получает список вакансий компании и количество откликов по каждой.
    """

    raw_vacancies = dm.get_company_vacancies()

    if not isinstance(raw_vacancies, list):
        logger.error(f"Ожидается список вакансий, получено: {type(raw_vacancies)}")
        return render_template("vacancies.html", error="Неверный формат данных от HH")

    vacancy_list = []
    for v in raw_vacancies:
        if not isinstance(v, dict):
            logger.warning(f"Найден неверный элемент: {v!r}")
            continue

        v_id = v.get("id")
        vacancy = dm.get_vacancy_by_id(v_id)
        negotiations = dm.get_negotiations_by_vacancy(v_id)
        logger.info(f"Получение откликов по вакансии {v_id}")
        city = vacancy.get("address", {}).get("city", "") if vacancy else ""

        total = len(negotiations)
        unread = sum(1 for n in negotiations if n.get("has_updates", False))

        vacancy_list.append({
            "title": v.get("name", "Без названия"),
            "id": v_id,
            "city": city,
            "responses_total": total,
            "responses_unread": unread,
            "url": v.get("alternate_url", "#")
        })

    return render_template("vacancies.html", vacancies=vacancy_list)


@app.route("/vacancies/<int:vacancy_id>")
def vacancy_responses(vacancy_id: int):
    """
    Отклики по конкретной вакансии.
    Сохраняет список откликов как новую задачу и перенаправляет на /resumes/<task_id>.
    """
    resume_ids, negotiation_ids = dm.get_new_resume_ids_from_negotiations(vacancy_id)
    vacancy = dm.get_vacancy_by_id(vacancy_id)
    description = vacancy.get("description", "") if vacancy else ""

    task_id = redis_manager.create_task(resume_ids, description=description)
    return redirect(url_for("show_resumes", task_id=task_id, negotiation_ids=negotiation_ids))


@app.route("/resumes/<task_id>")
def show_resumes(task_id: str, negotiation_ids: List[int] = None):
    # result = dm.get_task_resumes(task_id=task_id, offset=0, limit=1000)
    # resumes = result.get("items", [])
    # found = len(resumes)

    # # Получаем description из Redis
    # task_data = redis_manager.get_task_data(task_id)
    # description = task_data.get("description", "") if task_data else ""

    # # Обработка AI-оценки (можно оставить как есть)
    # for resume in resumes:
    #     candidate_exp = ""

    #     exp_data = resume.get("experience", [])
    #     if isinstance(exp_data, str):
    #         try:
    #             exp_data = json.loads(exp_data)
    #         except json.JSONDecodeError:
    #             exp_data = []

    #     for exp in exp_data:
    #         if isinstance(exp, dict):
    #             desc = exp.get("description", "").strip()
    #             if desc:
    #                 candidate_exp += desc + "\n\n"

    #     if not candidate_exp:
    #         candidate_exp = "Опыт работы не указан."

    #     match_percent, match_reason = ai_evaluator.evaluate_candidate_match(
    #         candidate_exp=candidate_exp,
    #         vacancy_description=description
    #     )

    #     resume["match_percent"] = match_percent
    #     resume["match_reason"] = match_reason

    # return render_template(
    #     "resume_list.html",
    #     resumes=resumes,
    #     found=found,
    #     current_offset=0,
    #     limit=1000,
    #     task_id=task_id
    # )
    return render_template("resume_list.html", task_id=task_id)


@app.route("/export/<task_id>/<format>")
def export_resumes(task_id: str, format: str):
    """
    Выгрузка резюме в формате CSV или XLSX.

    Args:
        task_id (str): Идентификатор задачи.
        format (str): Формат выгрузки ('csv' или 'xlsx').
    """
    dm.get_task_resumes(task_id)  # Предварительная проверка существования задачи
    exporter = None

    if format == "csv":
        exporter = CSVExporter(data=dm.export_resumes(task_id))
        file_path = f"{conf.OUTPUT_DIR}/resumes_{task_id}.csv"
    elif format == "xlsx":
        exporter = XLSXExporter(data=dm.export_resumes(task_id))
        file_path = f"{conf.OUTPUT_DIR}/resumes_{task_id}.xlsx"
    else:
        return "Неподдерживаемый формат", 400

    exporter.save(file_path)
    return send_file(file_path, as_attachment=True)


# === Роуты для тестирования и отладки ===

@app.route("/manager")
def get_manager_info():
    """
    Получает информацию о текущем менеджере.
    """
    manager = dm.get_current_manager()
    return manager or {"error": "Не удалось получить данные"}


@app.route("/limits")
def get_resume_limits():
    manager_id = dm.get_current_manager_id()
    if not manager_id:
        return {"error": "Не найден ID менеджера"}
    raw_limits = dm.get_resume_limits(manager_id)
    
    # Упрощённая структура
    simplified = {
        "used": raw_limits.get("spend", {}).get("resume_view", 0),
        "total": raw_limits.get("limits", {}).get("resume_view", 0),
        "left": raw_limits.get("left", {}).get("resume_view", 0),
    }

    return {
        "token_used": dm.hh_client.access_token[:8] + "...",
        "manager_id": manager_id,
        "limits": simplified
    }


@app.before_request
def load_resume_limits():
    try:
        manager_id = dm.get_current_manager_id()
        if manager_id:
            limits = dm.get_resume_limits(manager_id)
            g.resume_limits = limits
        else:
            g.resume_limits = {"error": "Нет ID менеджера"}
    except Exception as e:
        logger.warning(f"Не удалось загрузить лимиты: {e}")
        g.resume_limits = {"error": "Ошибка загрузки лимитов"}


# === Новый API-роут для AJAX ===

@app.route("/api/resumes/<task_id>")
def get_resumes_json(task_id: str):
    result = dm.get_task_resumes(task_id=task_id, offset=0, limit=1000)
    resumes = result.get("items", [])
    
    # Получаем description из Redis
    task_data = redis_manager.get_task_data(task_id)
    description = task_data.get("description", "") if task_data else ""

    processed_resumes = []
    count=1
    for resume in resumes:
        candidate_exp = ""
        exp_data = resume.get("experience", [])
        if isinstance(exp_data, str):
            try:
                exp_data = json.loads(exp_data)
            except json.JSONDecodeError:
                exp_data = []
        for exp in exp_data:
            if isinstance(exp, dict):
                desc = exp.get("description", "").strip()
                if desc:
                    candidate_exp += desc + "\n"
        if not candidate_exp:
            candidate_exp = "Опыт работы не указан."

        match_percent, match_reason = ai_evaluator.evaluate_candidate_match(
            candidate_exp=candidate_exp,
            vacancy_description=description
        )
        
        logger.info(f"Кандидат добавлен {count}/{len(resumes)}")
        count += 1

        processed_resumes.append({
            "id": resume.get("id"),
            "first_name": resume.get("first_name"),
            "last_name": resume.get("last_name"),
            "middle_name": resume.get("middle_name"),
            "age": resume.get("age"),
            "area": resume.get("area", {}).get("name") if resume.get("area") else "-",
            "title": resume.get("title"),
            "salary": f"{resume.get('salary', {}).get('amount')} {resume.get('salary', {}).get('currency')}" if resume.get("salary") else "—",
            "total_experience": resume.get("total_experience", {}).get("months", 0) if resume.get("total_experience") else 0,
            "match_percent": match_percent,
            "alternate_url": resume.get("alternate_url"),
        })

    return {"resumes": processed_resumes}