
import requests

ans = requests.get(
	r"https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
)

if ans.status_code == 200:
	with open("http_proxies.txt", "w") as f:
		f.write("\n".join(line.strip() for line in ans.text.split("\n") if line.strip()))
