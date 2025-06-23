import os
from pathlib import Path

# === Настройки ===
PROJECT_ROOT = "."  # корень проекта (текущая директория)
OUTPUT_FILE = "project_tree.txt"  # выходной файл

# Какие файлы читать (расширения)
INCLUDE_EXTENSIONS = [".py", ".txt", ".md", ".env", ".json"]

# Какие директории игнорировать
IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "migrations",
    ".pytest_cache",
    "env"
}

# Какие файлы игнорировать по имени
IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.log"
}


def is_ignored(path: str, ignore_list):
    """Проверяет, находится ли элемент в списке игнорируемых."""
    name = os.path.basename(path)
    for pattern in ignore_list:
        if name == pattern or (pattern.startswith("*") and name.endswith(pattern[1:])):
            return True
    return False


def walk_directory(root_dir, prefix="", level=0, max_level=3):
    """Рекурсивно обходит директорию и строит дерево."""
    tree = []
    root_path = Path(root_dir)

    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        return [f"{prefix}! [Ошибка доступа]"]

    for i, entry in enumerate(entries):
        path = root_path / entry

        if path.name in IGNORE_DIRS or is_ignored(entry, IGNORE_DIRS):
            continue

        connector = "└── " if i == len(entries) - 1 else "├── "

        if path.is_dir():
            tree.append(f"{prefix}{connector}[{entry}/]")
            if level < max_level:
                subtree = walk_directory(
                    path,
                    prefix + ("    " if i == len(entries) - 1 else "│   "),
                    level + 1,
                    max_level
                )
                tree.extend(subtree)
        else:
            if is_ignored(entry, IGNORE_FILES):
                continue
            tree.append(f"{prefix}{connector}{entry}")
            if any(entry.endswith(ext) for ext in INCLUDE_EXTENSIONS):
                tree.append(f"{prefix}    └── CONTENT:")
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().strip()
                        lines = content.splitlines()
                        for line in lines[:20]:  # ограничиваем до 20 строк
                            tree.append(f"{prefix}        {line}")
                        if len(lines) > 20:
                            tree.append(f"{prefix}        ...")
                except Exception as e:
                    tree.append(f"{prefix}        [Ошибка чтения файла: {e}]")
    return tree


if __name__ == "__main__":
    print("Строю древовидную структуру проекта...\n")

    tree_lines = ["=== Дерево проекта ===\n"]
    tree_lines.extend(walk_directory(PROJECT_ROOT))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(tree_lines))

    print(f"\n✅ Структура проекта сохранена в файл: {OUTPUT_FILE}")
    print("Теперь ты можешь отправить этот файл мне.")