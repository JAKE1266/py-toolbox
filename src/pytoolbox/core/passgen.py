"""密码生成与强度估算。

基于 :mod:`secrets` 的密码学安全随机源,并保证生成的密码至少包含
每一种已启用字符类型各一个字符。
"""

from __future__ import annotations

import math
import secrets
import string

UPPER = string.ascii_uppercase
LOWER = string.ascii_lowercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?"

#: 容易混淆的字符(肉眼难分辨,默认从密码中剔除)
AMBIGUOUS = set("Il1O0o")

_STRENGTH_LABELS = ("极弱", "弱", "中等", "强", "极强")


def generate_password(length: int = 16, *, upper: bool = True, lower: bool = True,
                      digits: bool = True, symbols: bool = True,
                      exclude_ambiguous: bool = True) -> str:
    """生成一个随机强密码。

    :param length: 密码长度(至少 4)
    :param upper: 包含大写字母
    :param lower: 包含小写字母
    :param digits: 包含数字
    :param symbols: 包含特殊符号
    :param exclude_ambiguous: 剔除 ``Il1O0o`` 等易混淆字符
    """
    if length < 4:
        raise ValueError("密码长度至少为 4")

    pools = []
    for enabled, chars in ((upper, UPPER), (lower, LOWER), (digits, DIGITS), (symbols, SYMBOLS)):
        if not enabled:
            continue
        if exclude_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        if chars:
            pools.append(chars)
    if not pools:
        raise ValueError("至少需要启用一种字符类型")
    if length < len(pools):
        raise ValueError(f"长度至少为 {len(pools)} 才能覆盖全部已启用的字符类型")

    rng = secrets.SystemRandom()
    alphabet = "".join(pools)
    # 每种字符类型先保证出现一次,其余随机补齐
    password = [rng.choice(pool) for pool in pools]
    password += [rng.choice(alphabet) for _ in range(length - len(pools))]
    rng.shuffle(password)
    return "".join(password)


def generate_passwords(count: int = 5, **kwargs) -> list:
    """批量生成密码,参数同 :func:`generate_password`。"""
    if count < 1:
        raise ValueError("count 至少为 1")
    return [generate_password(**kwargs) for _ in range(count)]


def estimate_strength(password: str) -> dict:
    """估算密码强度:字符集规模 × 长度得出信息熵(比特)。

    :returns: ``{"entropy_bits": float, "score": 0-4, "label": str}``
    """
    pool = 0
    if any(c in UPPER for c in password):
        pool += len(UPPER)
    if any(c in LOWER for c in password):
        pool += len(LOWER)
    if any(c in DIGITS for c in password):
        pool += len(DIGITS)
    if any(c not in UPPER + LOWER + DIGITS for c in password):
        pool += 33  # 可打印符号的常见规模
    entropy = len(password) * math.log2(pool) if pool and password else 0.0

    if entropy < 28:
        score = 0
    elif entropy < 36:
        score = 1
    elif entropy < 60:
        score = 2
    elif entropy < 128:
        score = 3
    else:
        score = 4
    return {"entropy_bits": round(entropy, 1), "score": score, "label": _STRENGTH_LABELS[score]}
