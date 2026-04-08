#!/usr/bin/env python3
"""
De xuat phong thu theo loai tan cong / bat thuong.
Map: attack_type, severity -> danh sach hanh dong phong thu (tieng Viet + English).
"""
from typing import List, Tuple

# attack_type (hoac anomaly) -> (severity) -> list of (title, description)
RECOMMENDATIONS = {
    "brute_force": {
        "high": [
            ("Bat chặn tự động (fail2ban)", "Theo dõi các lần đăng nhập sai. Nếu cùng 1 IP thử quá nhiều lần thì chặn IP tạm thời để ngăn brute-force."),
            ("Chính sách mật khẩu mạnh", "Bắt mật khẩu đủ dài và đủ mạnh. Khuyến nghị ưu tiên SSH key thay vì mật khẩu; nếu có thể thì bật thêm 2FA cho tài khoản quản trị."),
            ("Giới hạn số phiên/kết nối SSH", "Giới hạn số phiên SSH và số lần thử đăng nhập đồng thời. Việc này làm giảm hiệu quả các đợt quét/brute-force."),
            ("Chỉ cho SSH key", "Tắt đăng nhập bằng mật khẩu, chỉ cho đăng nhập bằng SSH key (giảm tối đa rủi ro brute-force từ password)."),
        ],
        "medium": [
            ("Theo doi log dang nhap", "Giam sat auth.log/sshd, canh bao khi nhieu failed tu cung IP."),
            ("Xem xet doi port SSH", "Doi port 22 sang port khac de giam scan tu dong (khong thay the cac bien phap khac)."),
        ],
    },
    "sql_injection": {
        "high": [
            ("Su dung prepared statements / ORM", "Tranh noi chuoi SQL tu input; dung parameterized queries."),
            ("WAF (Web Application Firewall)", "Bat mod_security hoac WAF truoc ung dung de loc request nghi ngo."),
            ("Validate va escape input", "Kiem tra kieu du lieu, gioi han do dai, escape ky tu dac biet."),
        ],
        "medium": [
            ("Phan quyen database", "User ung dung chi can quyen can thiet, khong dung root."),
            ("Log va canh bao request loi", "Ghi log request chua pattern SQL injection, dung ELKShield/Kibana xem."),
        ],
    },
    "xss": {
        "high": [
            ("Encode output (HTML/JS)", "Hien thi user input da encode (HTML entity, escape trong JS) de tranh thuc thi script."),
            ("Content-Security-Policy (CSP)", "Header CSP han che nguon script, giam surface XSS."),
        ],
        "medium": [
            ("Validate input (allowlist)", "Chi chap nhan ky tu/format hop le, loai bo tag va script."),
            ("HttpOnly cookie", "Danh dau session cookie HttpOnly de script doc duoc cookie kho hon."),
        ],
    },
    "escalation": {
        "high": [
            ("Han che sudo / su", "Chi cho phep sudo voi user can thiet; dung NOPASSWD han hep, audit sudoers."),
            ("Audit dang nhap va phan quyen", "Theo doi auth.log, auditd voi su/sudo; nguyen tac least privilege."),
            ("Tach quyen ung dung", "User chay web app (www-data) khong nen co quyen su/sudo len root."),
        ],
        "medium": [
            ("Giam sat session va thay doi user", "Canh bao khi co su/sudo bat thuong (tu IP la, gio bat thuong)."),
        ],
    },
    "unknown": {
        "high": [
            ("Xem lai log va nguyen nhan", "Phan tich log bat thuong (IP, user, request) de xac dinh loai tan cong."),
            ("Cap nhat va patch", "Dam bao OS, service (sshd, web server) va ung dung duoc cap nhat bao mat."),
        ],
        "medium": [
            ("Tang cuong giam sat", "Bat canh bao Kibana/Watcher khi co nhieu anomaly cung IP hoac cung loai."),
        ],
    },
}


def get_recommendations(attack_type: str, severity: str = "high") -> List[Tuple[str, str]]:
    """
    Tra ve danh sach (tieu de, mo ta) phong thu cho attack_type va severity.
    attack_type: brute_force | sql_injection | xss | unknown (hoac ''/None)
    severity: high | medium
    """
    if not attack_type or attack_type not in RECOMMENDATIONS:
        attack_type = "unknown"
    by_severity = RECOMMENDATIONS.get(attack_type, RECOMMENDATIONS["unknown"])
    # Lay ca high va medium neu severity la high; chi medium neu severity la medium
    out = list(by_severity.get(severity, []))
    if severity == "high" and "medium" in by_severity:
        out = list(by_severity["high"]) + list(by_severity.get("medium", []))
    return out if out else list(RECOMMENDATIONS["unknown"]["high"])


def format_recommendations_text(attack_type: str, severity: str = "high", lang: str = "vi") -> str:
    """Tra ve chuoi van ban: moi dong la mot de xuat (tieu de: mo ta)."""
    items = get_recommendations(attack_type, severity)
    lines = []
    for i, (title, desc) in enumerate(items, 1):
        lines.append(f"{i}. {title}: {desc}")
    return "\n".join(lines)


def add_recommendations_to_dataframe(df):
    """
    Them cot defense_recommendations vao DataFrame.
    Can cot attack_type (va tuy chon ml_anomaly/is_attack de set severity).
    """
    import pandas as pd
    if "attack_type" not in df.columns:
        df["attack_type"] = ""
    if "defense_recommendations" in df.columns:
        return df
    recs = []
    for _, row in df.iterrows():
        at = (row.get("attack_type") or "").strip() or "unknown"
        sev = "high" if row.get("ml_anomaly") or row.get("is_attack") else "medium"
        items = get_recommendations(at, sev)
        recs.append(" | ".join([t for t, _ in items]))
    df["defense_recommendations"] = recs
    return df


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="In de xuat phong thu theo loai tan cong")
    p.add_argument("--attack-type", default="brute_force", choices=["brute_force", "sql_injection", "xss", "unknown"])
    p.add_argument("--severity", default="high", choices=["high", "medium"])
    args = p.parse_args()
    print(format_recommendations_text(args.attack_type, args.severity))
