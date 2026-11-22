import subprocess
import unittest
from unittest.mock import Mock, call, patch

from internal.core.src import audio_router
from internal.core.src.audio_router import AudioDeviceItem, AudioRouter


class VirtualOutputDetectionTests(unittest.TestCase):
    def test_recognizes_cable_and_virtual_output_names(self):
        self.assertTrue(audio_router._is_virtual_output_name(
            "CABLE Input (VB-Audio Virtual Cable)"
        ))
        self.assertTrue(audio_router._is_virtual_output_name("Generic Virtual Output"))

    def test_does_not_classify_physical_speakers_as_virtual(self):
        self.assertFalse(audio_router._is_virtual_output_name(
            "Speakers (Realtek(R) Audio)"
        ))

    def test_linux_virtual_microphone_uses_only_cable_input(self):
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                audio_router.sd,
                "query_devices",
                return_value={
                    "name": "Other_Virtual_Output",
                    "max_output_channels": 2,
                },
            ),
        ):
            self.assertFalse(AudioRouter.is_virtual_output(4))

        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                audio_router.sd,
                "query_devices",
                return_value={
                    "name": "CABLE Input",
                    "max_output_channels": 2,
                },
            ),
        ):
            self.assertTrue(AudioRouter.is_virtual_output(4))

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
                "microphoneAvailable": None,
                "created": False,
                "canRetry": False,
                "message": None,
            },
        )

    def test_reuses_existing_output_and_creates_named_microphone_source(self):
        virtual_output = AudioDeviceItem(
            4, "CABLE Input", "PulseAudio", 0, 2, 48000
        )
        source_lists = iter([
            [{"name": "cable_input.monitor"}],
            [
                {"name": "cable_input.monitor"},
                {"name": "cable_output", "description": "CABLE Output"},
            ],
        ])
        load_result = subprocess.CompletedProcess(
            args=["pactl", "load-module"],
            returncode=0,
            stdout="43\n",
            stderr="",
        )
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                AudioRouter, "refresh_backend", return_value=([], [virtual_output])
            ),
            patch.object(
                audio_router,
                "_linux_sound_endpoints",
                side_effect=lambda kind: (
                    [{
                        "name": "cable_input",
                        "description": "CABLE Input",
                    }]
                    if kind == "sinks"
                    else next(source_lists)
                ),
            ),
            patch.object(
                audio_router, "_run_pactl", return_value=load_result
            ) as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertTrue(result["available"])
        self.assertTrue(result["microphoneAvailable"])
        self.assertFalse(result["created"])
        self.assertTrue(result["microphoneCreated"])
        self.assertIsNone(self.router._virtual_output_module_id)
        self.assertEqual(self.router._virtual_microphone_module_id, "43")
        run_pactl.assert_called_once_with(
            [
                "load-module",
                "module-remap-source",
                "source_name=cable_output",
                "master=cable_input.monitor",
                '''source_properties="device.description='CABLE Output'"''',
            ],
            timeout=5,
        )

    def test_creates_named_sink_and_microphone_and_refreshes_devices(self):
        virtual_output = AudioDeviceItem(
            7, "CABLE Input", "PulseAudio", 0, 2, 48000
        )
        sink_load_result = subprocess.CompletedProcess(
            args=["pactl", "load-module"],
            returncode=0,
            stdout="42\n",
            stderr="",
        )
        microphone_load_result = subprocess.CompletedProcess(
            args=["pactl", "load-module"],
            returncode=0,
            stdout="43\n",
            stderr="",
        )
        source_lists = iter([
            [{"name": "cable_input.monitor"}],
            [
                {"name": "cable_input.monitor"},
                {"name": "cable_output", "description": "CABLE Output"},
            ],
        ])
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                AudioRouter,
                "refresh_backend",
                side_effect=[([], []), ([], [virtual_output])],
            ),
            patch.object(
                audio_router,
                "_linux_sound_endpoints",
                side_effect=lambda kind: (
                    []
                    if kind == "sinks" and self.router._virtual_output_module_id is None
                    else [{
                        "name": "cable_input",
                        "description": "CABLE Input",
                    }]
                    if kind == "sinks"
                    else next(source_lists)
                ),
            ),
            patch.object(
                audio_router,
                "_run_pactl",
                side_effect=[sink_load_result, microphone_load_result],
            ) as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertTrue(result["supported"])
        self.assertTrue(result["available"])
        self.assertTrue(result["microphoneAvailable"])
        self.assertTrue(result["created"])
        self.assertTrue(result["microphoneCreated"])
        self.assertFalse(result["canRetry"])
        self.assertEqual(self.router._virtual_output_module_id, "42")
        self.assertEqual(self.router._virtual_microphone_module_id, "43")
        self.assertEqual(run_pactl.call_args_list, [
            call(
                [
                    "load-module",
                    "module-null-sink",
                    "sink_name=cable_input",
                    '''sink_properties="device.description='CABLE Input'"''',
                ],
                timeout=5,
            ),
            call(
                [
                    "load-module",
                    "module-remap-source",
                    "source_name=cable_output",
                    "master=cable_input.monitor",
                    '''source_properties="device.description='CABLE Output'"''',
                ],
                timeout=5,
            ),
        ])

    def test_creates_own_route_instead_of_using_another_virtual_output(self):
        external_output = AudioDeviceItem(
            5, "Other_Virtual_Output", "PulseAudio", 0, 2, 48000
        )
        cable_input = AudioDeviceItem(
            7, "CABLE Input", "PulseAudio", 0, 2, 48000
        )
        sink_load_result = subprocess.CompletedProcess(
            args=["pactl", "load-module"],
            returncode=0,
            stdout="42\n",
            stderr="",
        )
        microphone_load_result = subprocess.CompletedProcess(
            args=["pactl", "load-module"],
            returncode=0,
            stdout="43\n",
            stderr="",
        )
        source_lists = iter([
            [{"name": "cable_input.monitor"}],
            [
                {"name": "cable_input.monitor"},
                {"name": "cable_output", "description": "CABLE Output"},
            ],
        ])

        def list_server_endpoints(kind):
            if kind == "sources":
                return next(source_lists)
            if self.router._virtual_output_module_id is None:
                return [{
                    "name": "other_virtual_output",
                    "description": "Other_Virtual_Output",
                }]
            return [
                {
                    "name": "other_virtual_output",
                    "description": "Other_Virtual_Output",
                },
                {
                    "name": "cable_input",
                    "description": "CABLE Input",
                },
            ]

        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                AudioRouter,
                "refresh_backend",
                side_effect=[
                    ([], [external_output]),
                    ([], [external_output, cable_input]),
                ],
            ),
            patch.object(
                audio_router,
                "_linux_sound_endpoints",
                side_effect=list_server_endpoints,
            ),
            patch.object(
                audio_router,
                "_run_pactl",
                side_effect=[sink_load_result, microphone_load_result],
            ) as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertTrue(result["available"])
        self.assertTrue(result["microphoneAvailable"])
        self.assertTrue(result["created"])
        self.assertTrue(result["microphoneCreated"])
        self.assertEqual(
            run_pactl.call_args_list[1],
            call(
                [
                    "load-module",
                    "module-remap-source",
                    "source_name=cable_output",
                    "master=cable_input.monitor",
                    '''source_properties="device.description='CABLE Output'"''',
                ],
                timeout=5,
            ),
        )

    def test_does_not_create_duplicate_when_server_sink_is_not_exposed(self):
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(AudioRouter, "refresh_backend", return_value=([], [])),
            patch.object(
                audio_router,
                "_linux_sound_endpoints",
                return_value=[
                    {
                        "name": "custom_sink",
                        "description": "CABLE Input",
                    }
                ],
            ),
            patch.object(audio_router, "_run_pactl") as run_pactl,
        ):
            result = self.router.ensure_linux_virtual_output()

        self.assertFalse(result["available"])
        self.assertFalse(result["microphoneAvailable"])
        self.assertFalse(result["created"])
        self.assertFalse(result["canRetry"])
        self.assertIn("PortAudio", result["message"])
        run_pactl.assert_not_called()

    def test_does_not_expose_own_virtual_microphone_as_input(self):
        microphone = AudioDeviceItem(
            2, "CABLE Output", "PulseAudio", 1, 0, 48000
        )
        physical = AudioDeviceItem(
            3, "USB Microphone", "PulseAudio", 1, 0, 48000
        )
        with (
            patch.object(audio_router.sys, "platform", "linux"),
            patch.object(
                audio_router,
                "_linux_sound_endpoints",
                return_value=[
                    {"name": "cable_output", "description": "CABLE Output"},
                    {"name": "usb_microphone", "description": "USB Microphone"},
                ],
            ),
        ):
            visible = audio_router._desktop_devices(
                [microphone, physical], is_input=True
            )

        self.assertEqual(visible, [physical])

    def test_releases_only_modules_owned_by_the_router(self):
        self.router._virtual_output_module_id = "42"
        self.router._virtual_microphone_module_id = "43"
        with patch.object(audio_router, "_run_pactl") as run_pactl:
            self.router.release_linux_virtual_output()

        self.assertEqual(
            run_pactl.call_args_list,
            [
                call(["unload-module", "43"]),
                call(["unload-module", "42"]),
            ],
        )
        self.assertIsNone(self.router._virtual_output_module_id)
        self.assertIsNone(self.router._virtual_microphone_module_id)



if __name__ == "__main__":
    unittest.main()
