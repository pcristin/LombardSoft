from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
from .constants import WEBSITE_URL, WEBSITE_KEY

class CaptchaSolver:
    def __init__(self, api_key: str):
        self.solver = recaptchaV2Proxyless()
        self.solver.set_verbose(1)
        self.solver.set_key(api_key)

    def solve_captcha(self, website_url: str = WEBSITE_URL, website_key: str = WEBSITE_KEY) -> str:
        self.solver.set_website_url(website_url)
        self.solver.set_website_key(website_key)
        g_code = self.solver.solve_and_return_solution()
        if g_code != 0:
            return g_code
        else:
            return None
        
    def get_solver_balance(self) -> float:
        return self.solver.get_balance()
