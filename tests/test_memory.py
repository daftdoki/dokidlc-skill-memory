"""Tests for scripts/memory that need neither the tool nor ollama."""

import json
import socket
import threading
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_loader = SourceFileLoader("memory", str(ROOT / "bin" / "memory"))
_spec = importlib.util.spec_from_loader("memory", _loader)
memory = importlib.util.module_from_spec(_spec)
_loader.exec_module(memory)


def test_field_name_is_stable_and_distinct(tmp_path):
    a = tmp_path / "Agent_One"
    b = tmp_path / "agent-one"
    a.mkdir(); b.mkdir()
    assert memory.field_name(a) == memory.field_name(a)
    assert memory.field_name(a) != memory.field_name(b)
    assert memory.NAME_RE.match(memory.field_name(a))
    assert memory.field_name(a).startswith("agent-one-")


def test_config_text_points_at_dot_memory(tmp_path):
    text = memory.config_text(tmp_path)
    assert f'location = "{(tmp_path / ".memory").resolve()}"' in text
    assert 'index_location = "cache"' in text
    assert f"[memoryfields.{memory.field_name(tmp_path)}]" in text


def test_normalize_host():
    assert memory.normalize_host(None) == "http://127.0.0.1:11434"
    assert memory.normalize_host("localhost:11434") == "http://localhost:11434"
    assert memory.normalize_host("http://x:1/") == "http://x:1"
    assert memory.normalize_host("https://x:1") == "https://x:1"


def test_host_guard_closed_port_returns_fast():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    assert memory.host_answers(f"http://127.0.0.1:{port}", timeout=1.0) is False


def test_host_guard_silent_host_returns_within_timeout():
    """A host that accepts and never replies must not hang. This is the 75s case."""
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    port = srv.getsockname()[1]
    stop = threading.Event()

    def hold():
        conns = []
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conns.append(srv.accept()[0])
            except socket.timeout:
                pass
        for c in conns:
            c.close()

    t = threading.Thread(target=hold, daemon=True); t.start()
    import time
    start = time.monotonic()
    assert memory.host_answers(f"http://127.0.0.1:{port}", timeout=1.0) is False
    assert time.monotonic() - start < 3.0
    stop.set(); t.join(); srv.close()


def test_read_pin(tmp_path):
    p = tmp_path / "pin"
    p.write_text("# comment\ntool_rev=abc123\nmodel = nomic-embed-text\n\n")
    assert memory.read_pin(p) == {"tool_rev": "abc123", "model": "nomic-embed-text"}


def test_pin_matches_prefix_either_way():
    pin = {"tool_rev": "3e447e1d5c4840028cce3c05e70e7349923fc634"}
    assert memory.pin_matches(pin, "3e447e1d5c4840028cce3c05e70e7349923fc634")
    assert memory.pin_matches(pin, "3e447e1")
    assert not memory.pin_matches(pin, "deadbeef")
    assert not memory.pin_matches(pin, None)


def test_filter_results_drops_index_md():
    rows = [{"filename": "index.md"}, {"filename": "a.md"}]
    assert memory.filter_results(rows) == [{"filename": "a.md"}]


def test_tokens_estimate():
    assert memory.tokens(0) == 0
    assert memory.tokens(4) == 1
    assert memory.tokens(5) == 2


def test_strip_ansi():
    assert memory.strip_ansi("\x1b[36m/a/b\x1b[39m\n") == "/a/b\n"


def test_parse_and_render_round_trip():
    text = "---\ntitle: T\nsummary: S\ntopics:\n- a\nkind: finding\ncreated: '2026-09-01T00:00:00Z'\n---\nbody\n\n## Sources\n\n- x\n"
    fm, body = memory.parse_page(text)
    assert fm["topics"] == ["a"] and fm["created"] == "2026-09-01T00:00:00Z"
    out = memory.render_page(fm, body)
    assert "created: '2026-09-01T00:00:00Z'" in out
    assert out.endswith("- x\n")
    assert memory.parse_page(out) == (fm, body)


def test_parse_page_without_frontmatter():
    assert memory.parse_page("just text\n") == ({}, "just text\n")


