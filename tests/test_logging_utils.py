import io
import unittest
from contextlib import redirect_stdout

from daily_stock.logging_utils import log_message


class LoggingUtilsTests(unittest.TestCase):
    def test_log_message_preserves_message_and_end(self):
        output = io.StringIO()

        with redirect_stdout(output):
            log_message("hello", end=" ")
            log_message("world")

        self.assertEqual(output.getvalue(), "hello world\n")


if __name__ == "__main__":
    unittest.main()
