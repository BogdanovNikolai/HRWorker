"""
Модуль Flask-приложения для работы с резюме из HeadHunter.

Содержит роуты:
- /search — поиск резюме по ключевым словам
- /vacancies — список вакансий нашей компании
- /vacancies/<vacancy_id> — отклики по вакансии
- /resumes/<task_id> — просмотр списка резюме
- /export/<task_id> — выгрузка выбранных резюме в формате CSV/XLSX
"""

from datetime import datetime
import json
from flask import Flask, request, render_template, redirect, url_for, send_file, g
from markupsafe import Markup
from data_manager import dm
from redis_manager import redis_manager
from utils.logger import setup_logger
from utils.decorators import log_function_call
from config import conf
from data_manager.exporters import CSVExporter, XLSXExporter, EStaffExporter
from ai import ai_evaluator
from helpers import area_manager
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import pytz



logger = setup_logger(__name__)
app = Flask(__name__)
regions = area_manager.areas
scheduler = None



def init_scheduler():
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(dm.update_vacancies_cache, 'cron', hour=8)
    scheduler.add_job(dm.update_vacancies_cache_avito, 'cron', hour=8)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

def check_and_update_vacancies_cache_on_startup():
    """
    Проверяет, есть ли в Redis кэш вакансий.
    Если его нет или он был создан до 8:00 утра текущего дня — обновляет его.
    """
    cache_key = "cached_company_vacancies"
    current_time = datetime.now(pytz.timezone("Europe/Moscow"))
    today_8am = current_time.replace(hour=8, minute=0, second=0, microsecond=0)

    cached_data = dm.redis_manager.client.get(cache_key)

    if not cached_data:
        logger.warning("Кэш вакансий не найден. Запуск фонового обновления...")
        dm.update_vacancies_cache()
        return

    try:
        ttl = dm.redis_manager.client.ttl(cache_key)
        if ttl < 0:
            logger.warning("Ключ в Redis просрочен. Обновляем кэш...")
            dm.update_vacancies_cache()
        # elif current_time > today_8am and ttl < (24 * 60 * 60 - 5 * 60):
        #     logger.info("Кэш существует, но возможно устарел относительно сегодняшнего 8:00. Обновляем...")
        #     dm.update_vacancies_cache()
        else:
            logger.info("Кэш вакансий актуален.")
    except Exception as e:
        logger.error(f"Ошибка при проверке актуальности кэша: {e}. Выполняем принудительное обновление...")
        dm.update_vacancies_cache()


@log_function_call
@app.route("/")
def index():
    """
    Главная страница.
    Перенаправляет на /search.
    """
    
    return redirect(url_for("search"))

@log_function_call
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
    source = request.args.get("source", default="hh")

    if not keywords:
        return render_template("search.html", error="Введите ключевые слова для поиска", regions=regions)

    if not region:
        return render_template("search.html", error="Выберите регион для поиска", regions=regions)

    try:
        task_id = dm.search_resumes(
            keywords=keywords,
            salary_to=salary_to,
            region=region,
            not_living=not_living,
            total=total,
            description=description,
            source=source,
        )
        return redirect(url_for("show_resumes", task_id=task_id, source=source))
    except ValueError as e:
        logger.warning(f"Ошибка валидации: {e}")
        return render_template("search.html", error=str(e), regions=regions)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при поиске: {e}")
        return render_template("search.html", error="Произошла ошибка при выполнении поиска", regions=regions)

@log_function_call
@app.route("/vacancies")
def vacancies():
    """
    Отображает список вакансий из кэша Redis.
    """
    cache_key = "cached_company_vacancies"
    cached_data = dm.redis_manager.client.get(cache_key)

    if cached_data:
        try:
            vacancy_list = json.loads(cached_data)
            return render_template("vacancies.html", vacancies=vacancy_list)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON из кэша: {e}")
            return render_template("vacancies.html", error="Не удалось загрузить кэшированные данные")
    else:
        return render_template("vacancies.html", error="Данные о вакансиях ещё не загружены. Попробуйте позже.")
    
@app.route("/update-vacancies-cache")
def manual_update_vacancies():
    """Ручное обновление кэша вакансий."""
    dm.update_vacancies_cache()
    return "Кэш вакансий обновлён."

