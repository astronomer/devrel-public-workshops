import unittest

from include.custom_operator import MyBasicMathOperator


class TestMyBasicMathOperator(unittest.TestCase):

    def test_addition(self):
        operator = MyBasicMathOperator(
            task_id="basic_math_op", first_number=2, second_number=3, operation="+"
        )
        result = operator.execute(None)
        self.assertEqual(result, 5)

    def test_subtraction(self):
        operator = MyBasicMathOperator(
            task_id="basic_math_op", first_number=5, second_number=3, operation="-"
        )
        result = operator.execute(None)
        self.assertEqual(result, 2)

    def test_multiplication(self):
        operator = MyBasicMathOperator(
            task_id="basic_math_op", first_number=4, second_number=5, operation="*"
        )
        result = operator.execute(None)
        self.assertEqual(result, 20)

    def test_division(self):
        operator = MyBasicMathOperator(
            task_id="basic_math_op", first_number=10, second_number=2, operation="/"
        )
        result = operator.execute(None)
        self.assertEqual(result, 5)

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            operator = MyBasicMathOperator(
                task_id="basic_math_op", first_number=10, second_number=0, operation="/"
            )
            operator.execute(None)

    def test_invalid_operation(self):
        with self.assertRaises(ValueError):
            operator = MyBasicMathOperator(
                task_id="basic_math_op", first_number=10, second_number=2, operation="^"
            )
            operator.execute(None)


if __name__ == "__main__":
    unittest.main()
