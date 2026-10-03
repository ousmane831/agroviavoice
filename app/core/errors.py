"""
Erreurs de l'application et format JSON des réponses d'erreur.

Toutes les erreurs renvoyées par l'API ont la même forme
(Django lit ces clés, il ne faut pas les traduire) :
    {"success": false, "error": "CODE", "message": "Texte lisible"}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErreurApp(Exception):
    """Erreur "prévue" que les services peuvent lever."""

    def __init__(self, code: str, message: str, code_http: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.code_http = code_http


def reponse_erreur(code: str, message: str, code_http: int) -> JSONResponse:
    return JSONResponse(
        status_code=code_http,
        content={"success": False, "error": code, "message": message},
    )


async def gerer_erreur_app(request: Request, erreur: ErreurApp) -> JSONResponse:
    return reponse_erreur(erreur.code, erreur.message, erreur.code_http)


async def gerer_erreur_validation(request: Request, erreur: RequestValidationError) -> JSONResponse:
    # On ne renvoie que le premier problème : plus lisible pour l'utilisateur.
    premier_probleme = erreur.errors()[0]
    champ = premier_probleme["loc"][-1]
    message = premier_probleme["msg"].removeprefix("Value error, ")
    return reponse_erreur("VALIDATION_ERROR", f"{champ} : {message}", 422)


def enregistrer_gestionnaires_erreurs(app: FastAPI) -> None:
    app.add_exception_handler(ErreurApp, gerer_erreur_app)
    app.add_exception_handler(RequestValidationError, gerer_erreur_validation)
