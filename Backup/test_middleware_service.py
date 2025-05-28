import unittest
from unittest.mock import patch, MagicMock, call
import logging

import middleware_service

class TestMiddlewareService(unittest.TestCase):
    def setUp(self):
        # Silence logging during tests
        logging.disable(logging.CRITICAL)
        self.service = middleware_service.MiddlewareService()

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_active(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "active"}
        mock_get.return_value.raise_for_status = lambda: None
        self.service.poll_hvac_status()
        self.assertTrue(self.service.hvac_active)

    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_inactive(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "inactive"}
        mock_get.return_value.raise_for_status = lambda: None
        self.service.poll_hvac_status()
        self.assertFalse(self.service.hvac_active)

    @patch('middleware_service.requests.get', side_effect=Exception('API Down'))
    def test_poll_hvac_status_api_down(self, mock_get):
        # Should log error and not throw
        self.service.hvac_active = None
        self.service.poll_hvac_status()
        self.assertIsNone(self.service.hvac_active)

    @patch('middleware_service.requests.post')
    def test_send_hvac_command_activate(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.text = "ok"
        self.service.send_hvac_command(True)
        mock_post.assert_called_once_with(
            f"{middleware_service.LEGACY_API_BASE}/command",
            json={"command": "activate"},
            timeout=5,
        )

    @patch('middleware_service.requests.post')
    def test_send_hvac_command_deactivate(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.text = "ok"
        self.service.send_hvac_command(False)
        mock_post.assert_called_once_with(
            f"{middleware_service.LEGACY_API_BASE}/command",
            json={"command": "deactivate"},
            timeout=5,
        )

    def test_on_message_valid_temperature(self):
        msg = MagicMock()
        msg.topic = "building/room1/temperature"
        msg.payload.decode.return_value = "31.5"
        self.service.on_message(None, None, msg)
        self.assertEqual(self.service.temperatures["room1"], 31.5)

    def test_on_message_invalid_temperature(self):
        msg = MagicMock()
        msg.topic = "building/room2/temperature"
        msg.payload.decode.return_value = "not_a_number"
        # Should not raise
        self.service.temperatures["room2"] = 22.0
        self.service.on_message(None, None, msg)
        # Temperature should not change
        self.assertEqual(self.service.temperatures["room2"], 22.0)

    @patch.object(middleware_service.MiddlewareService, "send_hvac_command")
    def test_decision_logic_triggers_hvac(self, mock_send_cmd):
        # Simulate one room above threshold
        self.service.temperatures = {r: 28 for r in middleware_service.ROOMS}
        self.service.temperatures["room3"] = 31
        self.service.hvac_active = False
        # Run one iteration of main logic
        any_above = any(t > 30 for t in self.service.temperatures.values())
        if any_above and self.service.hvac_active is not True:
            self.service.send_hvac_command(True)
            self.service.hvac_active = True
        mock_send_cmd.assert_called_once_with(True)

    @patch.object(middleware_service.MiddlewareService, "send_hvac_command")
    def test_decision_logic_deactivates_hvac(self, mock_send_cmd):
        # All rooms below threshold
        self.service.temperatures = {r: 25 for r in middleware_service.ROOMS}
        self.service.hvac_active = True
        any_above = any(t > 30 for t in self.service.temperatures.values())
        if not any_above and self.service.hvac_active is not False:
            self.service.send_hvac_command(False)
            self.service.hvac_active = False
        mock_send_cmd.assert_called_once_with(False)

if __name__ == "__main__":
    unittest.main()