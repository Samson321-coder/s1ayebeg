import unittest

import strings
from location_options import CITY_OPTIONS, NEIGHBORHOOD_OPTIONS, build_location_string, get_city_keyboard, get_neighborhood_keyboard


class LocationOptionsTests(unittest.TestCase):
    def test_city_options_includes_expected_cities(self):
        self.assertIn("አዲስ አበባ/ዙሪያ", CITY_OPTIONS)
        self.assertIn("ዲላ/አካባቢዋ", CITY_OPTIONS)
        self.assertGreaterEqual(len(CITY_OPTIONS), 2)

    def test_neighborhood_keyboard_is_available(self):
        self.assertGreater(len(NEIGHBORHOOD_OPTIONS), 0)
        keyboard = get_neighborhood_keyboard()
        self.assertTrue(keyboard)
        self.assertEqual(keyboard[0][0], NEIGHBORHOOD_OPTIONS[0])

    def test_location_string_is_built_from_city_and_neighborhood(self):
        self.assertEqual(build_location_string("Dilla", "አዲስ ሰፈር"), "Dilla - አዲስ ሰፈር")

    def test_location_prompts_direct_users_to_select_from_buttons(self):
        self.assertIn("ይምረጡ", strings.OWNER_ASK_CITY)
        self.assertIn("ይምረጡ", strings.OWNER_ASK_LOCATION)
        self.assertIn("ይምረጡ", strings.SEEKER_ASK_CITY)
        self.assertIn("ይምረጡ", strings.SEEKER_ASK_SEARCH)


if __name__ == "__main__":
    unittest.main()
