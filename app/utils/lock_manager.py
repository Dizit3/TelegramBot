import os
import sys
import subprocess
from loguru import logger
# But for a basic bot, a lock file with PID is usually enough if handled carefully.

LOCK_FILE = "bot.lock"

def acquire_lock():
    """Агрессивно завершает все другие процессы этого бота и создает новую блокировку."""
    current_pid = os.getpid()
    
    if os.name == 'nt': # Windows
        try:
            current_pid = os.getpid()
            parent_pid = os.getppid() # Доступно в Python 3.12+ на Windows
            
            # Ищем все процессы python/py, в командной строке которых есть 'main.py'
            # И которые НЕ являются текущим процессом или его родителем
            ps_cmd = (
                f'Get-CimInstance Win32_Process | '
                f'Where-Object {{ ($_.CommandLine -like "*main.py*") -and '
                f'($_.ProcessId -ne {current_pid}) -and ($_.ProcessId -ne {parent_pid}) }} | '
                f'ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}'
            )
            subprocess.run(['powershell', '-Command', ps_cmd], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            
            import time
            time.sleep(2) # Даем ОС время на очистку
            logger.info("Все предыдущие копии бота автоматически завершены.")
        except Exception as e:
            logger.warning(f"Предупреждение при очистке процессов: {e}")
    else: # Unix
        # Для Unix оставляем логику с лок-файлом, так как там это работает надежнее
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, "r") as f:
                    pid = int(f.read().strip())
                if pid != current_pid:
                    os.kill(pid, 9)
                    import time
                    time.sleep(1)
                    print(f"Предыдущий процесс (PID: {pid}) завершен.")
            except:
                pass

    # Записываем PID текущего процесса
    with open(LOCK_FILE, "w") as f:
        f.write(str(current_pid))

def release_lock():
    """Удаляет файл-блокировку при выходе."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
