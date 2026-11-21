import subprocess
import unittest
from unittest.mock import Mock, patch

from internal.core.src import audio_router
from internal.core.src.audio_router import AudioDeviceItem, AudioRouter


class VirtualOutputDetectionTests(unittest.TestCase):
    def test_recognizes_cable_and_voxcraft_virtual_output_names(self):
        self.assertTrue(audio_router._is_virtual_output_name(
            "CABLE Input (VB-Audio Virtual Cable)"
        ))
        self.assertTrue(audio_router._is_virtual_output_name("VoxCraft_Virtual_Output"))

    def test_does_not_classify_physical_speakers_as_virtual(self):
        self.assertFalse(audio_router._is_virtual_output_name(
            "Speakers (Realtek(R) Audio)"
        ))

    def test_start_rejects_physical_output_before_opening_audio(self):
        router = AudioRouter(Mock())
        with patch.object(AudioRouter, "is_virtual_output", return_value=False):
            started, message = router.start(in_idx=0, out_idx=1)

        self.assertFalse(started)
        self.assertIn("saída virtual", message)
        self.assertFalse(router.running)


class LinuxVirtualOutputSetupTests(unittest.TestCase):
    def setUp(self):
        self.router = AudioRouter(Mock())

    def test_non_linux_platform_does_not_attempt_to_configure_sink(self):
        with patch.object(audio_router.sys, "platform", "win32"):
            result = self.router.ensure_linux_virtual_output()

        self.assertEqual(
            result,
            {
                "supported": False,
                "available": False,
                "created": False,
                "canRetry": False,
                "message": None,
            },
        )

    def test_reuses_an_existing_virtual_output(self):
        virtual_output = AudioDeviceItem(
            4, "Existing Virtual Output", "PulseAudio", 0, 2, 48000
        )
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                self.router, "_find_voxcraft_virtual_sink_module", return_value=None
            ),
            patch.object(
                AudioRouter, "refresh_backend", return_value=([], [virtual_output])
            ),
            patch.object(audio_router, "_linux_sound_endpoints") as endpoints,
            patch.object(audio_router, "_run_pactl") as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertTrue(result["available"])
        self.assertFalse(result["created"])
        endpoints.assert_not_called()
        run_pactl.assert_not_called()

    def test_creates_named_sink_and_refreshes_portaudio_devices(self):
        virtual_output = AudioDeviceItem(
            7, "VoxCraft_Virtual_Output", "PulseAudio", 0, 2, 48000
        )
        load_result = subprocess.CompletedProcess(
            args=["pactl", "load-module"],
            returncode=0,
            stdout="42\n",
            stderr="",
        )
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                self.router, "_find_voxcraft_virtual_sink_module", return_value=None
            ),
            patch.object(
                AudioRouter,
                "refresh_backend",
                side_effect=[([], []), ([], [virtual_output])],
            ),
            patch.object(audio_router, "_linux_sound_endpoints", return_value=[]),
            patch.object(audio_router, "_run_pactl", return_value=load_result) as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertTrue(result["supported"])
        self.assertTrue(result["available"])
        self.assertTrue(result["created"])
        self.assertFalse(result["canRetry"])
        self.assertEqual(self.router._virtual_output_module_id, "42")
        run_pactl.assert_called_once_with(
            [
                "load-module",
                "module-null-sink",
                "sink_name=voxcraft_virtual_output",
                "sink_properties=device.description=VoxCraft_Virtual_Output",
            ],
            timeout=5,
        )

    def test_does_not_create_duplicate_when_server_sink_is_not_exposed(self):
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                self.router, "_find_voxcraft_virtual_sink_module", return_value=None
            ),
            patch.object(AudioRouter, "refresh_backend", return_value=([], [])),
            patch.object(
                audio_router,
                "_linux_sound_endpoints",
                return_value=[
                    {
                        "name": "custom_sink",
                        "description": "VoxCraft Virtual Output",
                    }
                ],
            ),
            patch.object(audio_router, "_run_pactl") as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertFalse(result["available"])
        self.assertFalse(result["created"])
        self.assertFalse(result["canRetry"])
        self.assertIn("PortAudio", result["message"])
        run_pactl.assert_not_called()

    def test_releases_only_the_module_owned_by_the_router(self):
        self.router._virtual_output_module_id = "42"
        with patch.object(audio_router, "_run_pactl") as run_pactl:
            self.router.release_linux_virtual_output()

        run_pactl.assert_called_once_with(["unload-module", "42"])
        self.assertIsNone(self.router._virtual_output_module_id)


if __name__ == "__main__":
    unittest.main()
