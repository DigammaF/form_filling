
import json
import rich
import random
import asyncio
import aiohttp
import requests
import string
import time
import arrow

from pathlib import Path
from markovchain.text import MarkovText
from faker import Faker

CONSOLE = rich.get_console()

CONSOLE.print("""
	[italic purple]Greetings![/italic purple]
	First, make sure to get a proxy list with [green]python regenerate_proxies.py[/green].
	Then go back to this program.
	After some time, all the IPs in the proxy list will be marked by the website as having [red]already submitted the form[/red].
	When this happens, you can regenerate proxies again.
	Please note that the proxy service used by [green]regenerate_proxies.py[/green] is free, so results are not guaranteed.
	Feel free to use your own proxy list, the format is as follow:
	ip:port
	ip:port
	ip:port
	...
	One will be picked at random every time the program tries to submit a form.
	Please note that a program restart is required to update the proxy list.
""")

CONSOLE.rule("Loading addresses")
ADDRESSES = json.load(open("addresses.json"))

CONSOLE.rule("Loading firstnames")
FIRSTNAMES = json.load(open("firstnames.json"))

CONSOLE.rule("Loading lastnames")
LASTNAMES = json.load(open("lastnames.json"))

CONSOLE.rule("Loading markov model")
ARTICLES = Path("articles")
MARKOV = MarkovText()

for file in ARTICLES.iterdir():
	with open(file) as f:
		for line in f:
			MARKOV.data(line, part=True)
	MARKOV.data("", part=False)

CONSOLE.rule("Loading proxies")
PROXIES = []

with open("http_proxies.txt") as f:
	for line in f:
		PROXIES.append(line.strip())

CONSOLE.print(f"Found {len(PROXIES)} proxies")

CONSOLE.rule("Setting details")

URL = r"https://ago.mo.gov/file-a-complaint/transgender-center-concerns?sf_cntrl_id=ctl00%24MainContent%24C001"
USER_AGENT = r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
LOGS = Path("logs")
if not LOGS.exists(): LOGS.mkdir()
CONSOLE.print(f"{URL=}")
CONSOLE.print(f"{LOGS=}")

FAKER = Faker()

def random_address() -> dict:
	return {
		**random.choice(ADDRESSES),
		"nbr": random.randint(1, 40),
		"phone": "314" + "".join(str(random.randint(0,9)) for _ in range(7))
	}

def purify_address(address: dict[str, str]):

	for key in ("street", "city"):
		address[key] = " ".join(w.capitalize() for w in address[key].split(" "))

def random_provider() -> str:
	return random.choice(
		(
			"gmail.com",
			"outlook.com",
			"icloud.com",
			"mac.com",
		)
	)

def make_email(firstname: str, lastname: str) -> str:

	if random.random() > 0.5:
		return f"{firstname.lower()}_{lastname.lower()}@{random_provider()}"

	else:
		return f"{firstname[0].lower()}{lastname.lower()}@{random_provider()}"

def random_identity() -> dict:

	identity = random_address()
	purify_address(identity)
	identity["firstname"] = random.choice(FIRSTNAMES)
	identity["lastname"] = random.choice(LASTNAMES)
	identity["email"] = make_email(identity["firstname"], identity["lastname"])
	return identity

def random_form_id() -> str:
	"""
		ff8b4107-9b52-4f0b-a2ea-cdd472e9093a
	"""
	return "-".join((rfIDp(8), rfIDp(4), rfIDp(4), rfIDp(4), rfIDp(12)))

def rfIDp(length: int) -> str:
	return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

async def post(report_text: str, identity: dict, proxy: str) -> str:

	args = {
		"FormId": random_form_id(),
		"TextFieldController_4": identity["firstname"],
		"TextFieldController_5": identity["lastname"],
		"TextFieldController_1": str(identity["nbr"]) + " " + identity["street"],
		"TextFieldController_2": identity["city"],
		"DropdownListFieldController": "MO",
		"TextFieldController_6": identity["postcode"],
		"TextFieldController_0": identity["email"],
		"TextFieldController_3": identity["phone"],
		"ParagraphTextFieldController": report_text,
	}
	headers = {
		#"Content-Type": "application/json",
		"User-Agent": FAKER.user_agent(),
		#"X-Forwarded-For": FAKER.ipv4(),
		# suggested by https://www.reddit.com/user/forgetful_egg/
		# but it doesn't seem to work here(?)
		"Cookie": ""
	}
	proxy_url=f"http://{proxy}"
	async with aiohttp.ClientSession() as session:
		async with session.post(URL, data=args, timeout=5, proxy=proxy_url, headers=headers) as req:
			return await req.text()

async def wrapped_post(report_text: str, identity: dict, proxy: str):
	try:
		return await post(report_text, identity, proxy)
	except:
		return None

async def auto_post(text, identity) -> str:

	proxy = random.choice(PROXIES)

	try:
		return await post(text, identity, proxy)
	except Exception as e:
		return await auto_post(text, identity)

async def proxy_post_job(proxy: str):
	identity = random_identity()
	text = " ".join((MARKOV() for _ in range(20)))
	res = await wrapped_post(text, identity, proxy)
	if res is None: return
	if "You have already submitted this form." in res:
		CONSOLE.print(f"|{arrow.utcnow()}| posted form")
		CONSOLE.print(f"[red]{proxy=} Form already submitted[/red]")
	if "Success! Thanks for filling out our form!" in res:
		CONSOLE.print(f"|{arrow.utcnow()}| posted form")
		CONSOLE.print(f"[green]{proxy=} Success[/green]")
		with open(LOGS / f"{int(time.time()*100)}.html", "w") as f:
			f.write("IDENTITY\n")
			f.write(str(identity) + "\n")
			f.write("TEXT\n")
			f.write(text + "\n")
			f.write(res)

async def post_job():
	identity = random_identity()
	text = " ".join((MARKOV() for _ in range(20)))
	res = await auto_post(text, identity)
	if "You have already submitted this form." in res:
		CONSOLE.print(f"|{arrow.utcnow()}| posted form")
		CONSOLE.print("[red]Form already submitted[/red]")
	if "Success! Thanks for filling out our form!" in res:
		CONSOLE.print(f"|{arrow.utcnow()}| posted form")
		CONSOLE.print("[green]Success[/green]")
		with open(LOGS / f"{int(time.time()*100)}.html", "w") as f:
			f.write("IDENTITY\n")
			f.write(str(identity) + "\n")
			f.write("TEXT\n")
			f.write(text + "\n")
			f.write(res)

async def post_loop():

	while True:
		await post_job()

async def main():
	CONSOLE.rule("Let's go!")
	await asyncio.gather(*(post_loop() for _ in range(50)))

async def proxy_set_main():
	CONSOLE.rule("Let's go!")
	await asyncio.gather(*(proxy_post_job(proxy) for proxy in PROXIES))

if __name__ == "__main__":
	asyncio.run(main())
