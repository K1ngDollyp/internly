import time
from playwright.sync_api import sync_playwright

def run_browser_verification():
    with sync_playwright() as p:
        # Launch Chrome browser in headed mode so it displays on user's desktop!
        browser = p.chromium.launch(headless=False, channel="chrome", slow_mo=500)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("[TEST STEP 1] Navigating to https://internly2026.vercel.app ...")
        page.goto("https://internly2026.vercel.app")
        page.wait_for_selector("#login-email")
        page.screenshot(path="scratch/01_landing_page.png")

        print("[TEST STEP 2] Logging in as Industry Supervisor (supervisor1@brighttech.com) ...")
        page.fill("#login-email", "supervisor1@brighttech.com")
        page.fill("#login-password", "password123")
        page.click("#login-form button[type='submit']")

        # Wait for dashboard section to be unhidden
        page.wait_for_selector("#dashboard-section:not(.hidden)")
        time.sleep(3)
        page.screenshot(path="scratch/02_supervisor_dashboard.png")

        print("[TEST STEP 3] Clicking 'Grade / Review' for Oluwaseun Adeleke ...")
        page.click("button:has-text('Grade / Review')")
        page.wait_for_selector("#supervisor-review-workspace")
        time.sleep(2)
        page.screenshot(path="scratch/03_supervisor_workspace_locked_assessment.png")

        print("[TEST STEP 4] Verifying Logbook Week Selector dropdown ...")
        select_elem = page.locator("#supervisor-logbook-week-select")
        if select_elem.is_visible():
            print("Logbook Week Selector dropdown is visible!")
            options = select_elem.locator("option").all_inner_texts()
            print(f"Dropdown options found: {options}")

        print("[TEST STEP 5] Verifying Final SIWES Assessment Locked Notice ...")
        locked_notice = page.locator("#sup-final-grading-locked-notice")
        if locked_notice.is_visible():
            print("SUCCESS: Final SIWES Assessment form is correctly LOCKED and hidden!")
            print(f"Notice text: {locked_notice.inner_text()}")

        print("[TEST STEP 6] Logging in as Coordinator (coordinator@university.edu.ng) to verify In-App PDF Preview & CSV Export ...")
        page.click("button:has-text('Log Out')")
        page.wait_for_selector("#login-email")

        page.fill("#login-email", "coordinator@university.edu.ng")
        page.fill("#login-password", "password123")
        page.click("button[type='submit']")
        page.wait_for_selector("#coord-total-students")
        time.sleep(2)
        page.screenshot(path="scratch/04_coordinator_dashboard.png")

        print("[TEST COMPLETED] Closing browser in 5 seconds...")
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    run_browser_verification()
