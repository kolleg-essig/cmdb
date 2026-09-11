"""
Gunicorn-Konfiguration für den Produktivbetrieb.

Start:
    gunicorn -c gunicorn.conf.py "app:create_app()"
"""

# Bind-Adresse: alle Interfaces, Port 80
bind = "0.0.0.0:80"

# Anzahl Worker-Processes (Faustformel: 2 * CPU-Kerne + 1; hier konservativ 4)
workers = 4

# Worker-Typ: sync ist der robuste Standard für Flask
worker_class = "sync"

# Timeout in Sekunden – Requests, die länger dauern, werden abgetötet
timeout = 120

# Graceful-Shutdown: Worker dürfen bis zu 30 s offene Requests beenden
graceful_timeout = 30

# Maximale Anzahl gleichzeitiger Requests pro Worker
worker_connections = 1000

# Logs in die Konsole (in Produktion besser an ein Log-System leiten)
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Prozessname in ps/top
proc_name = "asset_manager"

# Python-Pfad, damit die App überall importiert werden kann
pythonpath = "."
