from .errors import RequestError


def parse_id(value):
    if type(value) is not int or not 0 < value <= 2147483647:
        raise RequestError("Selecciona una ubicación y un producto válidos.")
    return value
