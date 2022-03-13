from dataclasses import dataclass
import arrow


@dataclass
class ShortID:
    """该 ID 由年份与自增数两部分组成，年份与自增数分别转 36 进制字符，不分大小写。"""

    year: int
    n: int

    def __str__(self) -> str:
        return str36(self.year, self.n)

    def next_id(self) -> str:
        this_year = arrow.now().year
        if this_year > self.year:
            return str36(this_year, 0)

        return str36(self.year, self.n + 1)


def first_id() -> str:
    fid = ShortID(year=arrow.now().year, n=0)
    return str(fid)


def parse_id(id_str: str) -> ShortID:
    """有“万年虫”问题，大概公元五万年时本算法会出错，当然，这个问题可以忽略。"""
    year = int(id_str[0:3], 36)  # 可以姑且认为年份总是占三个字符
    n = int(id_str[3 : len(id_str)], 36)
    return ShortID(year=year, n=n)


def str36(year: int, n: int) -> str:
    head = base_repr(year, 36)
    tail = base_repr(n, 36)
    return (head + tail).upper()


# https://github.com/numpy/numpy/blob/main/numpy/core/numeric.py
def base_repr(number: int, base: int = 10, padding: int = 0) -> str:
    """
    Return a string representation of a number in the given base system.
    """
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if base > len(digits):
        raise ValueError("Bases greater than 36 not handled in base_repr.")
    elif base < 2:
        raise ValueError("Bases less than 2 not handled in base_repr.")

    num = abs(number)
    res = []
    while num:
        res.append(digits[num % base])
        num //= base
    if padding:
        res.append("0" * padding)
    if number < 0:
        res.append("-")
    return "".join(reversed(res or "0"))
