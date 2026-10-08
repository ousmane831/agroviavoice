import requests

url = "http://127.0.0.1:8001/api/v1/agriculture/respond"

data = {
    "question": "ñaata kilogramme laay jaay ci sama parcelles",
    "language": "wolof",
    "agricultural_context": '{"ventes":{"vendu_total_kg":10474.0}}',
}

print("Envoi de la requête...")

response = requests.post(
    url,
    data=data,
    timeout=30,
)

print("STATUS :", response.status_code)
print("REPONSE :", response.text)