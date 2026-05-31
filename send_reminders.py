import os
import json
import urllib.request
import urllib.parse
from datetime import date, timedelta

SUPABASE_URL = "https://vchafdroyfbkmpnzneoz.supabase.co"
SUPABASE_ANON = os.environ["SUPABASE_ANON"]
ACCESS_CODE = os.environ["ACCESS_CODE"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]


def rpc(fn, payload):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("apikey", SUPABASE_ANON)
    req.add_header("Authorization", f"Bearer {SUPABASE_ANON}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get_chat_ids():
    res = rpc("get_dashboard_data", {"code": ACCESS_CODE})
    # chat ids are stored in app_config; fetch via a tiny helper below
    return res


def fetch_config_value(key):
    url = f"{SUPABASE_URL}/rest/v1/rpc/get_config"
    # fallback handled in main if function missing
    return None


def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        print(f"Sent to {chat_id}")
    except Exception as e:
        print(f"Failed to send to {chat_id}: {e}")


def main():
    due = rpc("get_due_tasks", {"code": ACCESS_CODE})
    if isinstance(due, dict) and due.get("error"):
        print("Auth error talking to database. Check ACCESS_CODE secret.")
        return

    tasks = due.get("tasks", []) if isinstance(due, dict) else []

    today = date.today()
    tomorrow = today + timedelta(days=1)

    today_list, tomorrow_list, overdue_list = [], [], []
    for t in tasks:
        dd = t.get("due_date")
        if not dd:
            continue
        d = date.fromisoformat(dd)
        label = t.get("title", "Untitled")
        if t.get("category") == "hh":
            label = "[HH] " + label
        if d < today:
            overdue_list.append(label)
        elif d == today:
            today_list.append(label)
        elif d == tomorrow:
            tomorrow_list.append(label)

    lines = ["\U0001F514 SCM Dashboard reminder", ""]
    lines.append("Please review and update the dashboard if anything has changed.")
    lines.append("")

    if overdue_list:
        lines.append("Overdue:")
        lines += [f"\u2022 {x}" for x in overdue_list]
        lines.append("")
    if today_list:
        lines.append("Due today:")
        lines += [f"\u2022 {x}" for x in today_list]
        lines.append("")
    if tomorrow_list:
        lines.append("Due tomorrow:")
        lines += [f"\u2022 {x}" for x in tomorrow_list]
        lines.append("")

    if not (overdue_list or today_list or tomorrow_list):
        lines.append("No tasks due today or tomorrow. \U0001F331")

    message = "\n".join(lines).strip()

    chat_ids_raw = os.environ.get("TELEGRAM_CHAT_IDS", "")
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]

    if not chat_ids:
        print("No chat IDs found in TELEGRAM_CHAT_IDS secret.")
        return

    for cid in chat_ids:
        send_telegram(cid, message)


if __name__ == "__main__":
    main()
