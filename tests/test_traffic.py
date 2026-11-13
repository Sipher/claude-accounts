"""Regression tests for upstream error handling; no network or credentials required."""
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "claude-accounts"
loader = importlib.machinery.SourceFileLoader("accounts", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
accounts = importlib.util.module_from_spec(spec)
loader.exec_module(accounts)


class Store:
    def __init__(self):
        self.accounts = {"one": {}, "two": {}, "three": {}}
        self.state = {}

    def label(self, acct):
        return acct


class TrafficTests(unittest.TestCase):
    def test_upstream_failure_stops_other_account_requests_even_when_forced(self):
        store = Store()
        with patch.object(accounts, "fetch_usage", side_effect=accounts.HttpError(503, "temporarily unavailable")) as fetch, \
             patch.object(accounts, "record_history"):
            _, errors = accounts.fetch_all(store, "one", force=set(store.accounts))
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(set(errors), set(store.accounts))
        self.assertGreater(store.state["usage_backoff"]["global"], accounts.time.time())

    def test_cloudflare_does_not_invalidate_login_or_switch(self):
        store = Store()
        store.state["active"] = "one"
        event = '{"error":"authentication_failed", "error_details":"HTTP 403 Attention Required! | Cloudflare", "session_id":"test"}'
        from contextlib import contextmanager
        @contextmanager
        def locked():
            yield store
        with patch.object(accounts, "locked", locked), patch.object(accounts, "sync", return_value="one"), \
             patch.object(accounts, "fetch_all", side_effect=AssertionError("should not poll")), \
             patch.object(accounts, "switch_to", side_effect=AssertionError("should not switch")), \
             patch.object(accounts, "log"), patch("sys.stdin", io.StringIO(event)):
            self.assertEqual(accounts.cmd_hook(None), 0)
        self.assertNotIn("broken", store.state)

    def test_old_prompt_hook_sends_nothing(self):
        with patch.object(accounts, "locked", side_effect=AssertionError("should not poll")):
            self.assertEqual(accounts.cmd_prime(type("Args", (), {"auto": True})()), 0)

    def prime_setup(self, store, usage):
        from contextlib import contextmanager
        @contextmanager
        def locked():
            yield store
        tmp = tempfile.mkdtemp()
        return [patch.object(accounts, "locked", locked), patch.object(accounts, "sync", return_value="one"),
                patch.object(accounts, "fetch_all", return_value=(usage, {})),
                patch.object(accounts, "fresh_login", return_value={"accessToken": "t"}),
                patch.object(accounts, "DATA_DIR", tmp), patch.object(accounts, "STATE_FILE", os.path.join(tmp, "s.json")),
                patch.object(accounts, "log")]

    def run_prime(self, store, usage, heartbeat, auto=True):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for p in self.prime_setup(store, usage):
                stack.enter_context(p)
            sleep = stack.enter_context(patch.object(accounts.time, "sleep"))
            beat = stack.enter_context(patch.object(accounts, "heartbeat", side_effect=heartbeat))
            accounts.prime_pass(auto=auto)
        return sleep, beat

    working = {"one": {"five_hour": {"utilization": 5, "resets_at": 4e9}, "seven_day": {"utilization": 5}},
               "two": {"five_hour": {"utilization": 0}, "seven_day": {"utilization": 5}},
               "three": {"five_hour": {"utilization": 0}, "seven_day": {"utilization": 5}}}

    def test_auto_heartbeat_is_on_by_default(self):
        _, beat = self.run_prime(Store(), self.working, None)
        self.assertEqual(beat.call_count, 2)

    def test_auto_heartbeat_can_be_turned_off(self):
        store = Store()
        store.state["auto_prime"] = False
        _, beat = self.run_prime(store, self.working, None)
        beat.assert_not_called()

    def test_auto_heartbeat_waits_until_someone_is_working(self):
        store = Store()
        store.state["auto_prime"] = True
        idle = dict(self.working, one={"five_hour": {"utilization": 0}, "seven_day": {"utilization": 5}})
        _, beat = self.run_prime(store, idle, None)
        beat.assert_not_called()

    def test_auto_heartbeats_are_spaced_one_at_a_time(self):
        store = Store()
        store.state["auto_prime"] = True
        sleep, beat = self.run_prime(store, self.working, None)
        self.assertEqual(beat.call_count, 2)  # "one" is already running
        sleep.assert_called_once_with(accounts.PRIME_GAP)

    def test_heartbeats_stop_at_first_block(self):
        store = Store()
        store.state["auto_prime"] = True
        idle = {a: {"five_hour": {"utilization": 0}, "seven_day": {"utilization": 5}} for a in store.accounts}
        _, beat = self.run_prime(store, idle, accounts.Fail("heartbeat failed: API Error: 403 Cloudflare"), auto=False)
        self.assertEqual(beat.call_count, 1)
        self.assertGreater(store.state["usage_backoff"]["global"], accounts.time.time())

    def test_one_expired_login_does_not_freeze_balancing(self):
        store = Store()
        usage = {a: {"five_hour": {"utilization": 10}, "seven_day": {"utilization": 10}} for a in ("one", "two")}
        from contextlib import contextmanager
        @contextmanager
        def locked():
            yield store
        with patch.object(accounts, "locked", locked), patch.object(accounts, "sync", return_value="one"), \
             patch.object(accounts, "fetch_all", return_value=(usage, {"three": "login expired"})), \
             patch.object(accounts, "rank", return_value=[]) as rank, patch.object(accounts, "log"):
            accounts.cmd_balance(type("Args", (), {"quiet": True})())
        rank.assert_called_once()


REWAKE = SCRIPT.parent / "claude-net-rewake"
rl = importlib.machinery.SourceFileLoader("rewake", str(REWAKE))
rewake = importlib.util.module_from_spec(importlib.util.spec_from_loader(rl.name, rl))
rl.exec_module(rewake)


class RewakeTests(unittest.TestCase):
    def probe_with(self, code):
        err = rewake.urllib.error.HTTPError(rewake.URL, code, "x", None, None)
        with patch.object(rewake.urllib.request, "urlopen", side_effect=err):
            return rewake.probe()[0]

    def test_blocked_or_down_api_is_not_back(self):
        for code in (403, 429, 500, 503):
            self.assertFalse(self.probe_with(code), code)

    def test_normal_status_is_back(self):
        self.assertTrue(self.probe_with(404))


if __name__ == "__main__":
    unittest.main()
