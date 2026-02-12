import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STATE_FILE = Path("/app/data/state.json")


def get_env_or_exit(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.error(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value


def validate_ipv4(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False
        except ValueError:
            return False
    return True


def load_state() -> Optional[dict]:
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load state file: {e}")
        return None


def save_state(status: str, changed_at: float) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {"status": status, "changed_at": changed_at}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    logger.debug(f"State saved: {state}")


def ping(ip: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except FileNotFoundError:
        logger.error("ping utility not found. Install iputils-ping.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ping failed with exception: {e}")
        return False


def format_duration(seconds: float) -> str:
    total_minutes = int(seconds // 60)
    days = total_minutes // (24 * 60)
    remaining = total_minutes % (24 * 60)
    hours = remaining // 60
    minutes = remaining % 60

    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if days > 0 or hours > 0:
        parts.append(f"{hours}год")
    parts.append(f"{minutes}хв")

    return " ".join(parts)


def send_telegram(token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.warning(f"Telegram API error: {resp.status_code} {resp.text}")
        except requests.RequestException as e:
            logger.warning(f"Telegram request failed (attempt {attempt + 1}): {e}")

        if attempt < max_retries - 1:
            delay = 2 ** (attempt + 1)
            logger.info(f"Retrying in {delay}s...")
            time.sleep(delay)

    logger.error("Failed to send Telegram message after all retries")
    return False


def main():
    token = get_env_or_exit("TELEGRAM_BOT_TOKEN")
    chat_id = get_env_or_exit("TELEGRAM_CHAT_ID")
    target_ip = get_env_or_exit("TARGET_IPV4")

    if not validate_ipv4(target_ip):
        logger.error(f"Invalid IPv4 address: {target_ip}")
        sys.exit(1)

    try:
        interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "180"))
    except ValueError:
        logger.error("CHECK_INTERVAL_SECONDS must be an integer")
        sys.exit(1)

    tz = os.environ.get("TZ", "Europe/Kiev")
    os.environ["TZ"] = tz
    try:
        time.tzset()
    except AttributeError:
        pass

    logger.info(f"Starting ping monitor for {target_ip}")
    logger.info(f"Check interval: {interval}s, Timezone: {tz}")

    state = load_state()
    if state:
        current_status = state["status"]
        changed_at = state["changed_at"]
        logger.info(f"Loaded state: {current_status} since {datetime.fromtimestamp(changed_at)}")
    else:
        current_status = None
        changed_at = None
        logger.info("No previous state found, will initialize on first check")

    while True:
        is_up = ping(target_ip)
        new_status = "UP" if is_up else "DOWN"
        now = time.time()

        if current_status is None:
            current_status = new_status
            changed_at = now
            save_state(current_status, changed_at)
            logger.info(f"Initial state: {current_status}")
        elif new_status != current_status:
            duration = now - changed_at
            duration_str = format_duration(duration)
            time_str = datetime.now().strftime("%H:%M")

            if new_status == "DOWN":
                message = f"{time_str} Світло зникло\nВоно було {duration_str}"
            else:
                message = f"{time_str} Світло з'явилося\nЙого не було {duration_str}"

            logger.info(f"State changed: {current_status} -> {new_status}")
            send_telegram(token, chat_id, message)

            current_status = new_status
            changed_at = now
            save_state(current_status, changed_at)
        else:
            logger.debug(f"No change, status: {current_status}")

        time.sleep(interval)


if __name__ == "__main__":
    main()
