def is_leap(year):
    if (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0):
        return True
    return False


def day_of_year(day, month, year):
    days_in_month = [31, 28, 31, 30, 31, 30,
                     31, 31, 30, 31, 30, 31]

    if is_leap(year):
        days_in_month[1] = 29

    day_of_years = sum(days_in_month[:month - 1]) + day
    return day_of_years


print(day_of_year(29, 2, 2024))  # 60 (leap year)

def day_in_year(year):
    return 366 if is_leap(year) else 365


def date_diff(date1, date2):
    d1, m1, y1 = map(int, date1.split("-"))
    d2, m2, y2 = map(int, date2.split("-"))

    if y1 == y2:
        return day_of_year(d2, m2, y2) - day_of_year(d1, m1, y1) + 1

    days = day_in_year(y1) - day_of_year(d1, m1, y1) + 1

    for year in range(y1 + 1, y2):
        days += day_in_year(year)

    days += day_of_year(d2, m2, y2)

    return days


print(date_diff("25-12-1999", "9-3-2000"))  # 76
