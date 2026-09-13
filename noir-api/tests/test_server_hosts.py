"""サーバー編の基盤（archive_node/corp_server。バックエンド_コマンド機能仕様 § 5c）。

Mission26/27 はまだ `_DEFS` に存在しないため、`required_mission_id` をテスト内で
既存の（クリア済みの）Mission id に一時的に差し替えてホストを解放する
（`commands.SSH_HOSTS[host]["required_mission_id"]` を monkeypatch。実装が揃うまでの
間、本番ではこの2ホストへは誰も到達できない＝予約済みのまま）。
"""

import pytest

from app.evaluator import commands
from app.evaluator.engine import evaluate
from tests.helpers import state_at_mission


@pytest.fixture(autouse=True)
def _unlock_server_hosts(monkeypatch):
    # state_at_mission(22) は Mission21 までクリア済みなので、21 を要求元にすれば
    # 「解放済み」になる。
    monkeypatch.setitem(commands.SSH_HOSTS["archive_node"], "required_mission_id", 21)
    monkeypatch.setitem(commands.SSH_HOSTS["corp_server"], "required_mission_id", 21)


def _run(state: dict, line: str) -> tuple[list[str], dict]:
    return evaluate(line, state)


def _ssh(state: dict, host: str) -> dict:
    out, state = _run(state, f"ssh {host}")
    assert out == [f"Connected to {host}"]
    return state


# --- archive_node ---


def test_ssh_archive_node_hostname_and_uname() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "hostname")
    assert out == ["archive-node-01"]
    out, s = _run(s, "uname")
    assert out == ["Linux"]
    out, s = _run(s, "uname -a")
    assert out == [
        "Linux archive-node-01 6.1.0-18-amd64 #1 SMP Debian 6.1.76-1 x86_64 GNU/Linux"
    ]


def test_ssh_archive_node_os_release() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "cat /etc/os-release")
    assert 'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"' in out
    assert 'NAME="Debian GNU/Linux"' in out
    assert 'VERSION_ID="12"' in out


def test_archive_node_df_shows_var_at_98_percent() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "df -h")
    assert any("98%" in ln and "/var" in ln for ln in out)
    assert any("/dev/sda1" in ln and "/" in ln for ln in out)


def test_archive_node_du_uses_sizes_table() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "du -sh /var/log/spool.log")
    assert out == ["17G\t/var/log/spool.log"]


def test_archive_node_du_glob_expands_multiple_rows() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "du -sh /var/log/*")
    assert "17G\t/var/log/spool.log" in out
    assert "220M\t/var/log/syslog" in out
    assert "12M\t/var/log/auth.log" in out


def test_archive_node_systemctl_status_failed_service() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "systemctl status archive-indexer")
    assert out[0] == "● archive-indexer.service - Archive indexer"
    assert "failed (Result: exit-code)" in out[1]
    assert any("No space left on device" in ln for ln in out)


def test_archive_node_journalctl_with_n() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "journalctl -u archive-indexer -n 1")
    assert out[0].startswith("-- Logs begin at")
    assert len(out) == 2
    assert "Failed with result 'exit-code'." in out[1]


def test_archive_node_ip_a() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "ip a")
    assert any("192.168.10.5/24" in ln for ln in out)
    assert any("127.0.0.1/8" in ln for ln in out)


def test_archive_node_crontab_l() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "crontab -l")
    assert "0 2 * * * /usr/local/bin/backup.sh" in out
    assert "*/30 * * * * /usr/bin/healthcheck.sh" in out


def test_archive_node_ss_before_and_after_stopping_sshd() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "ss -tln")
    assert any(":22 " in ln for ln in out)

    out, s = _run(s, "systemctl stop sshd")
    assert out == []
    out, s = _run(s, "ss -tln")
    assert not any(":22 " in ln for ln in out)

    out, s = _run(s, "systemctl status sshd")
    assert "inactive (dead)" in out[1]

    out, s = _run(s, "systemctl start sshd")
    assert out == []
    out, s = _run(s, "systemctl status sshd")
    assert "active (running)" in out[1]
    out, s = _run(s, "ss -tln")
    assert any(":22 " in ln for ln in out)


def test_overrides_persist_across_exit_and_reconnect() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "systemctl stop sshd")
    assert out == []
    out, s = _run(s, "exit")
    assert out == []
    s = _ssh(s, "archive_node")
    out, s = _run(s, "systemctl status sshd")
    assert "inactive (dead)" in out[1]


def test_systemctl_stop_refused_locally() -> None:
    s = state_at_mission(22)
    out, s = _run(s, "systemctl stop sshd")
    assert out == ["Error: command not allowed"]


def test_systemctl_status_unknown_unit() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "archive_node")
    out, s = _run(s, "systemctl status nope")
    assert out == ["Unit nope.service could not be found."]


def test_systemctl_status_local_always_not_found() -> None:
    s = state_at_mission(22)
    out, s = _run(s, "systemctl status sshd")
    assert out == ["Unit sshd.service could not be found."]


# --- corp_server ---


def test_ssh_corp_server_hostname_uname_os_release() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "hostname")
    assert out == ["corp-web-01"]
    out, s = _run(s, "uname -a")
    assert "Ubuntu" in out[0]
    out, s = _run(s, "cat /etc/os-release")
    assert 'PRETTY_NAME="Ubuntu 24.04 LTS"' in out


def test_corp_server_df() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "df -h")
    assert any("41%" in ln for ln in out)


def test_corp_server_crontab_l() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "crontab -l")
    assert out == ["0 3 * * * /usr/bin/certbot renew"]


def test_corp_server_curl_metadata_key() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "curl http://169.254.169.254/latest/meta-data/instance-id")
    assert out == ["i-0f3e9a7c2b1d4e5f6"]


def test_corp_server_curl_metadata_listing() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "curl http://169.254.169.254/latest/meta-data/")
    assert "instance-id" in out
    assert "region" in out


def test_corp_server_curl_metadata_unknown_key() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "curl http://169.254.169.254/latest/meta-data/nope")
    assert out == ["404 - Not Found"]


def test_corp_server_curl_non_mock_url() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "curl http://example.com/")
    assert out == ["curl: (6) Could not resolve host: example.com"]


def test_local_curl_metadata_fails_to_connect() -> None:
    s = state_at_mission(22)
    out, s = _run(s, "curl http://169.254.169.254/latest/meta-data/instance-id")
    assert out == ["curl: (7) Failed to connect to 169.254.169.254 port 80"]


def test_corp_server_backdoor_relay_active_and_ss_shows_4444() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "ss -tln")
    assert any(":4444 " in ln for ln in out)
    assert any(":8080 " in ln for ln in out)
    # sshd は最初から failed なので 22 は listen していない。
    assert not any(":22 " in ln for ln in out)


def test_corp_server_journalctl_backdoor_relay() -> None:
    s = state_at_mission(22)
    s = _ssh(s, "corp_server")
    out, s = _run(s, "journalctl -u backdoor-relay")
    assert any("forwarding to 10.66.6.6" in ln for ln in out)
