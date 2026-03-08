#!/usr/bin/env python3
"""
Sinh dataset SSH log đa dạng cho training/demo: thời gian trải nhiều ngày/giờ,
nhiều loại normal (password, publickey, session), nhiều IP/user tấn công.
Xuất CSV raw cùng format data/raw/logs.csv để chạy preprocess -> train.
"""

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Cấu hình mặc định
DEFAULT_DAYS = 14
DEFAULT_NORMAL_RATIO = 0.85
DEFAULT_TOTAL = 8000
ATTACK_USERS = ["admin", "root", "ubuntu", "oracle", "test", "postgres", "git", "www-data", "mysql", "guest"]
NORMAL_USERS = ["user1", "user2", "deploy", "git", "www-data", "backup", "jenkins", "runner"]
ATTACK_IPS = ["10.10.10.10", "10.10.10.11", "172.16.0.5", "172.16.0.6", "192.168.2.100", "192.168.2.101", "203.0.113.10", "198.51.100.20"]
NORMAL_IP_PREFIXES = ["192.168.1.", "10.0.1.", "192.168.10."]


def _syslog_msg(ts: datetime, host: str, proc: str, msg: str) -> str:
    """Tạo phần message dạng syslog: 'Jan 19 10:00:01 localhost sshd[1001]: ...'"""
    tstr = ts.strftime("%b %d %H:%M:%S")
    return f"{tstr} {host} {proc}: {msg}"


def gen_accepted_password(ts: datetime, user: str, ip: str, pid: int) -> tuple:
    msg = f"Accepted password for {user} from {ip} port 22 ssh2"
    full = _syslog_msg(ts, "localhost", f"sshd[{pid}]", msg)
    return full, "accepted", "", False


def gen_accepted_publickey(ts: datetime, user: str, ip: str, pid: int) -> tuple:
    msg = f"Accepted publickey for {user} from {ip} port 22 ssh2"
    full = _syslog_msg(ts, "localhost", f"sshd[{pid}]", msg)
    return full, "accepted", "", False


def gen_session_opened(ts: datetime, user: str, pid: int) -> tuple:
    msg = f"pam_unix(sshd:session): session opened for user {user}"
    full = _syslog_msg(ts, "localhost", f"sshd[{pid}]", msg)
    return full, "session", "", False


def gen_session_closed(ts: datetime, user: str, pid: int) -> tuple:
    msg = f"pam_unix(sshd:session): session closed for user {user}"
    full = _syslog_msg(ts, "localhost", f"sshd[{pid}]", msg)
    return full, "session", "", False


def gen_failed_invalid_user(ts: datetime, user: str, ip: str, pid: int) -> tuple:
    msg = f"Failed password for invalid user {user} from {ip} port 22 ssh2"
    full = _syslog_msg(ts, "localhost", f"sshd[{pid}]", msg)
    return full, "failed", "brute_force", True


def gen_failed_password(ts: datetime, user: str, ip: str, pid: int) -> tuple:
    """Failed password (user có thật, brute force)."""
    msg = f"Failed password for {user} from {ip} port 22 ssh2"
    full = _syslog_msg(ts, "localhost", f"sshd[{pid}]", msg)
    return full, "failed", "brute_force", True


