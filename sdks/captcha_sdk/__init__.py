"""
Captcha SDK

A Python SDK for solving captchas using AntiCaptcha service.
"""

from .captcha_solver import CaptchaSolver
from .constants import WEBSITE_URL, WEBSITE_KEY

__all__ = ['CaptchaSolver', 'WEBSITE_URL', 'WEBSITE_KEY']
