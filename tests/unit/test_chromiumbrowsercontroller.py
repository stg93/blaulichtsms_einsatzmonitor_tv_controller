import subprocess
from unittest.mock import patch

import pytest

import chromiumbrowsercontroller
from chromiumbrowsercontroller import ChromiumBrowserController, find_chromium_executable


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(chromiumbrowsercontroller.Path, "home", lambda: tmp_path)
    return tmp_path


class TestFindChromiumExecutable:
    def test_prefers_chromium_browser(self):
        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}"):
            assert find_chromium_executable() == "/usr/bin/chromium-browser"

    def test_falls_back_to_chromium(self):
        def which(name):
            return "/usr/bin/chromium" if name == "chromium" else None

        with patch("shutil.which", side_effect=which):
            assert find_chromium_executable() == "/usr/bin/chromium"

    def test_raises_if_not_installed(self):
        with patch("shutil.which", return_value=None), pytest.raises(FileNotFoundError):
            find_chromium_executable()


class TestChromiumBrowserController:
    def test_start_opens_dashboard_in_kiosk_mode(self, home):
        with (
            patch.object(
                chromiumbrowsercontroller, "find_chromium_executable", return_value="chromium"
            ),
            patch("subprocess.Popen") as popen,
        ):
            ChromiumBrowserController("token123").start()

        args = popen.call_args.args[0]
        assert args[0] == "chromium"
        assert "--kiosk" in args
        assert args[-1] == "https://dashboard.blaulichtsms.net/#/login?token=token123"
        assert popen.call_args.kwargs["stdout"] == subprocess.DEVNULL

    def test_is_alive_and_terminate_use_the_process(self, home):
        controller = ChromiumBrowserController("token")
        with (
            patch.object(
                chromiumbrowsercontroller, "find_chromium_executable", return_value="chromium"
            ),
            patch("subprocess.Popen") as popen,
        ):
            controller.start()
        process = popen.return_value

        process.poll.return_value = None
        assert controller.is_alive() is True
        process.poll.return_value = 0
        assert controller.is_alive() is False

        controller.terminate()
        process.terminate.assert_called_once()

    def test_delete_crash_exit_resets_exit_type(self, home):
        preferences = home / ".config" / "chromium" / "Default" / "Preferences"
        preferences.parent.mkdir(parents=True)
        preferences.write_text('{"profile":{"exit_type":"Crashed","name":"x"}}\n')

        ChromiumBrowserController("token")._delete_crash_exit()

        assert preferences.read_text() == '{"profile":{"exit_type":"Normal","name":"x"}}\n'

    def test_delete_crash_exit_ignores_missing_preferences(self, home):
        ChromiumBrowserController("token")._delete_crash_exit()
