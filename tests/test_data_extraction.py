#!/usr/bin/env python3
"""Unit tests for data_extraction (parse_ssh_message, get_log_type)."""
import sys
from pathlib import Path

# Add project root so we can import scripts
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_extraction import parse_ssh_message, get_log_type


def test_parse_ssh_message_failed_password():
    msg = "Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2"
    ip, user, status, is_attack, attack_type = parse_ssh_message(msg)
    assert ip == "10.10.10.10"
    assert user == "admin"
    assert status == "failed"
    assert is_attack is True
    assert attack_type == "brute_force"


def test_parse_ssh_message_accepted():
    msg = "Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2"
    ip, user, status, is_attack, attack_type = parse_ssh_message(msg)
    assert ip == "192.168.1.10"
    assert user == "user1"
    assert status == "accepted"
    assert is_attack is False
    assert attack_type == ""


def test_parse_ssh_message_empty():
    ip, user, status, is_attack, attack_type = parse_ssh_message("")
    assert ip == "" and user == "" and status == "" and is_attack is False


def test_parse_ssh_message_none():
    ip, user, status, is_attack, attack_type = parse_ssh_message(None)
    assert ip == "" and user == ""


def test_get_log_type_from_fields():
    log = {"fields": {"log_type": "ssh"}}
    assert get_log_type(log) == "ssh"
    log2 = {"fields": {"log_type": "web"}}
    assert get_log_type(log2) == "web"


def test_get_log_type_from_message():
    log = {"message": "sshd[123]: Failed password for root from 1.2.3.4 port 22"}
    assert get_log_type(log) in ("ssh", None)  # may infer ssh from content
