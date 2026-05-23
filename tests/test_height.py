import unittest

from src.height import choose_building_height


class HeightRulesTest(unittest.TestCase):
    def test_uses_height_first(self):
        result = choose_building_height({"HEIGHT": 12, "GRND_FLR": 99}, 3.0, 6.0)
        self.assertEqual(result.value, 12)
        self.assertEqual(result.source, "HEIGHT")

    def test_floor_fallback(self):
        result = choose_building_height({"HEIGHT": 0, "GRND_FLR": 4}, 3.0, 6.0)
        self.assertEqual(result.value, 12)
        self.assertEqual(result.source, "floor_fallback")

    def test_default_fallback(self):
        result = choose_building_height({}, 3.0, 6.0)
        self.assertEqual(result.value, 6)
        self.assertEqual(result.source, "default")

    def test_clamps_height(self):
        result = choose_building_height({"HEIGHT": 9999}, 3.0, 6.0)
        self.assertEqual(result.value, 300)

    def test_custom_height_field(self):
        result = choose_building_height({"MY_H": 8, "HEIGHT": 0}, 3.0, 6.0, height_fields=("MY_H",))
        self.assertEqual(result.value, 8)
        self.assertEqual(result.source, "HEIGHT")

    def test_custom_floor_field(self):
        result = choose_building_height({"MY_FLOORS": 5}, 3.0, 6.0, floor_fields=("MY_FLOORS",))
        self.assertEqual(result.value, 15)
        self.assertEqual(result.source, "floor_fallback")


if __name__ == "__main__":
    unittest.main()
