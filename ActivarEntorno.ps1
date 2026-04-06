Set-Location "~\UltraPresetGaming\backend"
.\venv\Scripts\Activate.ps1

python api/crawler.py

python manage.py runserver

