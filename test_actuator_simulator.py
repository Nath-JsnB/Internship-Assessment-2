# Import the unittest module for creating and running unit tests
import unittest
# Import patch and MagicMock for mocking objects and functions
from unittest.mock import patch, MagicMock
# Import the sensor_simulator module to be tested
import sensor_simulator

# Define a test case class inheriting from unittest.TestCase
class TestSensorSimulator(unittest.TestCase):

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_temperature_publish_range(self, mock_mqtt_client):
        # Create a mock client instance
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch time.sleep to skip sleeping, and random.uniform to always return 25
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 25):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # Check that publish was called once per room (5 times)
        calls = client_instance.publish.call_args_list
        self.assertEqual(len(calls), 5)
        for call in calls:
            topic, payload = call[0]
            self.assertTrue(topic.startswith("building/room"))
            self.assertEqual(payload, "25")

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_temperature_publish_lower_bound(self, mock_mqtt_client):
        # Create a mock client instance
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch time.sleep to skip sleeping, and random.uniform to always return 0
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 0):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # Verify all published payloads are "0"
        for call in client_instance.publish.call_args_list:
            _, payload = call[0]
            self.assertEqual(payload, "0")

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_temperature_publish_upper_bound(self, mock_mqtt_client):
        # Create a mock client instance
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch time.sleep to skip sleeping, and random.uniform to always return 50
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 50):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # Verify all published payloads are "50"
        for call in client_instance.publish.call_args_list:
            _, payload = call[0]
            self.assertEqual(payload, "50")

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_temperature_publish_negative_temperature(self, mock_mqtt_client):
        # Simulate negative temperature (outside expected range)
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch time.sleep to skip sleeping, and random.uniform to always return -10
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: -10):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # Verify all published payloads are "-10"
        for call in client_instance.publish.call_args_list:
            _, payload = call[0]
            self.assertEqual(payload, "-10")

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_temperature_publish_above_max_temperature(self, mock_mqtt_client):
        # Simulate temperature above maximum (outside expected range)
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch time.sleep to skip sleeping, and random.uniform to always return 100
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 100):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # Verify all published payloads are "100"
        for call in client_instance.publish.call_args_list:
            _, payload = call[0]
            self.assertEqual(payload, "100")

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_publish_failure_handling(self, mock_mqtt_client):
        # Simulate publish raising an exception (e.g., MQTT disconnected)
        client_instance = MagicMock()
        client_instance.publish.side_effect = Exception("MQTT publish error")
        mock_mqtt_client.return_value = client_instance

        # Patch time.sleep and random.uniform as before
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 25):
            # The simulator may not handle the exception, so wrap in assertRaises
            with self.assertRaises(Exception) as context:
                sensor_simulator.main()
            self.assertIn("MQTT publish error", str(context.exception))

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_no_rooms(self, mock_mqtt_client):
        # Simulate no rooms in the ROOMS list
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch ROOMS to [], time.sleep, and random.uniform
        with patch('sensor_simulator.ROOMS', []), \
             patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 25):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # No publish calls should occur
        self.assertEqual(client_instance.publish.call_count, 0)

    # Patch the mqtt.Client class in sensor_simulator for this test
    @patch('sensor_simulator.mqtt.Client')
    def test_non_string_room_names(self, mock_mqtt_client):
        # Simulate room names that are not strings
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance

        # Patch ROOMS to [123, None], time.sleep, and random.uniform
        with patch('sensor_simulator.ROOMS', [123, None]), \
             patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 25):
            # Call main and expect the StopIteration to break the loop after one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))

        # Verify topics are built using non-string room names
        calls = client_instance.publish.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], "building/123/temperature")
        self.assertEqual(calls[1][0][0], "building/None/temperature")

# Standard boilerplate to run the test when the script is executed directly
if __name__ == '__main__':
    unittest.main()
