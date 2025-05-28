import unittest
from unittest.mock import MagicMock
import actuator_simulator

class TestActuatorSimulator(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.userdata = None

    def test_on_connect_subscribes(self):
        actuator_simulator.on_connect(self.client, self.userdata, None, 0)
        self.assertEqual(self.client.subscribe.call_count, 5)
        topics = [call[0][0] for call in self.client.subscribe.call_args_list]
        for room in actuator_simulator.ROOMS:
            self.assertIn(f"building/{room}/hvac/cmd", topics)

    def test_on_message_valid_command(self):
        class Msg:
            def __init__(self, topic, payload):
                self.topic = topic
                self.payload = payload.encode()
        with patch('builtins.print') as mock_print:
            msg = Msg("building/room2/hvac/cmd", "ON")
            actuator_simulator.on_message(self.client, self.userdata, msg)
            mock_print.assert_any_call("Room room2: HVAC command received: ON")

    def test_on_message_invalid_command(self):
        class Msg:
            def __init__(self, topic, payload):
                self.topic = topic
                self.payload = payload.encode()
        with patch('builtins.print') as mock_print:
            msg = Msg("building/room3/hvac/cmd", "INVALID")
            actuator_simulator.on_message(self.client, self.userdata, msg)
            mock_print.assert_any_call("Room room3: Invalid command received: INVALID")

if __name__ == '__main__':
    unittest.main()