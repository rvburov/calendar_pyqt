import os
import sys
from pathlib import Path

def get_folder_structure(directory, exclude_dirs=None):
    """
    Рекурсивно строит структуру папок и файлов, исключая указанные директории
    Возвращает строку с древовидной структурой
    """
    if exclude_dirs is None:
        exclude_dirs = ['venv', '__pycache__', '.git', 'node_modules', '.idea', '.vscode']
    
    directory = Path(directory)
    structure = []
    
    def build_tree(current_path, prefix=""):
        items = []
        try:
            for item in sorted(current_path.iterdir()):
                # Пропускаем исключенные директории
                if item.is_dir() and item.name in exclude_dirs:
                    continue
                # Пропускаем скрытые файлы/папки (опционально)
                if item.name.startswith('.'):
                    continue
                items.append(item)
        except PermissionError:
            return
        
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            structure.append(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir():
                extension = "    " if is_last else "│   "
                build_tree(item, prefix + extension)
    
    structure.append(directory.name)
    build_tree(directory)
    return "\n".join(structure)

def collect_py_files(directory, exclude_dirs=None):
    """
    Рекурсивно собирает все .py файлы, исключая __init__.py и исключенные директории
    Возвращает список путей относительно корневой директории
    """
    if exclude_dirs is None:
        exclude_dirs = ['venv', '__pycache__', '.git', 'node_modules', '.idea', '.vscode']
    
    py_files = []
    directory = Path(directory)
    
    for root, dirs, files in os.walk(directory):
        # Модифицируем dirs на месте, чтобы os.walk не заходил в исключенные папки
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                full_path = Path(root) / file
                relative_path = full_path.relative_to(directory)
                py_files.append(relative_path)
    
    return sorted(py_files, key=lambda p: str(p))

def read_file_content(file_path):
    """
    Читает содержимое файла, обрабатывая возможные ошибки кодировки
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='cp1251') as f:
                return f.read()
        except:
            return f"# [Ошибка: не удалось прочитать файл]"
    except Exception as e:
        return f"# [Ошибка: {str(e)}]"

def generate_output(project_dir, output_file='project_export.txt'):
    """
    Генерирует выходной .txt файл со структурой проекта и всеми .py файлами (кроме __init__.py)
    """
    project_path = Path(project_dir)
    
    if not project_path.exists():
        print(f"Ошибка: Директория '{project_dir}' не существует!")
        return False
    
    # Получаем структуру проекта
    print("Формируем структуру проекта...")
    structure = get_folder_structure(project_path)
    
    # Собираем все .py файлы
    print("Собираем .py файлы...")
    py_files = collect_py_files(project_path)
    
    if not py_files:
        print("Не найдено .py файлов (исключая __init__.py)")
        return False
    
    # Записываем в выходной файл
    with open(output_file, 'w', encoding='utf-8') as out:
        # Записываем заголовок и структуру
        out.write("Структура проекта\n")
        out.write("=" * 50 + "\n")
        out.write(structure)
        out.write("\n\n")
        out.write("=" * 50 + "\n")
        out.write("Содержимое файлов\n")
        out.write("=" * 50 + "\n\n")
        
        # Записываем содержимое каждого файла
        for rel_path in py_files:
            full_path = project_path / rel_path
            
            # Записываем путь к файлу
            out.write(f"{rel_path}\n")
            
            # Записываем содержимое файла
            content = read_file_content(full_path)
            out.write(content)
            
            # Добавляем пустую строку между файлами
            if not content.endswith('\n'):
                out.write('\n')
            out.write('\n')
    
    print(f"Готово! Создан файл '{output_file}'")
    print(f"Обработано файлов: {len(py_files)}")
    print(f"Исключены папки: venv, __pycache__, .git и др.")
    return True

def main():
    # Если передан аргумент командной строки - используем его как путь к проекту
    # Иначе используем текущую директорию
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = os.getcwd()
    
    print(f"Сканируем директорию: {project_dir}")
    generate_output(project_dir)

if __name__ == "__main__":
    main()