@log_function_call
@app.route("/vacancies/<int:vacancy_id>")
def vacancy_responses(vacancy_id: int, source: str = "hh"):
    """
    Отклики по конкретной вакансии.
    Сохраняет список откликов как новую задачу и перенаправляет на /resumes/<task_id>.
    """
    resume_ids, negotiation_ids = dm.get_new_resume_ids_from_negotiations(vacancy_id)

    # маппинг resume_id: negotiation_id для передачи на фронт
    resume_to_negotiation = dict(zip(resume_ids, negotiation_ids))
    
    vacancy = dm.get_vacancy_by_id(vacancy_id)
    description = vacancy.get("description", "") if vacancy else ""

    task_id = redis_manager.create_task(resume_ids, description=description)

    return redirect(url_for("show_resumes", task_id=task_id, source=source, resume_negotiation_map=json.dumps(resume_to_negotiation)))

# --- Роуты для вакансий Avito ---
@log_function_call
@app.route("/vacancies_avito")
def vacancies_avito():
    """
    Отображает список вакансий Avito из кэша Redis.
    """
    cache_key = "cached_company_vacancies_avito"
    cached_data = dm.redis_manager.client.get(cache_key)

    if cached_data:
        try:
            vacancy_list = json.loads(cached_data)
            return render_template("vacancies_avito.html", vacancies=vacancy_list)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON из кэша Avito: {e}")
            return render_template("vacancies_avito.html", error="Не удалось загрузить кэшированные данные")
    else:
        return render_template("vacancies_avito.html", error="Данные о вакансиях Avito ещё не загружены. Попробуйте позже.")
    
@app.route("/update-vacancies-cache-avito")
def manual_update_vacancies_avito():
    """Ручное обновление кэша вакансий Avito."""
    dm.update_vacancies_cache_avito()
    return "Кэш вакансий Avito обновлён."

@log_function_call
@app.route("/vacancies_avito/<int:vacancy_id>")
def vacancy_responses_avito(vacancy_id: int):
    """
    Отклики по конкретной вакансии Avito.
    Сохраняет список откликов как новую задачу и перенаправляет на /resumes/<task_id>.
    """
    resume_ids, response_ids = dm.get_new_resume_ids_from_negotiations_avito(vacancy_id)

    # маппинг resume_id: response_id для передачи на фронт
    resume_to_response = dict(zip(resume_ids, response_ids))
    
    vacancy = dm.get_vacancy_by_id_avito(vacancy_id)
    description = vacancy.get("description", "") if vacancy else ""

    task_id = redis_manager.create_task(resume_ids, description=description)

    return redirect(url_for("show_resumes", task_id=task_id, source="avito", resume_negotiation_map=json.dumps(resume_to_response)))

@log_function_call
@app.route("/resumes/<task_id>")
def show_resumes(task_id: str, source: str = "hh"):
    source = request.args.get("source", "hh")
    map_json = request.args.get("resume_negotiation_map")

    try:
        negotiation_map = json.loads(map_json) if map_json else {}
    except json.JSONDecodeError:
        negotiation_map = {}

    safe_json = json.dumps(negotiation_map)

    return render_template(
        "resume_list.html",
        task_id=task_id,
        source=source,
        resume_negotiation_map=Markup(safe_json)
    )

@log_function_call
@app.route("/export/<task_id>/<format>", methods=["POST"])
def export_resumes(task_id: str, format: str):
    """
    Выгрузка выбранных резюме в формате CSV или XLSX.
    Принимает уже обработанные данные от клиента, но дополняет их опытом из БД.
    """
    resume_data = request.form.get("resume_data")
    if not resume_data:
        return "Нет данных для экспорта", 400

    try:
        # Предполагаем, что resume_data содержит список резюме с id и, возможно, другими полями
        all_resumes = json.loads(resume_data)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return "Неверный формат данных", 400

    # Извлекаем ID резюме из полученных данных
    selected_ids = [r.get("id") for r in all_resumes if r.get("id")]

    if not selected_ids:
        return "Не указаны ID резюме", 400

    # Получаем полные данные из БД по task_id и фильтруем по ID
    full_resumes = dm.export_resumes(task_id)
    full_resumes_dict = {r["id"]: r for r in full_resumes}

    # Добавляем опыт и другие данные из БД в each resume
    enriched_resumes = []
    for resume in all_resumes:
        resume_id = resume.get("id")
        if resume_id in full_resumes_dict:
            # Сохраняем существующие поля из all_resumes и дополняем данными из БД
            enriched = {**resume, **full_resumes_dict[resume_id]}
            enriched_resumes.append(enriched)
        else:
            # Если не найдено в БД — оставляем как есть (или можно пропустить)
            enriched_resumes.append(resume)

    # Проверяем наличие данных после enrich
    if not enriched_resumes:
        return "Нет данных для экспорта после дополнения", 400

    # Экспортируем
    exporter = None
    if format == "csv":
        exporter = CSVExporter(data=enriched_resumes)
        file_path = f"{conf.OUTPUT_DIR}/resumes_{task_id}.csv"
    elif format == "xlsx":
        exporter = XLSXExporter(data=enriched_resumes)
        file_path = f"{conf.OUTPUT_DIR}/resumes_{task_id}.xlsx"
    elif format == "estaff":
        exporter = EStaffExporter.export(resume_ids=selected_ids)
        return "Экспортировано в E-Staff", 200
    else:
        return "Неподдерживаемый формат", 400

    exporter.save(file_path)
    return send_file(file_path, as_attachment=True)

