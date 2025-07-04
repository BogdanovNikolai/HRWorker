from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Resume


def get_random_complete_resume(db: Session) -> Resume:
    """
    Возвращает одно случайное резюме, где все доступные поля заполнены.
    """
    resume = (
        db.query(Resume)
        .filter(
            Resume.id.isnot(None),
            Resume.first_name.isnot(None),
            Resume.middle_name.isnot(None),
            Resume.last_name.isnot(None),
            Resume.title.isnot(None),
            Resume.age.isnot(None),
            Resume.location.isnot(None),
            Resume.salary_json.isnot(None),
            Resume.experience.isnot(None),
            Resume.total_experience_months.isnot(None),
            Resume.link.isnot(None),
            Resume.received_at.isnot(None),
        )
        .order_by(func.random())
        .first()
    )

    return resume


def compare_resume_with_expected(resume_obj: Resume, expected_data: dict) -> dict:
    """
    Сравнивает поля объекта Resume с ожидаемыми значениями.
    Возвращает словарь с расхождениями.
    """
    mismatches = {}

    for field, expected_value in expected_data.items():
        actual_value = getattr(resume_obj, field, None)

        if isinstance(actual_value, datetime):
            actual_value = actual_value.isoformat() if actual_value else None
        if isinstance(expected_value, datetime):
            expected_value = expected_value.isoformat()

        if actual_value != expected_value:
            mismatches[field] = {
                "expected": expected_value,
                "actual": actual_value
            }

    return mismatches


def main():
    db = next(get_db())

    try:
        # 1. Получаем случайное полностью заполненное резюме из БД
        resume_record = get_random_complete_resume(db)

        if not resume_record:
            print("❌ Не найдено ни одного полностью заполненного резюме.")
            return

        print(f"✅ Найдено резюме: {resume_record.first_name} {resume_record.last_name} ({resume_record.title})")

        # 2. Пример данных из output.txt / XML
        expected_data = {
            "id": "0x6790A04267CC4A4B",
            "first_name": "Aleksandr",
            "last_name": "Bepkytov",
            "title": "Разнорабочий",
            "mobile_phone": "+79030182030",
            "source_id": "hh.ru",
            "educ_type_id": 1,
            "work_type_id": 1,
            "state_id": "phone_interview:call_failed",
            "is_active": 1,
            "last_comment": "но, смс.",
            "link": "https://hh.ru/resume/... ",
            "received_at": "2025-01-22T11:06:26+03:00",
        }

        # 3. Сравниваем
        mismatches = compare_resume_with_expected(resume_record, expected_data)

        if not mismatches:
            print("✅ Все поля совпадают.")
        else:
            print("⚠️ Найдены расхождения:")
            for field, values in mismatches.items():
                print(f" - Поле '{field}':")
                print(f"     Ожидается: {values['expected']}")
                print(f"     Получено:  {values['actual']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()