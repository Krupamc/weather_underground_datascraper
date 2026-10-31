# Conversions!
import re
def number(value):
    if value is None:
        return None

    text = (
        str(value)
        .replace("\xa0", " ")
        .replace("−", "-")
        .strip()
    )

    match = re.match(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text)

    return float(match.group()) if match else None

def make_float(not_float):
    if not_float is None:
        return None
    
    try:
        return float(str(not_float).strip())
    
    except (ValueError, TypeError):
        return None


def f_to_c(temp_F):
    temp_F = number(temp_F)

    if temp_F is None:
        return None

    return round((temp_F - 32) * 5 / 9, 2)

def c_to_f(temp_C: float):

    if temp_C is None:
        return None
    
    f = (temp_C * 9/5) + 32
    return round(f, 2)


def mph_to_knots(wind_speed_mph: float):

    if wind_speed_mph is None:
        return None
    
    return round((wind_speed_mph / 1.15078), 2)

def knots_to_mph(wind_speed_knots: float):

    if wind_speed_knots is None:
        return None

    return round((wind_speed_knots * 1.15078), 2)

def mph_to_ms(value):
    value = number(value)
    return None if value is None else round(value * 0.44704, 2)


def inhg_to_hpa(value):
    value = number(value)
    return None if value is None else round(value * 33.8638866667, 2)


def inches_to_mm(value):
    value = number(value)
    return None if value is None else round(value * 25.4, 2)
