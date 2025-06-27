import os

# Расширения, которые нужно склеить
INCLUDE_EXTENSIONS = {".py", ".html"}

# Файлы и папки, которые нужно игнорировать
IGNORE_ITEMS = {
    ".git",
    "__pycache__",
    ".env",
    "venv",
    "env",
    ".gitignore",
    ".pyc",
    "__pycache__",
    ".DS_Store",
    ".pytest_cache"
}

def should_ignore(name):
    """Проверяет, стоит ли игнорировать файл или папку."""
    return name in IGNORE_ITEMS or name.startswith(".") or name.startswith("__")

def get_project_tree(start_path):
    """Формирует дерево структуры проекта."""
    tree = []

    def recursive_tree(path, prefix=""):
        items = sorted(os.listdir(path))
        for i, item in enumerate(items):
            if should_ignore(item):
                continue
            is_last = i == len([x for x in items if not should_ignore(x)]) - 1
            full_path = os.path.join(path, item)
            rel_path = os.path.relpath(full_path)

            # Добавляем элемент к дереву
            if os.path.isdir(full_path):
                tree.append(f"{prefix}{'└── ' if is_last else '├── '}{item}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                recursive_tree(full_path, new_prefix)
            else:
                tree.append(f"{prefix}{'└── ' if is_last else '├── '}{item}")

    tree.append(os.path.basename(start_path) + "/")
    recursive_tree(start_path)
    return "\n".join(tree)

def merge_files_with_content(start_path, output_file="output.txt"):
    with open(output_file, "w", encoding="utf-8") as out:
        # Пишем заголовок и структуру
        out.write("📁 Структура проекта:\n\n")
        out.write(get_project_tree(start_path))
        out.write("\n\n" + "=" * 80 + "\n\n")

        # Теперь пишем содержимое файлов
        for root, dirs, files in os.walk(start_path):
            # Убираем игнорируемые директории
            dirs[:] = [d for d in dirs if not should_ignore(d)]

            for file in sorted(files):
                if should_ignore(file):
                    continue
                ext = os.path.splitext(file)[1]
                if ext not in INCLUDE_EXTENSIONS:
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    content = f"[Ошибка чтения файла: {e}]"

                relative_path = os.path.relpath(file_path, start_path)
                out.write(f"\n\n📄 Файл: {relative_path}\n")
                out.write("-" * (len(relative_path) + 7) + "\n")
                out.write(content)
                out.write("\n" + "-" * 80)

    print(f"✅ Все файлы успешно объединены в '{output_file}'")

if __name__ == "__main__":
    merge_files_with_content(".")