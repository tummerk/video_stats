from curl_cffi import requests

# Используйте socks5h для удаленного резолва DNS
proxy = "socks5h://Zt6cYt1A:9Pktk5xm@193.135.117.21:10000"

try:
    # Имитируем Chrome 110, это критически важно для прохода через WAF Instagram
    r = requests.get(
        "https://www.instagram.com/accounts/login/",
        proxies={"http": proxy, "https": proxy},
        impersonate="chrome110",
        timeout=30
    )
    print(f"Статус: {r.status_code}")
    print("Успех! TLS-отпечаток прошел проверку.")
except Exception as e:
    print(f"Ошибка: {e}")
    print("Если виснет здесь — значит проблема в MTU или жестком DPI провайдера.")