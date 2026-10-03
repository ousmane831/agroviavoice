"""
Lance le serveur : python run.py
(équivalent à : uvicorn app.main:app --reload)
"""

import uvicorn

from app.core.config import reglages

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=reglages.hote,
        port=reglages.port,
        reload=reglages.environnement == "development",
    )
