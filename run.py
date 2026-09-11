"""
Startet die Flask-App mit dem eingebauten Entwicklungsserver.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
