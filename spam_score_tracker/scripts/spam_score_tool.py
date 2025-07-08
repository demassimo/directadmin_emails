#!/usr/bin/env python3
import re, os, glob, gzip, argparse
from datetime import datetime, timedelta
import mysql.connector

# ———— CONFIGURE ME ————
DB_CONFIG = {
    'host':     '127.0.0.1',
    'user':     'your_db_user',
    'password': 'your_db_pass',
    'database': 'mail_logs',
}
LOG_GLOB = "/var/log/mail.log*"
TIMEZONE = None  # if you need to localize; otherwise leave None
# ————————————————————

LINE_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}).*spamd: result: [NY]\s+"
    r"(?P<score>[\d.]+)/\d+\.\d+.*mid=<(?P<mid>[^>]+)>"
)

def connect_db():
    return mysql.connector.connect(**DB_CONFIG)

def parse_ts(ts_str, year=None):
    # e.g. "Jul  8 10:56:44"
    dt = datetime.strptime(ts_str, "%b %d %H:%M:%S")
    return dt.replace(year=year or datetime.now().year)

def iterate_logs():
    """Yield (ts:datetime, score:float, mid:str) from all log files."""
    for fn in sorted(glob.glob(LOG_GLOB)):
        opener = gzip.open if fn.endswith(".gz") else open
        try:
            with opener(fn, "rt", errors="ignore") as f:
                for line in f:
                    m = LINE_RE.match(line)
                    if not m:
                        continue
                    ts = parse_ts(m.group("ts"))
                    score = float(m.group("score"))
                    mid   = m.group("mid")
                    yield ts, score, mid
        except FileNotFoundError:
            continue

def backfill():
    cnx = connect_db()
    cur = cnx.cursor()
    seen = set()
    for ts, score, mid in iterate_logs():
        key = (mid, ts)
        if key in seen:
            continue
        seen.add(key)
        # check before insert
        cur.execute(
            "SELECT 1 FROM spam_scores WHERE message_id=%s AND ts=%s",
            (mid, ts)
        )
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO spam_scores (ts, score, message_id) VALUES (%s,%s,%s)",
            (ts, score, mid)
        )
        cnx.commit()
        print(f"[+] backfilled {ts} {score:.2f} {mid}")
    cur.close()
    cnx.close()

def query(mid, time_str, tol_minutes=1):
    # parse the user-provided time; support "YYYY/mmdd HH:MM" or "YYYY/MM/DD HH:MM"
    for fmt in ("%Y/%m%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(time_str, fmt)
            break
        except ValueError:
            dt = None
    if not dt:
        raise SystemExit("❌ time format must be e.g. 2025/0708 10:56 or 2025/07/08 10:56")
    cnx = connect_db()
    cur = cnx.cursor()
    # 1) try DB
    cur.execute(
        "SELECT ts, score FROM spam_scores "
        "WHERE message_id=%s AND ts BETWEEN %s AND %s",
        (mid, dt - timedelta(minutes=tol_minutes), dt + timedelta(minutes=tol_minutes))
    )
    row = cur.fetchone()
    if row:
        print(f"✅ Found in DB: {row[0]} → score={row[1]:.2f}")
        return

    # 2) scan logs
    for ts, score, m2 in iterate_logs():
        if m2 == mid and abs((ts - dt).total_seconds()) <= tol_minutes * 60:
            print(f"🔍 Found in logs: {ts} → score={score:.2f}; inserting into DB")
            cur.execute(
                "INSERT INTO spam_scores (ts, score, message_id) VALUES (%s,%s,%s)",
                (ts, score, mid)
            )
            cnx.commit()
            cur.close()
            cnx.close()
            return

    print("⚠️  Not found within ±1 min in logs or DB.")
    cur.close()
    cnx.close()

def main():
    p = argparse.ArgumentParser(prog="spam_score_tool.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query", help="Look up one message-ID + timestamp")
    q.add_argument("--mid",   required=True, help="Full Message-ID, no <>")
    q.add_argument("--time",  required=True,
                   help="YYYY/mmdd HH:MM or YYYY/MM/DD HH:MM")
    b = sub.add_parser("backfill", help="Scan all existing logs and populate DB")
    args = p.parse_args()

    if args.cmd == "backfill":
        backfill()
    elif args.cmd == "query":
        query(args.mid, args.time)
    else:
        p.print_help()

if __name__ == "__main__":
    main()


# 1) Backfill once on first install:
#spam_score_tool.py backfill

# 2) On-demand lookup by message-ID + time:
#spam_score_tool.py query \
#  --mid "CAMyS0vHooAGpXc5MrN=kmVXXSvtZ-d=3HZYSR80taqPtwNOnGQ@mail.gmail.com" \
#  --time "2025/07/08 10:56"