def generate_rows(total: int, normal_ratio: float, days: int, seed: int) -> list:
    random.seed(seed)
    n_normal = int(total * normal_ratio)
    n_attack = total - n_normal

    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
    end = base + timedelta(days=days)
    rows = []

    def random_ts():
        delta = (end - base).total_seconds()
        return base + timedelta(seconds=random.uniform(0, delta))

    pid_counter = [1000]

    def next_pid():
        pid_counter[0] += 1
        return pid_counter[0]

    # ---- Normal ----
    # ~70% Accepted password, ~15% publickey, ~10% session opened/closed, ~5% 1-2 failed rồi accepted
    normal_types = [
        ("accepted_password", 0.70),
        ("publickey", 0.15),
        ("session_opened", 0.05),
        ("session_closed", 0.05),
        ("normal_failed_then_ok", 0.05),
    ]
    for _ in range(n_normal):
        r = random.random()
        acc = 0
        chosen = "accepted_password"
        for name, p in normal_types:
            acc += p
            if r <= acc:
                chosen = name
                break

        ts = random_ts()
        pid = next_pid()
        user = random.choice(NORMAL_USERS) if chosen != "accepted_password" else f"user{random.randint(1, 200)}"
        ip = random.choice(NORMAL_IP_PREFIXES) + str(random.randint(1, 254))

        if chosen == "accepted_password":
            full, status, attack_type, is_attack = gen_accepted_password(ts, user, ip, pid)
        elif chosen == "publickey":
            full, status, attack_type, is_attack = gen_accepted_publickey(ts, user, ip, pid)
        elif chosen == "session_opened":
            full, status, attack_type, is_attack = gen_session_opened(ts, user, pid)
        elif chosen == "session_closed":
            full, status, attack_type, is_attack = gen_session_closed(ts, user, pid)
        else:
            # 1 failed rồi 1 accepted từ cùng IP (normal - user gõ sai)
            ip = random.choice(NORMAL_IP_PREFIXES) + str(random.randint(1, 254))
            user = f"user{random.randint(1, 50)}"
            full1, _, _, _ = gen_failed_password(ts, user, ip, pid)
            ts2 = ts + timedelta(seconds=random.randint(5, 60))
            full2, _, _, _ = gen_accepted_password(ts2, user, ip, next_pid())
            rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": ip,
                "user": user,
                "status": "failed",
                "message": full1,
                "attack_type": "",
                "is_attack": False,
                "geoip_country": "",
                "geoip_city": "",
                "log_type": "ssh",
            })
            rows.append({
                "timestamp": ts2.strftime("%Y-%m-%d %H:%M:%S"),
                "source_ip": ip,
                "user": user,
                "status": "accepted",
                "message": full2,
                "attack_type": "",
                "is_attack": False,
                "geoip_country": "",
                "geoip_city": "",
                "log_type": "ssh",
            })
            continue

        rows.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "source_ip": ip,
            "user": user,
            "status": status,
            "message": full,
            "attack_type": attack_type,
            "is_attack": is_attack,
            "geoip_country": "",
            "geoip_city": "",
            "log_type": "ssh",
        })

    # ---- Attack: nhiều IP, nhiều user ----
    for _ in range(n_attack):
        ts = random_ts()
        pid = next_pid()
        ip = random.choice(ATTACK_IPS)
        user = random.choice(ATTACK_USERS)
        if random.random() < 0.7:
            full, status, attack_type, is_attack = gen_failed_invalid_user(ts, user, ip, pid)
        else:
            full, status, attack_type, is_attack = gen_failed_password(ts, user, ip, pid)
        rows.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "source_ip": ip,
            "user": user,
            "status": status,
            "message": full,
            "attack_type": attack_type,
            "is_attack": is_attack,
            "geoip_country": "",
            "geoip_city": "",
            "log_type": "ssh",
        })

    # Sắp xếp theo thời gian
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Sinh dataset SSH log đa dạng (raw CSV) cho ELKShield."
    )
    parser.add_argument("--output", "-o", default=None,
                        help="File CSV đầu ra (mặc định: data/raw/logs_synthetic.csv)")
    parser.add_argument("--total", "-n", type=int, default=DEFAULT_TOTAL,
                        help=f"Số dòng log tổng (mặc định: {DEFAULT_TOTAL})")
    parser.add_argument("--normal-ratio", type=float, default=DEFAULT_NORMAL_RATIO,
                        help=f"Tỷ lệ normal 0-1 (mặc định: {DEFAULT_NORMAL_RATIO})")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"Số ngày trải dữ liệu (mặc định: {DEFAULT_DAYS})")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--replace-logs", action="store_true",
                        help="Ghi đè data/raw/logs.csv (dùng làm dataset chính)")
    args = parser.parse_args()

    out = args.output
    if not out:
        out = PROJECT_ROOT / "data" / "raw" / "logs_synthetic.csv"
    else:
        out = Path(out)
        if not out.is_absolute():
            out = PROJECT_ROOT / out

    out.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_rows(args.total, args.normal_ratio, args.days, args.seed)

    fieldnames = ["timestamp", "source_ip", "user", "status", "message", "attack_type", "is_attack", "geoip_country", "geoip_city", "log_type"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    n_attack = sum(1 for r in rows if r.get("is_attack"))
    print(f"Da sinh {len(rows)} dong -> {out}")
    print(f"  Normal: {len(rows) - n_attack}, Attack: {n_attack}, Ty le attack: {n_attack/len(rows):.2%}")

    if args.replace_logs:
        main_logs = PROJECT_ROOT / "data" / "raw" / "logs.csv"
        import shutil
        shutil.copy(out, main_logs)
        print(f"  Da copy thanh data/raw/logs.csv (thay the dataset chinh).")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
