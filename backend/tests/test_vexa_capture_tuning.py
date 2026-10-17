"""Launch configuration checks; no upstream process, audio models, or Docker."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "deploy/vexa/voice_capture_config.py"
spec = importlib.util.spec_from_file_location("meetpilot_voice_capture_config", MODULE_PATH)
capture_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture_config)


class CaptureTuningTests(unittest.TestCase):
    def test_short_wake_defaults_keep_two_pass_confirmation(self):
        tuning, warnings = capture_config.capture_tuning({})
        self.assertEqual(tuning["BOT_SPEAKER_MIN_AUDIO_SEC"], "0.4")
        self.assertEqual(tuning["BOT_SPEAKER_SUBMIT_INTERVAL_SEC"], "1.0")
        self.assertEqual(tuning["BOT_SPEAKER_IDLE_TIMEOUT_SEC"], "1.5")
        self.assertEqual(tuning["BOT_SPEAKER_CONFIRM_THRESHOLD"], "2")
        self.assertEqual(warnings, [])

    def test_runtime_overrides_mounted_config_and_config_overrides_defaults(self):
        tuning, warnings = capture_config.capture_tuning(
            {"BOT_SPEAKER_MIN_AUDIO_SEC": "0.8"},
            {"BOT_SPEAKER_MIN_AUDIO_SEC": "0.6", "BOT_SPEAKER_IDLE_TIMEOUT_SEC": "2"})
        self.assertEqual(tuning["BOT_SPEAKER_MIN_AUDIO_SEC"], "0.8")
        self.assertEqual(tuning["BOT_SPEAKER_IDLE_TIMEOUT_SEC"], "2.0")
        self.assertEqual(warnings, [])

    def test_bad_values_do_not_disable_confirmation_or_create_busy_loops(self):
        tuning, warnings = capture_config.capture_tuning({
            "BOT_SPEAKER_MIN_AUDIO_SEC": "NaN",
            "BOT_SPEAKER_SUBMIT_INTERVAL_SEC": "0.01",
            "BOT_SPEAKER_IDLE_TIMEOUT_SEC": "inf",
            "BOT_SPEAKER_CONFIRM_THRESHOLD": "1",
            "BOT_SPEAKER_MAX_BUFFER_SEC": "900",
            "TTS_API_TOKEN": "secret-value",
        })
        self.assertEqual(tuning, capture_config.capture_tuning({})[0])
        self.assertEqual(len(warnings), 5)
        self.assertNotIn("TTS_API_TOKEN", tuning)
        self.assertNotIn("secret-value", " ".join(warnings))
        self.assertEqual(capture_config.capture_tuning({"BOT_SPEAKER_CONFIRM_THRESHOLD": "2.5"})[0]
                         ["BOT_SPEAKER_CONFIRM_THRESHOLD"], "2")

    def test_image_support_is_checked_against_its_own_compiled_build(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(capture_config.build_advertises_capture_tuning(root))
            (root / "dist").mkdir()
            (root / "dist/config.js").write_text(" ".join(capture_config.CAPTURE_DEFAULTS), encoding="utf-8")
            self.assertTrue(capture_config.build_advertises_capture_tuning(root))

    def test_unsupported_build_warns_and_does_not_claim_tuning_was_applied(self):
        env, reports = {}, []
        with TemporaryDirectory() as directory:
            supported = capture_config.configure_capture_environment(env, {}, directory, report=reports.append)
        self.assertFalse(supported)
        self.assertEqual(env["BOT_SPEAKER_IDLE_TIMEOUT_SEC"], "1.5")
        self.assertTrue(any("not verified" in message for message in reports))
