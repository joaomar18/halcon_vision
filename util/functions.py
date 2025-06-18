###########EXTERNAL IMPORTS############

#######################################

#############LOCAL IMPORTS#############

#######################################


def round_to_nearest_10(number: int) -> int:
    """
    Rounds an integer up to the nearest multiple of 10.

    This function takes an integer and returns the next multiple of 10
    that is greater than or equal to the input number. If the number is
    already a multiple of 10, it returns the number PLUS 10.

    Args:
        number (int): The integer value to round up.

    Returns:
        int: The input number rounded up to the nearest multiple of 10,
             or the input number plus 10 if it's already a multiple of 10.
    """

    new_number = number

    if number % 10 != 0:
        padding = 10 - (number % 10)
        new_number = number + padding

    if new_number == number:
        new_number = number + 10

    return new_number


def is_float(value: str) -> bool:
    """
    Determine if a value represents or can be converted to a floating-point number.

    This function checks if a value is a float or a string representation of a float
    by examining if it contains a decimal separator (either '.' or ',').

    Args:
        value: The value to check, can be of any type.

    Returns:
        bool: True if the value is a float or appears to represent a float,
              False otherwise.
    """

    if isinstance(value, float):
        return True
    elif isinstance(value, str) and ("." in value or "," in value):
        return True

    return False
