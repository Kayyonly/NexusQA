from __future__ import annotations


class LoginDetector:
    SUCCESS_HINTS = ["logout", "sign out", "dashboard", "my account", "profile"]
    FAILURE_HINTS = ["invalid", "incorrect", "wrong password", "try again", "failed"]

    async def detect(self, page) -> dict:
        url = page.url.lower()
        body_text = (await page.inner_text("body")).lower()[:5000]
        cookies = await page.context.cookies()

        has_failure_text = any(h in body_text for h in self.FAILURE_HINTS)
        has_success_text = any(h in body_text for h in self.SUCCESS_HINTS)
        logout_button = await page.locator("button:has-text('Logout'), a:has-text('Logout'), button:has-text('Sign out'), a:has-text('Sign out')").count()
        redirect_after_login = "login" not in url
        token_detected = await page.evaluate(
            """() => {
                const keys = [...Object.keys(localStorage), ...Object.keys(sessionStorage)];
                return keys.some(k => /(token|auth|jwt|session)/i.test(k));
            }"""
        )

        login_success = (redirect_after_login or has_success_text) and not has_failure_text
        return {
            "login_success": login_success,
            "login_failed": has_failure_text and not login_success,
            "invalid_credential_message": has_failure_text,
            "redirect_after_login": redirect_after_login,
            "dashboard_loaded": has_success_text,
            "logout_button_visible": logout_button > 0,
            "auth_token_exists": bool(token_detected),
            "cookie_session_created": len(cookies) > 0,
        }
