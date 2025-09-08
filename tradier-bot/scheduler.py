import subprocess, time, datetime as dt
import zoneinfo
from common.settings import SETTINGS


tz = zoneinfo.ZoneInfo(SETTINGS.timezone)


def hhmm_now() -> str:
	n = dt.datetime.now(tz)
	return f"{n.hour:02d}{n.minute:02d}"


def should_run(now_hhmm: str) -> bool:
	return SETTINGS.open_hhmm <= now_hhmm < SETTINGS.close_hhmm


def main():
	print("scheduler: starting")
	while True:
		nh = hhmm_now()
		if should_run(nh):
			print("scheduler: launching live executor")
			p = subprocess.Popen(["python", "bot/executor.py"])  # inherit env
			while True:
				time.sleep(30)
				nh = hhmm_now()
				if not should_run(nh):
					p.terminate()
					try:
						p.wait(timeout=10)
					except Exception:
						p.kill()
					print("scheduler: stopped for close")
					break
		else:
			time.sleep(15)


if __name__ == "__main__":
	main()