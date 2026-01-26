"""
Session recovery module for Gemini Web OCR.

Detects various session issues beyond simple logout: verification prompts,
browser compatibility warnings, captcha, and redirects.
"""

import logging
import re
from typing import Optional, Dict, List, Tuple

from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class SessionIssueType:
    """Session issue type constants."""
    LOGIN_REQUIRED = "login_required"
    VERIFICATION_REQUIRED = "verification_required"
    SMS_VERIFICATION_REQUIRED = "sms_verification_required"
    OAUTH_APP_VERIFICATION = "oauth_app_verification"
    BROWSER_UNSUPPORTED = "browser_unsupported"
    CAPTCHA_DETECTED = "captcha_detected"
    ACCOUNT_REDIRECT = "account_redirect"
    UNKNOWN = "unknown"


class SessionRecovery:
    """Detects and diagnoses session-related issues."""
    
    # Issue indicators: (type, pattern, check_method)
    # check_method: "text" = page text search, "url" = URL pattern, "element" = element presence
    ISSUE_INDICATORS: List[Tuple[str, str, str]] = [
        # Login screens
        (SessionIssueType.LOGIN_REQUIRED, "Zaloguj się", "text"),
        (SessionIssueType.LOGIN_REQUIRED, "Sign in", "text"),
        (SessionIssueType.LOGIN_REQUIRED, "Sign in to continue", "text"),
        
        # Verification prompts
        (SessionIssueType.VERIFICATION_REQUIRED, "Verify it's you", "text"),
        (SessionIssueType.VERIFICATION_REQUIRED, "Potwierdź tożsamość", "text"),
        (SessionIssueType.VERIFICATION_REQUIRED, "Verify your identity", "text"),
        (SessionIssueType.VERIFICATION_REQUIRED, "Potwierdź, że to Ty", "text"),
        
        # SMS/Phone verification (requires manual intervention)
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Get a verification code", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Uzyskaj kod weryfikacyjny", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Text me a verification code", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Wyślij mi SMS z kodem", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Confirm your phone number", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Potwierdź numer telefonu", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "2-Step Verification", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Weryfikacja dwuetapowa", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Enter the code we sent", "text"),
        (SessionIssueType.SMS_VERIFICATION_REQUIRED, "Wpisz kod, który wysłaliśmy", "text"),
        
        # OAuth app verification dialog (auto-handled by AutoLogin)
        (SessionIssueType.OAUTH_APP_VERIFICATION, "Make sure this app is from Google", "text"),
        (SessionIssueType.OAUTH_APP_VERIFICATION, "Make sure Google made this app", "text"),
        (SessionIssueType.OAUTH_APP_VERIFICATION, "Sprawdź, czy ta aplikacja została pobrana z Google", "text"),
        (SessionIssueType.OAUTH_APP_VERIFICATION, "Sign in with Google", "text"),
        (SessionIssueType.OAUTH_APP_VERIFICATION, "Zaloguj się przez Google", "text"),
        
        # Browser compatibility
        (SessionIssueType.BROWSER_UNSUPPORTED, "This browser isn't supported", "text"),
        (SessionIssueType.BROWSER_UNSUPPORTED, "Twoja przeglądarka nie jest obsługiwana", "text"),
        (SessionIssueType.BROWSER_UNSUPPORTED, "Browser not supported", "text"),
        (SessionIssueType.BROWSER_UNSUPPORTED, "Update your browser", "text"),
        
        # Captcha
        (SessionIssueType.CAPTCHA_DETECTED, "I'm not a robot", "text"),
        (SessionIssueType.CAPTCHA_DETECTED, "reCAPTCHA", "text"),
        (SessionIssueType.CAPTCHA_DETECTED, "Verify you're human", "text"),
        (SessionIssueType.CAPTCHA_DETECTED, "Potwierdź, że jesteś człowiekiem", "text"),
        (SessionIssueType.CAPTCHA_DETECTED, "iframe[src*='recaptcha']", "element"),
        (SessionIssueType.CAPTCHA_DETECTED, "iframe[title*='reCAPTCHA']", "element"),
        (SessionIssueType.CAPTCHA_DETECTED, "div.g-recaptcha", "element"),
        (SessionIssueType.CAPTCHA_DETECTED, "div[id*='captcha']", "element"),
        
        # Account redirects
        (SessionIssueType.ACCOUNT_REDIRECT, "accounts.google.com", "url"),
        (SessionIssueType.ACCOUNT_REDIRECT, "myaccount.google.com", "url"),
    ]
    
    # Recovery suggestions for each issue type
    RECOVERY_SUGGESTIONS: Dict[str, str] = {
        SessionIssueType.LOGIN_REQUIRED: (
            "Session expired. Run login script:\n"
            "  OCR_PROFILE_SUFFIX=<profile> python login.py"
        ),
        SessionIssueType.VERIFICATION_REQUIRED: (
            "Google requires identity verification. Run headed mode:\n"
            "  OCR_PROFILE_SUFFIX=<profile> OCR_HEADED=1 python run.py\n"
            "Complete verification in browser window."
        ),
        SessionIssueType.BROWSER_UNSUPPORTED: (
            "Browser compatibility issue detected. Try:\n"
            "  1. Update Playwright: pip install -U playwright\n"
            "  2. Install browsers: playwright install chromium\n"
            "  3. Check user agent in browser_controller.py"
        ),
        SessionIssueType.CAPTCHA_DETECTED: (
            "CAPTCHA detected - manual intervention required.\n"
            "Profile will be paused. Run headed mode to solve:\n"
            "  OCR_PROFILE_SUFFIX=<profile> OCR_HEADED=1 python run.py"
        ),
        SessionIssueType.ACCOUNT_REDIRECT: (
            "Redirected to Google account page. Possible reasons:\n"
            "  - Session expired\n"
            "  - Account security check\n"
            "  - Terms of service update\n"
            "Run headed mode to investigate."
        ),
        SessionIssueType.OAUTH_APP_VERIFICATION: (
            "OAuth app verification dialog detected.\n"
            "AutoLogin will attempt to click 'Sign in' / 'Zaloguj się' automatically."
        ),
        SessionIssueType.UNKNOWN: (
            "Unknown session issue. Check screenshots in artifacts/screenshots/"
        ),
    }
    
    def __init__(self):
        """Initialize session recovery detector."""
        pass
    
    def detect_issue(self, page: Page) -> Optional[str]:
        """
        Detect session issue type from page state.
        
        Args:
            page: Playwright page to check
            
        Returns:
            Issue type constant or None if no issue detected
        """
        page_url = page.url or ""
        
        for issue_type, pattern, check_method in self.ISSUE_INDICATORS:
            try:
                if check_method == "text":
                    # Check page text content
                    if page.get_by_text(pattern, exact=False).count() > 0:
                        logger.warning(f"[SessionRecovery] Detected: {issue_type} (text: '{pattern}')")
                        return issue_type
                        
                elif check_method == "url":
                    # Check URL pattern
                    if pattern in page_url:
                        logger.warning(f"[SessionRecovery] Detected: {issue_type} (url contains: '{pattern}')")
                        return issue_type
                        
                elif check_method == "element":
                    # Check element presence
                    if page.locator(pattern).count() > 0:
                        logger.warning(f"[SessionRecovery] Detected: {issue_type} (element: '{pattern}')")
                        return issue_type
                        
            except Exception as e:
                logger.debug(f"[SessionRecovery] Check failed for {pattern}: {e}")
                continue
        
        return None
    
    def get_recovery_suggestion(self, issue_type: str) -> str:
        """
        Get recovery suggestion for issue type.
        
        Args:
            issue_type: Issue type constant
            
        Returns:
            Human-readable recovery instructions
        """
        return self.RECOVERY_SUGGESTIONS.get(
            issue_type,
            self.RECOVERY_SUGGESTIONS[SessionIssueType.UNKNOWN]
        )
    
    def is_critical(self, issue_type: str) -> bool:
        """
        Check if issue requires immediate attention.
        
        Args:
            issue_type: Issue type constant
            
        Returns:
            True if critical (requires user intervention)
        """
        critical_types = {
            SessionIssueType.LOGIN_REQUIRED,
            SessionIssueType.VERIFICATION_REQUIRED,
            SessionIssueType.CAPTCHA_DETECTED,
        }
        return issue_type in critical_types
    
    def should_pause_profile(self, issue_type: str) -> bool:
        """
        Check if issue should pause the profile.
        
        Args:
            issue_type: Issue type constant
            
        Returns:
            True if profile should be paused
        """
        pause_types = {
            SessionIssueType.CAPTCHA_DETECTED,
            SessionIssueType.VERIFICATION_REQUIRED,
        }
        return issue_type in pause_types
    
    def get_diagnostic_info(self, page: Page, issue_type: str) -> Dict[str, str]:
        """
        Gather diagnostic information about the issue.
        
        Args:
            page: Page with the issue
            issue_type: Detected issue type
            
        Returns:
            Dict with diagnostic info
        """
        try:
            return {
                "issue_type": issue_type,
                "url": page.url or "unknown",
                "title": page.title() or "unknown",
                "suggestion": self.get_recovery_suggestion(issue_type),
                "critical": str(self.is_critical(issue_type)),
                "should_pause": str(self.should_pause_profile(issue_type)),
            }
        except Exception as e:
            logger.warning(f"[SessionRecovery] Failed to gather diagnostics: {e}")
            return {
                "issue_type": issue_type,
                "error": str(e),
            }
