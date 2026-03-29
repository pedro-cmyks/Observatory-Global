import requests
resp = requests.get("http://localhost:8000/api/v2/nodes?range=3m")
print(resp.status_code)
print(resp.text)
