import sys
from PyInstaller.__main__ import run

if __name__ == '__main__':
    opts = [
        'main.py',                                            # основной файл
        '--name=Календарь',                                   # имя exe файла
        '--icon=icon.ico',                                    # иконка для exe
        '--windowed',                                         # без консоли
        '--onefile',                                          # один exe файл
        '--add-data=icon.ico;.',                              # добавить иконку в корень сборки
        '--hidden-import=sqlite3',                            # поддержка SQLite
        '--clean',                                            # очистка временных файлов
        '--noconfirm',                                        # автоматическое подтверждение
    ]
    
    # Автоматическая замена разделителя для Linux/Mac (на Windows не меняем)
    if sys.platform != 'win32':
        for i, opt in enumerate(opts):
            if ';' in opt:
                opts[i] = opt.replace(';', ':')
    
    run(opts)
