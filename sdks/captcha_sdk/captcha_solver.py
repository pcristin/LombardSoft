from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
from sdks.captcha_sdk.constants import WEBSITE_URL, WEBSITE_KEY
from utils.logger_config import logger

class CaptchaSolver:
    def __init__(self, api_key: str) -> None:
        self.solver = recaptchaV2Proxyless()
        self.solver.set_verbose(1)
        self.solver.set_key(api_key)
        logger.info("CaptchaSolver initialized")

    def solve_captcha(self, website_url: str = WEBSITE_URL, website_key: str = WEBSITE_KEY) -> str:
        self.solver.set_website_url(website_url)
        self.solver.set_website_key(website_key)
        g_code = self.solver.solve_and_return_solution()
        if g_code != 0:
            logger.info("Captcha solved successfully")
            return g_code
        else:
            logger.error("Failed to solve captcha")
            return ''
        
    def get_solver_balance(self) -> float:
        balance = self.solver.get_balance()
        logger.info(f"Captcha solver balance: {balance}")
        return balance
