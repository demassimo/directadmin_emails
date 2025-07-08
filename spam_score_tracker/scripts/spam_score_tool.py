#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import glob
import gzip
import argparse
import time
import sys
from datetime import datetime, timedelta
import mysql.connector

# -- CONFIGURE ME ------------------------------------------------------------
DB_CONFIG = {
    'host':     '127.0.0.1',
    'user':     'mail_logs',
    'password': 'l59X8bHfO07FIBWY08Z98',
    'database': 'mail_logs',
    'charset':  'utf8mb4',
}
LOG_FILES = ["/var/log/exim/mainlog", "/var/log/mail.log"]
TIMEZONE = None  # if you need to localize; otherwise leave None
# ------------------------------------------------------------------------------

# regexes converted from the PHP parser
RECEIVED_RE    = re.compile(r'^(?P<ts>\S+\s+\S+)\s+(?P<id>\S+)\s+<=\s+(?P<from>\S+).*\[(?P<ip>[^\]]+)\]')
SUBJECT_RE     = re.compile(r'T="([^"]*)"')
MSGID_RE       = re.compile(r'id=([^\s]+)')
SIZE_RE        = re.compile(r'S=(\d+)')
RCPT_RE        = re.compile(r'^(?P<ts>\S+\s+\S+)\s+(?P<id>\S+)\s+=>\s+(?P<to>\S+)')
COMPL_RE       = re.compile(r'^(?P<ts>\S+\s+\S+)\s+(?P<id>\S+)\s+Completed')
REJ_RE         = re.compile(r'^(?P<ts>\S+\s+\S+)\s+(?P<id>\S+).*rejected', re.I)
SPAMCHECK_RE   = re.compile(
    r'^(?P<ts>\S+\s+\S+)\s+(?P<id>\S+)\s+.*spamcheck.*score=([\d\.\-]+)(?:.*tests=([A-Za-z0-9_,-]+))?',
    re.I
)
SPAMD_MID_RE   = re.compile(
    r'^(?P<ts>\w{3}\s+\d+\s+\d+:\d+:\d+).*spamd: result:.*?\s(-?[\d\.]+)\s-\s*([A-Za-z0-9_,-]+).*mid=<([^>]+)>',
    re.I
)
SPAMD_RE       = re.compile(
    r'^(?P<ts>\w{3}\s+\d+\s+\d+:\d+:\d+).*spamd: result:.*?\s(-?[\d\.]+)\s-\s*([A-Za-z0-9_,-]+)',
    re.I
)


def connect_db():
    return mysql.connector.connect(**DB_CONFIG)