#   <== API-эндпоинты ==>
@log_function_call
@app.route("/api/limits")
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

@log_function_call
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

@log_function_call
@app.route("/api/resumes/<task_id>")
def get_resumes_json(task_id: str):
    source = request.args.get("source", "hh")
    map_json = request.args.get("resume_negotiation_map")
    negotiation_map = None
    if map_json:
        try:
            negotiation_map = json.loads(map_json)
        except Exception:
            negotiation_map = None

    responses = None
    if source == "avito" and negotiation_map:
        # Собираем все response_id и получаем отклики через DataManager
        response_ids = list(negotiation_map.values())
        # Получаем все отклики (responses) по этим ID
        # Используем метод AvitoAPIClient.get_applications_by_ids
        responses_data = None
        if response_ids:
            responses_data = dm.avito_client.get_applications_by_ids(response_ids)
            responses = responses_data.get("applies", []) if responses_data else []

    result = dm.get_task_resumes(task_id=task_id, offset=0, limit=1000, source=source, negotiation_map=negotiation_map, responses=responses)
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
        if exp_data:
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
        
        if source == "hh":
            link = resume.get("alternate_url") or resume.get("link")
            if not link:
                link = resume.get("url")
            
            total_experience_months = \
                                resume.get("total_experience", {}).get("months", 0) if resume.get("total_experience") else 0
        else:
            link = f"{resume.get('link')}" or None
            if not link:
                link = f"{resume.get('url')}"
            link = f"{link}"
            total_experience_months = \
                                resume.get("total_experience", {}).get("months", 0) if resume.get("total_experience") else 0
        
        count += 1

        processed_resumes.append({
            "id": resume.get("id"),
            "first_name": resume.get("first_name"),
            "last_name": resume.get("last_name"),
            "middle_name": resume.get("middle_name"),
            "age": resume.get("age"),
            "area": resume.get("area", {}).get("name") if isinstance(resume.get("area"), dict) else resume.get("area", "-"),
            "title": resume.get("title"),
            "salary": f"{resume.get('salary', {}).get('amount')} {resume.get('salary', {}).get('currency')}" if resume.get("salary") else "—",
            "total_experience": total_experience_months,
            "match_percent": match_percent,
            "link": link,
        })

    return {"items": processed_resumes, "found": len(processed_resumes)}

@log_function_call
@app.route("/api/read_negotiations", methods=["POST"])
def read_negotiations():
    data = request.get_json()
    negotiation_ids = data.get("negotiation_ids", [])

    if not negotiation_ids:
        return {"error": "Не переданы negotiation_ids"}, 400

    try:
        success = dm.read_negotiations(negotiation_ids)
        if success:
            return {"status": "ok"}
        else:
            return {"error": "Не удалось пометить отклики как прочитанные"}, 500
    except Exception as e:
        logger.error(f"Ошибка при пометке откликов: {e}")
        return {"error": "Внутренняя ошибка сервера"}, 500

@log_function_call
@app.route("/api/read_negotiations_avito", methods=["POST"])
def read_negotiations_avito():
    data = request.get_json()
    vacancy_id = data.get("vacancy_id")
    response_ids = data.get("response_ids", [])

    if not vacancy_id:
        return {"error": "Не передан vacancy_id"}, 400

    if not response_ids:
        return {"error": "Не переданы response_ids"}, 400

    try:
        success = dm.read_negotiations_avito(vacancy_id, response_ids)
        if success:
            return {"status": "ok"}
        else:
            return {"error": "Не удалось пометить отклики Avito как прочитанные"}, 500
    except Exception as e:
        logger.error(f"Ошибка при пометке откликов Avito: {e}")
        return {"error": "Внутренняя ошибка сервера"}, 500