def test_validate_page_rules():
    good = {"title": "T", "summary": "S", "topics": ["a"], "kind": "finding"}
    assert memory.validate_page("ok-page.md", good, "b\n\n## Sources\n\n- x\n") == []
    errs = memory.validate_page("Bad_Name.md", {"title": "T"}, "no sources")
    assert any("page name" in e for e in errs)
    assert any("summary" in e for e in errs)
    assert any("topics" in e for e in errs)
    assert any("kind" in e for e in errs)
    assert any(e.startswith("warning:") and "Sources" in e for e in errs)
    assert any("index.md" in e for e in memory.validate_page("index.md", good, "## Sources\n"))


def test_fill_ref_from_git(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "docs").mkdir(); (tmp_path / "docs" / "a.md").write_text("one\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "one"], check=True)
    sha = subprocess.run(["git", "-C", str(tmp_path), "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
    assert memory.fill_ref("docs/a.md", tmp_path) == f"docs/a.md@{sha}"
    assert memory.fill_ref("docs/a.md@abc1234", tmp_path) == "docs/a.md@abc1234"
    with pytest.raises(SystemExit):
        memory.fill_ref("docs/missing.md", tmp_path)
    with pytest.raises(SystemExit):
        memory.fill_ref("docs/a.md@nothex", tmp_path)


def test_regenerate_index_counts_topics_and_keeps_head(tmp_path):
    field = tmp_path / ".memory"; field.mkdir()
    (field / "index.md").write_text("---\ntitle: Memory\n---\n\nHand-written intro.\n\n<!-- generated below -->\n\nold stuff\n")
    (field / "a.md").write_text("---\ntopics:\n- install\n- ollama\n---\nx\n")
    (field / "b.md").write_text("---\ntopics:\n- install\n---\ny\n")
    memory.regenerate_index(field)
    text = (field / "index.md").read_text()
    assert "Hand-written intro." in text
    assert "old stuff" not in text
    assert "Topics across 2 pages:" in text
    assert text.index("- install (2)") < text.index("- ollama (1)")


def test_regenerate_index_without_marker_appends_one(tmp_path):
    field = tmp_path / ".memory"; field.mkdir()
    (field / "index.md").write_text("intro only\n")
    memory.regenerate_index(field)
    text = (field / "index.md").read_text()
    assert text.startswith("intro only\n\n<!-- generated below -->")
    assert "(no pages yet)" in text


def _repo(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "docs").mkdir(); (tmp_path / "docs" / "a.md").write_text("one\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "one"], check=True)
    return subprocess.run(["git", "-C", str(tmp_path), "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()


def test_ref_changed_after_commit(tmp_path):
    import subprocess
    sha = _repo(tmp_path)
    assert memory.ref_changed(f"docs/a.md@{sha}", tmp_path) is None
    (tmp_path / "docs" / "a.md").write_text("two\n")
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qam", "two"], check=True)
    reason = memory.ref_changed(f"docs/a.md@{sha}", tmp_path)
    assert reason and "changed since cited (1 commit)" in reason
    assert "not found" in memory.ref_changed("docs/a.md@deadbeef", tmp_path)
    assert "no commit cited" in memory.ref_changed("docs/a.md", tmp_path)


def test_age_hint_by_kind():
    from datetime import UTC, datetime
    now = datetime(2026, 12, 1, tzinfo=UTC)
    old = {"kind": "environment", "updated": "2026-09-01T00:00:00Z"}
    assert "environment page, 91 days since written" == memory.age_hint(old, now)
    assert memory.age_hint({"kind": "procedure", "updated": "2026-09-01T00:00:00Z"}, now) == "procedure page, 91 days since written"
    assert memory.age_hint({"kind": "finding", "updated": "2026-09-01T00:00:00Z"}, now) is None
    assert memory.age_hint({"kind": "decision", "updated": "2020-01-01T00:00:00Z"}, now) is None
    verified = {"kind": "environment", "updated": "2026-01-01T00:00:00Z", "verified": "2026-11-20T00:00:00Z"}
    assert memory.age_hint(verified, now) is None


def test_suspicion_ranks_ref_before_check_before_age(tmp_path):
    from datetime import UTC, datetime
    import subprocess
    sha = _repo(tmp_path)
    (tmp_path / "docs" / "a.md").write_text("two\n")
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qam", "two"], check=True)
    fm = {"kind": "environment", "updated": "2026-01-01T00:00:00Z", "refs": [f"docs/a.md@{sha}"], "check": "false"}
    signals = memory.suspicion(fm, tmp_path, run_checks=True, now=datetime(2026, 12, 1, tzinfo=UTC))
    assert [s for s, _ in signals] == ["ref", "check", "age"]
    without = memory.suspicion(fm, tmp_path, run_checks=False, now=datetime(2026, 12, 1, tzinfo=UTC))
    assert [s for s, _ in without] == ["ref", "age"]
    assert memory.marker(signals).startswith("  suspect: docs/a.md changed")
    assert "glance: environment page" in memory.marker(signals)
    assert memory.marker([]) == ""


def test_run_check_pass_fail_timeout():
    assert memory.run_check("true") is None
    assert "exit 1" in memory.run_check("false")
    memory.CHECK_TIMEOUT = 1
    assert "timed out" in memory.run_check("sleep 5")
    memory.CHECK_TIMEOUT = 10


def test_distance_text_handles_substring_fallback():
    assert memory.distance_text({"distance": 0.3333}) == "distance 0.333"
    assert memory.distance_text({"distance": None}) == "string match"
    assert memory.distance_text({}) == "string match"


def test_set_root_and_project_root(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert memory.project_root() == tmp_path.resolve()
    memory.set_root(tmp_path)
    assert memory.FIELD_DIR == tmp_path.resolve() / ".memory"
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    assert memory.project_root() == tmp_path.resolve()


def test_index_carries_format_line_and_check(tmp_path, capsys):
    field = tmp_path / ".memory"; field.mkdir()
    (field / "index.md").write_text("intro\n")
    memory.set_root(tmp_path)
    memory.regenerate_index()
    text = (field / "index.md").read_text()
    assert "<!-- memory format 1, written by memory" in text
    assert memory.read_format() == 1
    (field / "index.md").write_text(text.replace("format 1", "format 2"))
    with pytest.raises(SystemExit) as e:
        memory.check_format()
    assert e.value.code == 2 and "newer memory plugin" in capsys.readouterr().err
    (field / "index.md").write_text("intro only\n")
    assert memory.read_format() == 0
    memory.check_format()
    assert memory.read_format() == 1


def test_init_appends_paragraph_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(memory.shutil, "which", lambda name: None)
    (tmp_path / "CLAUDE.md").write_text("# Agent\n")
    memory.main(["init"])
    text = (tmp_path / "CLAUDE.md").read_text()
    assert text.startswith("# Agent\n") and text.count(memory.CLAUDE_MD_MARK) == 1
    assert (tmp_path / ".memory" / "index.md").is_file()
    memory.main(["init"])
    assert (tmp_path / "CLAUDE.md").read_text().count(memory.CLAUDE_MD_MARK) == 1
    assert "nothing changed" in capsys.readouterr().out


def test_doctor_brief_guides_setup(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    memory.main(["doctor", "--brief"])
    assert "not set up on this machine" in capsys.readouterr().out
    memory.main(["setup", "--substring"]); capsys.readouterr()
    memory.main(["doctor", "--brief"])
    assert "no .memory/" in capsys.readouterr().out
    monkeypatch.setattr(memory.shutil, "which", lambda name: None)
    memory.main(["init"]); capsys.readouterr()
    memory.main(["doctor", "--brief"])
    out = capsys.readouterr().out
    assert out.startswith("memory: 0 pages, string search.") and "Persistence:" in out   # no git repo yet


def test_git_checks_and_init_staging(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(memory.shutil, "which", lambda name: None)
    memory.set_root(tmp_path)
    assert memory.git_checks()[0][1] == "this directory is a git repository"
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".memory/\n")
    memory.main(["init"])
    states = {label: ok for ok, label, _ in memory.git_checks()}
    assert states[".memory is ignored by git"] is False
    assert states[".claude/settings.json does not exist"] is False
    (tmp_path / ".gitignore").write_text("")
    (tmp_path / ".claude").mkdir(); (tmp_path / ".claude" / "settings.json").write_text("{}")
    memory.git_add([".memory", "CLAUDE.md", ".claude/settings.json"])
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"], check=True)
    assert all(ok for ok, _, _ in memory.git_checks())


def test_host_candidates_order(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert memory.host_candidates() == [("http://127.0.0.1:11434", "default")]
    memory.write_config_file({"embedding_host": "http://frame:11434"})
    assert memory.host_candidates() == [("http://frame:11434", "memory setup"), ("http://127.0.0.1:11434", "default")]
    monkeypatch.setenv("OLLAMA_HOST", "other:1")
    assert [c[1] for c in memory.host_candidates()] == ["OLLAMA_HOST", "memory setup", "default"]


def test_resolve_host_skips_a_dead_env_host(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("OLLAMA_HOST", "http://dead:11434")
    memory.write_config_file({"embedding_host": "http://frame:11434"})
    monkeypatch.setattr(memory, "host_answers", lambda url, timeout=2.0: url == "http://frame:11434")
    memory._RESOLVED = None
    assert memory.resolve_host() == ("http://frame:11434", "memory setup", True)
    memory._RESOLVED = None
    monkeypatch.setattr(memory, "host_answers", lambda url, timeout=2.0: False)
    assert memory.resolve_host() == ("http://dead:11434", "OLLAMA_HOST", False)
    memory._RESOLVED = None


def test_search_json_never_calls_the_tool_on_a_dead_host(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setattr(memory, "host_answers", lambda url, timeout=2.0: False)
    memory._RESOLVED = None
    called = []
    monkeypatch.setattr(memory, "tool", lambda *a, **k: called.append(a))
    assert memory.search_json("anything") == []
    assert called == []
    memory._RESOLVED = None


def test_setup_writes_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setattr(memory, "host_answers", lambda base, timeout=2.0: False)
    memory.main(["setup", "--host", "frame:11434"])
    assert memory.read_config() == {"semantic": True, "embedding_host": "http://frame:11434"}
    assert "does not answer yet" in capsys.readouterr().out
    memory.main(["setup", "--local"])
    assert memory.read_config()["embedding_host"] == "http://127.0.0.1:11434"
    memory.main(["setup", "--substring"])
    assert memory.read_config()["semantic"] is False and memory.semantic_enabled() is False
    assert memory.tool_env()["OLLAMA_HOST"] == memory.NO_EMBEDDING_HOST
    monkeypatch.setenv("OLLAMA_HOST", "x:1")
    assert memory.semantic_enabled() is True
    monkeypatch.delenv("OLLAMA_HOST")
    with pytest.raises(SystemExit):
        memory.main(["setup", "--local", "--host", "x"])
    with pytest.raises(SystemExit):
        memory.main(["setup", "--semantic", "--substring"])


def test_semantic_is_on_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert memory.semantic_enabled() is True
    memory.write_config_file({"semantic": False})
    assert memory.semantic_enabled() is False


def test_merge_results_unions_and_ranks():
    a = [{"filename": "x.md", "summary": "X", "distance": 0.4}, {"filename": "y.md", "summary": "Y", "distance": None}]
    b = [{"filename": "y.md", "summary": "Y", "distance": None}, {"filename": "z.md", "summary": "Z", "distance": 0.2}]
    rows = memory.merge_results([("one", a), ("two", b)])
    assert [r["filename"] for r in rows] == ["y.md", "z.md", "x.md"]     # matched by both terms first, then by distance
    assert rows[0]["matched"] == ["one", "two"]


def test_parse_results_skips_the_fallback_notice():
    noisy = 'embedding failed: Failed to connect to Ollama.\n[\n  {"filename": "a.md", "summary": "A", "distance": null}\n]\n'
    assert memory.parse_results(noisy) == [{"filename": "a.md", "summary": "A", "distance": None}]
    assert memory.parse_results("") == []
    assert memory.parse_results("garbage") == []


def test_query_terms_keeps_identifiers_and_parts():
    assert memory.query_terms("Why does install fail on a mac with pysqlite3-binary?") == ["install", "fail", "mac", "pysqlite3-binary", "pysqlite3", "binary"]
    assert memory.query_terms("the of and") == []


def test_string_search_and_hybrid_ranking(tmp_path, monkeypatch):
    field = tmp_path / ".memory"; field.mkdir()
    (field / "index.md").write_text("intro\n")
    (field / "pysqlite3-install-override.md").write_text("---\ntitle: pysqlite3-binary blocks install\nsummary: the uv override\n---\nx\n")
    (field / "ollama-host-silent-hang.md").write_text("---\ntitle: A silent OLLAMA_HOST hangs the tool\nsummary: probe first\n---\nx\n")
    (field / "unrelated.md").write_text("---\ntitle: Something else\nsummary: nothing here\n---\nx\n")
    memory.set_root(tmp_path)
    hits = memory.string_search(["install", "pysqlite3", "hang"])
    assert {r["filename"]: r["matched"] for r in hits} == {"pysqlite3-install-override.md": ["install", "pysqlite3"], "ollama-host-silent-hang.md": ["hang"]}
    (field / "body-only.md").write_text("---\ntitle: Elsewhere\nsummary: nothing\n---\nthe incident was filed as I113.\n")
    body = memory.string_search(["i113"])
    assert [r["filename"] for r in body] == ["body-only.md"] and body[0]["head_hits"] == 0
    monkeypatch.setattr(memory, "semantic_enabled", lambda: True)
    monkeypatch.setattr(memory, "search_json", lambda q: [
        {"filename": "unrelated.md", "summary": "nothing here", "distance": 0.30},
        {"filename": "pysqlite3-install-override.md", "summary": "the uv override", "distance": 0.40},
    ])
    rows = memory.hybrid_search("why does install fail with pysqlite3")
    assert [r["filename"] for r in rows] == ["pysqlite3-install-override.md", "unrelated.md"]   # found by both beats a closer semantic-only hit
    assert rows[0]["via"] == ["semantic", "install", "pysqlite3"]
    monkeypatch.setattr(memory, "semantic_enabled", lambda: False)
    rows = memory.hybrid_search("hang")
    assert [r["filename"] for r in rows] == ["ollama-host-silent-hang.md"] and rows[0]["via"] == ["hang"]


def test_url_refs_are_kept_and_never_checked_in_search(tmp_path):
    assert memory.fill_ref("https://example.com/x", tmp_path) == "https://example.com/x"
    assert memory.ref_changed("https://example.com/x", tmp_path) is None
    assert memory.suspicion({"refs": ["https://example.com/x"]}, tmp_path) == []


def test_url_status_gone_and_unreachable():
    import http.server, threading, socket
    class H(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(404 if self.path == "/gone" else 200); self.end_headers()
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H); port = srv.server_port
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        assert memory.url_status(f"http://127.0.0.1:{port}/ok") is None
        sig, reason = memory.url_status(f"http://127.0.0.1:{port}/gone")
        assert sig == "ref" and "gone" in reason
    finally:
        srv.shutdown()
    s = socket.socket(); s.bind(("127.0.0.1", 0)); closed = s.getsockname()[1]; s.close()
    sig, reason = memory.url_status(f"http://127.0.0.1:{closed}/x", timeout=1.0)
    assert sig == "url" and "could not be reached" in reason
    assert memory.marker([("url", "x could not be reached")]).startswith("  glance:")


def test_guard_asks_only_for_network_doubt():
    import json, subprocess
    shim = ROOT / "scripts" / "guard.sh"
    def run(cmd):
        return subprocess.run(["sh", str(shim)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}), capture_output=True, text=True)
    assert run("memory doubt").stdout == ""
    assert run("git status").stdout == ""
    out = json.loads(run("memory doubt --network").stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_recall_gates_and_filter():
    assert not memory.recall_worthy("yes")
    assert not memory.recall_worthy("3> agree, and the second one too, please go ahead")
    assert not memory.recall_worthy("/plugin install memory@dokidlc and then something long enough")
    assert memory.recall_worthy("why does installing memoryfield-tool fail on this mac")
    rows = [
        {"filename": "both.md", "summary": "B", "distance": 0.45, "via": ["semantic", "install"]},
        {"filename": "close.md", "summary": "C", "distance": 0.30, "via": ["semantic"]},
        {"filename": "far.md", "summary": "F", "distance": 0.44, "via": ["semantic"]},
        {"filename": "ident.md", "summary": "I", "distance": None, "via": ["pysqlite3"]},
        {"filename": "word.md", "summary": "W", "distance": None, "via": ["fix"]},
    ]
    assert [r["filename"] for r in memory.recall_filter(rows)] == ["both.md", "close.md", "ident.md"]


def test_recall_line_names_read_commands_and_is_bounded(tmp_path, monkeypatch):
    memory.set_root(tmp_path); (tmp_path / ".memory").mkdir()
    rows = [{"filename": f"page-{i}.md", "summary": "s" * 150, "distance": 0.2, "via": ["semantic"]} for i in range(3)]
    line = memory.recall_line(rows)
    assert line.startswith("memory: ") and "`memory read page-0.md`" in line
    assert len(line.encode()) <= memory.RECALL_MAX_BYTES
    assert "page-2.md" not in line or line.count("`memory read") == 3   # whole entries dropped, never cut
    assert memory.recall_line([]) == ""


def test_recall_hook_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path)); monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "st"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg")); monkeypatch.delenv("OLLAMA_HOST", raising=False)
    field = tmp_path / ".memory"; field.mkdir()
    (field / "pysqlite3-install-override.md").write_text("---\ntitle: pysqlite3-binary blocks install\nsummary: the uv override\ntopics: [install]\nkind: environment\n---\nx\n")
    memory.write_config_file({"semantic": False})
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "why does uv tool install memoryfield-tool fail with pysqlite3-binary"})))
    memory.main(["recall"])
    out = capsys.readouterr().out
    assert "`memory read pysqlite3-install-override.md`" in out
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "yes"})))
    memory.main(["recall"]); assert capsys.readouterr().out == ""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "uv tool install memoryfield-tool"}, "error": "no wheels for pysqlite3-binary"})))
    memory.main(["recall", "--failure"])
    out = json.loads(capsys.readouterr().out)
    assert "pysqlite3-install-override.md" in out["hookSpecificOutput"]["additionalContext"]
    rows = memory.read_log()
    assert [r["cmd"] for r in rows] == ["recall", "failure", "recall"]