def parse_ts(ts_str, year=None):
    """
    Parse either:
      - ISO timestamps: "2025-07-06 00:43:18"
      - Exim-style timestamps: "Jul  8 10:56:37"
    Returns a datetime.
    """
    for fmt in ("%Y-%m-%d %H:%M:%S", "%b %d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            if fmt == "%b %d %H:%M:%S":
                # Exim logs don't include year
                dt = dt.replace(year=year or datetime.now().year)
            return dt
        except ValueError:
            continue
    raise ValueError(f"unrecognized timestamp format: {ts_str!r}")


def safe_float(s):
    """Return float(s) or None if it can't be parsed."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_logs(files):
    messages = {}
    mid_map = {}
    pending = {}
    current_id = None

    # expand globs, sort to read in chronological order
    filenames = sorted(sum([glob.glob(f + "*") for f in files], []))

    for fn in filenames:
        opener = gzip.open if fn.endswith('.gz') else open
        try:
            with opener(fn, 'rt', errors='ignore') as f:
                for line in f:
                    # -- RECEIVED
                    m = RECEIVED_RE.search(line)
                    if m:
                        id_ = m.group('id')
                        current_id = id_
                        msg = messages.setdefault(id_, {'to': []})
                        msg['time'] = parse_ts(m.group('ts'))
                        msg['from'] = m.group('from')
                        msg['ip'] = m.group('ip')

                        s = SUBJECT_RE.search(line)
                        if s:
                            msg['subject'] = s.group(1)

                        mi = MSGID_RE.search(line)
                        if mi:
                            msgid = mi.group(1)
                            msg['msgid'] = msgid
                            mid_map[msgid] = id_
                            if msgid in pending:
                                for sa in pending[msgid]:
                                    msg['time']  = msg.get('time') or parse_ts(sa['time'])
                                    msg['score'] = safe_float(sa['score'])
                                    msg['tests'] = sa['tests']
                                del pending[msgid]

                        sz = SIZE_RE.search(line)
                        if sz:
                            msg['size'] = sz.group(1)
                        continue

                    # -- RCPT
                    m = RCPT_RE.search(line)
                    if m:
                        id_ = m.group('id')
                        current_id = id_
                        msg = messages.setdefault(id_, {'to': []})
                        msg.setdefault('to', []).append(m.group('to'))
                        continue

                    # -- COMPLETED
                    m = COMPL_RE.search(line)
                    if m:
                        id_ = m.group('id')
                        current_id = id_
                        msg = messages.setdefault(id_, {'to': []})
                        msg.setdefault('action', 'delivered')
                        continue

                    # -- REJECTED
                    m = REJ_RE.search(line)
                    if m:
                        id_ = m.group('id')
                        current_id = id_
                        msg = messages.setdefault(id_, {'to': []})
                        msg['action'] = 'rejected'
                        continue

                    # -- SPAMCHECK
                    m = SPAMCHECK_RE.search(line)
                    if m:
                        id_     = m.group('id')
                        current_id = id_
                        msg     = messages.setdefault(id_, {'to': []})
                        msg['time'] = msg.get('time') or parse_ts(m.group('ts'))
                        score    = safe_float(m.group(3))
                        if score is not None:
                            msg['score'] = score
                        tests = m.group(4)
                        if tests:
                            msg['tests'] = tests
                        msg['spamline'] = line.strip()
                        continue

                    # -- SPAMD with explicit mid
                    m = SPAMD_MID_RE.search(line)
                    if m:
                        mid    = m.group(4)
                        info   = {'time': m.group('ts'), 'score': m.group(2), 'tests': m.group(3)}
                        score  = safe_float(m.group(2))
                        if mid in mid_map:
                            id_ = mid_map[mid]
                            msg = messages.setdefault(id_, {'to': []})
                            msg['time']  = msg.get('time') or parse_ts(m.group('ts'))
                            if score is not None:
                                msg['score'] = score
                            msg['tests'] = m.group(3)
                            msg['spamline'] = line.strip()
                        elif current_id:
                            id_ = current_id
                            msg = messages.setdefault(id_, {'to': []})
                            msg['time']  = msg.get('time') or parse_ts(m.group('ts'))
                            if score is not None:
                                msg['score'] = score
                            msg['tests'] = m.group(3)
                            msg['spamline'] = line.strip()
                        else:
                            pending.setdefault(mid, []).append(info)
                        continue

                    # -- fallback SPAMD
                    m = SPAMD_RE.search(line)
                    if m and current_id:
                        id_ = current_id
                        msg = messages.setdefault(id_, {'to': []})
                        msg['time']  = msg.get('time') or parse_ts(m.group('ts'))
                        score = safe_float(m.group(2))
                        if score is not None:
                            msg['score'] = score
                        msg['tests']   = m.group(3)
                        msg['spamline'] = line.strip()
                        continue

        except FileNotFoundError:
            continue

    return messages


def generate_entries():
    msgs = parse_logs(LOG_FILES)
    for msg in msgs.values():
        if 'score' in msg and 'msgid' in msg:
            yield {
                'ts':         msg['time'],
                'score':      msg['score'],
                'message_id': msg['msgid'],
                'sender':     msg.get('from'),
                'recipients': ','.join(msg.get('to', [])),
                'subject':    msg.get('subject'),
            }


def backfill():
    cnx = connect_db()
    cur = cnx.cursor()
    for entry in generate_entries():
        cur.execute(
            "SELECT 1 FROM spam_scores WHERE message_id=%s AND ts=%s",
            (entry['message_id'], entry['ts'])
        )
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO spam_scores (ts, score, message_id, sender, recipients, subject)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            (entry['ts'], entry['score'], entry['message_id'],
             entry['sender'], entry['recipients'], entry['subject'])
        )
        cnx.commit()
        print(f"[+] backfilled {entry['ts']} {entry['score']:.2f} {entry['message_id']}")
    cur.close()
    cnx.close()


def query(mid, time_str, tol_minutes=1):
    # allow two date formats for backward compatibility
    for fmt in ("%Y/%m%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(time_str, fmt)
            break
        except ValueError:
            dt = None
    if not dt:
        raise SystemExit("ERROR: time format must be e.g. 2025/0708 10:56 or 2025/07/08 10:56")

    cnx = connect_db()
    cur = cnx.cursor()
    cur.execute(
        "SELECT ts, score, sender, recipients, subject FROM spam_scores "
        "WHERE message_id=%s AND ts BETWEEN %s AND %s",
        (mid, dt - timedelta(minutes=tol_minutes), dt + timedelta(minutes=tol_minutes))
    )
    row = cur.fetchone()
    if row:
        print(f"Found in DB: {row[0]} -> score={row[1]:.2f}")
        cur.close(); cnx.close()
        return

    for entry in generate_entries():
        if entry['message_id'] == mid and abs((entry['ts'] - dt).total_seconds()) <= tol_minutes * 60:
            print(f"Found in logs: {entry['ts']} -> score={entry['score']:.2f}; inserting into DB")
            cur.execute(
                "INSERT INTO spam_scores (ts, score, message_id, sender, recipients, subject)"
                " VALUES (%s,%s,%s,%s,%s,%s)",
                (entry['ts'], entry['score'], entry['message_id'],
                 entry['sender'], entry['recipients'], entry['subject'])
            )
            cnx.commit()
            cur.close(); cnx.close()
            return

    print("WARNING: Not found within +-1 min in logs or DB.")
    cur.close(); cnx.close()


def follow(interval=60):
    while True:
        backfill()
        time.sleep(interval)


def main():
    p = argparse.ArgumentParser(prog="spam_score_tool.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query", help="Look up one message-ID + timestamp")
    q.add_argument("--mid",  required=True, help="Full Message-ID, no <>")
    q.add_argument("--time", required=True, help="YYYY/mmdd HH:MM or YYYY/MM/DD HH:MM")
    sub.add_parser("backfill", help="Scan all existing logs and populate DB")
    sub.add_parser("follow",   help="Continuously update DB from logs")
    args = p.parse_args()

    if args.cmd == "backfill":
        backfill()
    elif args.cmd == "query":
        query(args.mid, args.time)
    elif args.cmd == "follow":
        follow()
    else:
        p.print_help()


if __name__ == "__main__":
    main()
