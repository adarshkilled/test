import requests
import json

bot_token = '7570184245:AAE7OWZlAgr933j660Asx2GIHPTa6stftEs'
chat_id = '668694490'
group_chat_id = '-1002558840727'

message = '✅ Live test successful! Message sent from Python 🐍'

url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
updateurl = f'https://api.telegram.org/bot{bot_token}/getUpdates'

payload = {
    'chat_id': group_chat_id,
    'text': message
}
response = requests.get(updateurl)
data = response.json()

# Pretty print the response
print(json.dumps(data, indent=2))
res = requests.post(url, data=payload)
print(res.status_code)
print(res.text)