import unittest
from unittest.mock import patch, MagicMock
import sensor_simulator

class TestSensorSimulator(unittest.TestCase):
    @patch('sensor_simulator.mqtt.Client')
    def test_temperature_publish_range(self, mock_mqtt_client):
        client_instance = MagicMock()
        mock_mqtt_client.return_value = client_instance
        # Patch time.sleep to avoid delay
        with patch('sensor_simulator.time.sleep', return_value=None), \
             patch('sensor_simulator.random.uniform', side_effect=lambda a, b: 25):
            # Only run one iteration
            with self.assertRaises(StopIteration):
                next(iter([sensor_simulator.main()]))
        # Check publish calls
        calls = client_instance.publish.call_args_list
        self.assertEqual(len(calls), 5)
        for call in calls:
            topic, payload = call[0]
            self.assertTrue(topic.startswith("building/room"))
            self.assertEqual(payload, "25")

if __name__ == '__main__':
    unittest.main()