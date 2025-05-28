# Import the unittest module for creating and running unit tests
import unittest
# Import patch and MagicMock for mocking objects and functions
from unittest.mock import patch, MagicMock
# Import logging module to control log output during tests
import logging
# Import the middleware_service module to be tested
import middleware_service

# Define a test case class inheriting from unittest.TestCase
class TestMiddlewareService(unittest.TestCase):
    # setUp runs before each test method
    def setUp(self):
        # Disable logging to avoid cluttering test output
        logging.disable(logging.CRITICAL)
        # Create a new MiddlewareService instance for testing
        self.service = middleware_service.MiddlewareService()

    # tearDown runs after each test method
    def tearDown(self):
        # Re-enable logging after tests
        logging.disable(logging.NOTSET)

    # Test that poll_hvac_status sets hvac_active to True for "active" status
    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_active(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "active"}
        mock_get.return_value.raise_for_status = lambda: None
        self.service.poll_hvac_status("room1")
        self.assertTrue(self.service.hvac_active["room1"])

    # Test that poll_hvac_status sets hvac_active to False for "inactive" status
    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_inactive(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "inactive"}
        mock_get.return_value.raise_for_status = lambda: None
        self.service.poll_hvac_status("room2")
        self.assertFalse(self.service.hvac_active["room2"])

    # Test that poll_hvac_status handles request exceptions gracefully
    @patch('middleware_service.requests.get', side_effect=Exception('API Down'))
    def test_poll_hvac_status_api_down(self, mock_get):
        # The method should handle the exception internally and not raise
        try:
            self.service.poll_hvac_status("room3")
        except Exception:
            self.fail("poll_hvac_status raised Exception unexpectedly!")

    # Test that send_hvac_command sends the correct activate command
    @patch('middleware_service.requests.post')
    def test_send_hvac_command_activate(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.text = "ok"
        self.service.send_hvac_command("room1", True)
        mock_post.assert_called_once_with(
            f"{middleware_service.Legacy_API_Base}/room1/command",
            json={"command": "activate"},
            timeout=2,
            auth=middleware_service.AUTH
        )

    # Test that send_hvac_command sends the correct deactivate command
    @patch('middleware_service.requests.post')
    def test_send_hvac_command_deactivate(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.text = "ok"
        self.service.send_hvac_command("room2", False)
        mock_post.assert_called_once_with(
            f"{middleware_service.Legacy_API_Base}/room2/command",
            json={"command": "deactivate"},
            timeout=2,
            auth=middleware_service.AUTH
        )

    # Test that on_message correctly sets temperature for valid input
    def test_on_message_valid_temperature(self):
        msg = MagicMock()
        msg.topic = "building/room1/temperature"
        msg.payload.decode.return_value = "31.5"
        self.service.on_message(None, None, msg)
        self.assertEqual(self.service.temperatures["room1"], 31.5)

    # Test that on_message does not update temperature for invalid input
    def test_on_message_invalid_temperature(self):
        msg = MagicMock()
        msg.topic = "building/room2/temperature"
        msg.payload.decode.return_value = "not_a_number"
        self.service.temperatures["room2"] = 22.0
        self.service.on_message(None, None, msg)
        self.assertEqual(self.service.temperatures["room2"], 22.0)

    # --- EDGE CASE TESTS ---

    # Test poll_hvac_status with an API response missing the "status" key
    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_no_status_in_response(self, mock_get):
        mock_get.return_value.json.return_value = {}
        mock_get.return_value.raise_for_status = lambda: None
        self.service.poll_hvac_status("room4")
        # Should default to inactive (False) or None, depending on implementation
        self.assertIn(self.service.hvac_active["room4"], (False, None))

    # Test poll_hvac_status with a status string not recognized
    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_unexpected_status_string(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "weirdvalue"}
        mock_get.return_value.raise_for_status = lambda: None
        self.service.poll_hvac_status("room5")
        self.assertIn(self.service.hvac_active["room5"], (False, None))

    # Test send_hvac_command handles request exceptions gracefully
    @patch('middleware_service.requests.post', side_effect=Exception('API Down'))
    def test_send_hvac_command_api_down(self, mock_post):
        try:
            self.service.send_hvac_command("room1", True)
        except Exception:
            self.fail("send_hvac_command raised Exception unexpectedly!")

    # Test on_message does not update temperature for extreme out-of-range values
    def test_on_message_extreme_temperature(self):
        # Test lower and upper bounds
        for temp in ["-10", "100"]:
            msg = MagicMock()
            msg.topic = "building/room1/temperature"
            msg.payload.decode.return_value = temp
            # Set an initial value
            self.service.temperatures["room1"] = 15.0
            self.service.on_message(None, None, msg)
            # Should not update to invalid value
            self.assertEqual(self.service.temperatures["room1"], 15.0)

    # Test on_message with empty payload
    def test_on_message_empty_payload(self):
        msg = MagicMock()
        msg.topic = "building/room2/temperature"
        msg.payload.decode.return_value = ""
        self.service.temperatures["room2"] = 18.0
        self.service.on_message(None, None, msg)
        self.assertEqual(self.service.temperatures["room2"], 18.0)

    # Test on_message with an invalid topic
    def test_on_message_invalid_topic(self):
        msg = MagicMock()
        msg.topic = "invalidtopic"
        msg.payload.decode.return_value = "25"
        # Should not raise, and should not update any temperature
        try:
            self.service.on_message(None, None, msg)
        except Exception:
            self.fail("on_message raised Exception unexpectedly!")

    # Test the decision logic for activating HVAC based on temperature
    @patch.object(middleware_service.MiddlewareService, "send_hvac_command")
    def test_decision_logic_triggers_hvac(self, mock_send_cmd):
        # Set up temperatures for all rooms, with one above 30°C
        self.service.temperatures = {r: 28 for r in middleware_service.ROOMS}
        self.service.temperatures["room3"] = 31
        self.service.hvac_active = {r: False for r in middleware_service.ROOMS}
        # Simulate the main loop's HVAC logic
        for room, temp in self.service.temperatures.items():
            if temp > 30 and not self.service.hvac_active.get(room, False):
                self.service.send_hvac_command(room, True)
                self.service.hvac_active[room] = True
        mock_send_cmd.assert_any_call("room3", True)

    # Test the decision logic for deactivating HVAC based on temperature
    @patch.object(middleware_service.MiddlewareService, "send_hvac_command")
    def test_decision_logic_deactivates_hvac(self, mock_send_cmd):
        self.service.temperatures = {r: 25 for r in middleware_service.ROOMS}
        self.service.hvac_active = {r: True for r in middleware_service.ROOMS}
        for room, temp in self.service.temperatures.items():
            if temp <= 30 and self.service.hvac_active.get(room, False):
                self.service.send_hvac_command(room, False)
                self.service.hvac_active[room] = False
        for room in middleware_service.ROOMS:
            mock_send_cmd.assert_any_call(room, False)

    # --- ADDITIONAL EDGE CASES ---

    # Test on_message with a room not initialized in temperatures
    def test_on_message_room_not_in_temps(self):
        msg = MagicMock()
        msg.topic = "building/nonexistent/temperature"
        msg.payload.decode.return_value = "22"
        try:
            self.service.on_message(None, None, msg)
        except Exception:
            self.fail("on_message raised Exception unexpectedly!")

    # Test poll_hvac_status with a room not initialized in hvac_active
    @patch('middleware_service.requests.get')
    def test_poll_hvac_status_room_not_in_hvac_active(self, mock_get):
        mock_get.return_value.json.return_value = {"status": "active"}
        mock_get.return_value.raise_for_status = lambda: None
        # Remove the room first if present
        if "roomX" in self.service.hvac_active:
            del self.service.hvac_active["roomX"]
        self.service.poll_hvac_status("roomX")
        self.assertTrue(self.service.hvac_active["roomX"])

    # Test send_hvac_command with a room not initialized in api_error
    @patch('middleware_service.requests.post')
    def test_send_hvac_command_room_not_in_api_error(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.text = "ok"
        if "roomY" in self.service.api_error:
            del self.service.api_error["roomY"]
        self.service.send_hvac_command("roomY", True)
        mock_post.assert_called_once_with(
            f"{middleware_service.Legacy_API_Base}/roomY/command",
            json={"command": "activate"},
            timeout=2,
            auth=middleware_service.AUTH
        )

# Standard boilerplate to run the tests if this script is executed directly
if __name__ == "__main__":
    unittest.main()
