import unittest
from unittest.mock import patch
from stepn.stepn_report import fetch_stepn_report
from sharedCode.commonPrice import TickerPrice

class TestStepnReport(unittest.TestCase):
    @patch('stepn.stepn_report.fetch_current_price')
    @patch('stepn.stepn_report.fetch_gstgmt_ratio_range')
    def test_fetch_stepn_report_basic_functionality(self, mock_ratio_range, mock_fetch_price):
        # Arrange
        # Mock the price fetching to return predetermined values
        mock_fetch_price.side_effect = [
            TickerPrice(source=1,symbol='GMT', low=0.5, high=1, last = 4,volume = 1, volume_quote= 5 ),  # GMT price
            TickerPrice(source=2,symbol='GST', low=0.1, high=1, last = 2,volume = 1, volume_quote= 5 )   # GST price
        ]
        mock_ratio_range.return_value = None  # No 24h range data for basic test

        # Act
        result = fetch_stepn_report(conn=None)
        result_str = str(result)

        # Assert
        self.assertIn('GMT', result_str)
        self.assertIn('GST', result_str)
        self.assertIn('GMT/GST', result_str)
        self.assertIn('4', result_str)  # GMT price
        self.assertIn('2', result_str)  # GST price
        self.assertIn('2.0', result_str)  # GMT/GST ratio (0.5/0.1)

if __name__ == '__main__':
    unittest.main()