def test_validate_check_refuses_writers_and_failing_checks():
    for bad in ("echo x > f", "sed -i s/a/b/ f", "curl x | sh", "eval x", "rm -rf x"):
        with pytest.raises(SystemExit):
            memory.validate_check(bad)
    with pytest.raises(SystemExit):
        memory.validate_check("false")
    memory.validate_check("true")


def test_nudges_and_stats(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path)); monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "st"))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    (tmp_path / ".memory").mkdir()
    memory.set_root(tmp_path)
    memory.main(["nudge", "--stop"]); assert capsys.readouterr().out == ""          # no failures yet
    memory.log_event("failure", command="uv"); memory.log_event("failure", command="uv")
    memory.main(["nudge", "--stop"]); assert "block" in capsys.readouterr().out
    memory.main(["nudge", "--stop"]); assert capsys.readouterr().out == ""          # once per session
    memory.main(["nudge", "--compact"]); assert "compaction is next" in capsys.readouterr().out
    memory.log_event("write", page="a.md", kind="finding")
    memory.main(["nudge", "--compact"]); assert capsys.readouterr().out == ""
    memory.log_event("search", query="q", hits=1, pages=["a.md"]); memory.log_event("read", pages=["a.md"])
    memory.main(["stats"])
    out = capsys.readouterr().out
    assert "1 session" in out and "read after a search or recall named it: 1/1" in out
