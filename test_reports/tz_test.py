"""Standalone Playwright timezone bug verification for Sanctus daily practice."""
import asyncio
import re
from playwright.async_api import async_playwright

BASE = "https://faithful-fitness-3.preview.emergentagent.com"
TOKEN = "TEST_FE_ITER11_TOKEN"


def to_minutes(s):
    if not s:
        return None
    s = s.strip().upper().replace(" ", "")
    m = re.match(r"(\d{1,2}):(\d{2})(AM|PM)", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "PM" and h != 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return h * 60 + mi


async def test_tz(browser, tz_name):
    print(f"\n==== Testing timezone: {tz_name} ====")
    ctx = await browser.new_context(
        viewport={"width": 390, "height": 844},
        timezone_id=tz_name,
    )
    page = await ctx.new_page()
    try:
        await page.goto(BASE + "/", wait_until="domcontentloaded")
        await page.evaluate(f"localStorage.setItem('sanctus_session_token', JSON.stringify('{TOKEN}'))")
        await page.goto(BASE + "/(tabs)", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        browser_tz = await page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")
        print(f"Browser-reported timezone: {browser_tz}")

        try:
            await page.wait_for_selector('[data-testid="daily-practice-card"]', timeout=15000)
        except Exception as e:
            print(f"daily-practice-card NOT FOUND: {e}")
            await page.screenshot(path=f"/tmp/no_card_{tz_name.replace('/', '_')}.png", quality=40, full_page=False)
            return None

        undo = await page.query_selector('[data-testid="daily-practice-undo"]')
        if undo:
            print("Already completed, clicking undo to reset")
            await undo.click(force=True)
            await page.wait_for_timeout(2000)

        await page.wait_for_selector('[data-testid="daily-practice-complete"]', timeout=10000)

        js_time_before = await page.evaluate(
            "new Date().toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'})"
        )
        js_iso_before = await page.evaluate("new Date().toISOString()")
        print(f"Local time BEFORE tap: {js_time_before}  iso={js_iso_before}")

        await page.click('[data-testid="daily-practice-complete"]', force=True)
        await page.wait_for_timeout(3000)

        js_time_after = await page.evaluate(
            "new Date().toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'})"
        )

        done = await page.query_selector('[data-testid="daily-practice-done"]')
        if not done:
            print("daily-practice-done block did NOT appear")
            await page.screenshot(path=f"/tmp/no_done_{tz_name.replace('/', '_')}.png", quality=40, full_page=False)
            return None
        displayed_text = await done.inner_text()
        print(f"Done block text: {displayed_text!r}")

        m = re.search(r"Completed at (\d{1,2}:\d{2}\s?(?:AM|PM))", displayed_text, re.IGNORECASE)
        displayed_time = m.group(1) if m else None
        print(f"Parsed displayed: {displayed_time}")
        print(f"Local before    : {js_time_before}")
        print(f"Local after     : {js_time_after}")

        disp_m = to_minutes(displayed_time)
        before_m = to_minutes(js_time_before)
        after_m = to_minutes(js_time_after)
        diff = None
        if disp_m is not None and before_m is not None:
            diff_a = min(abs(disp_m - before_m), 1440 - abs(disp_m - before_m))
            diff_b = min(abs(disp_m - after_m), 1440 - abs(disp_m - after_m)) if after_m is not None else 9999
            diff = min(diff_a, diff_b)
            print(f"Diff (minutes) vs local: {diff}")
        return {
            "tz": tz_name,
            "browser_tz": browser_tz,
            "displayed_time": displayed_time,
            "js_time_before": js_time_before,
            "js_time_after": js_time_after,
            "diff_minutes": diff,
            "pass": diff is not None and diff <= 1,
        }
    finally:
        await ctx.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            r_ny = await test_tz(browser, "America/New_York")
            r_la = await test_tz(browser, "America/Los_Angeles")
        finally:
            await browser.close()

    print("\n========== SUMMARY ==========")
    for label, v in [("New York", r_ny), ("Los Angeles", r_la)]:
        print(f"{label}: {v}")
        if v and v.get("pass"):
            print(f"  PASS - displayed time matches local within 1 minute")
        elif v and v.get("diff_minutes") is not None:
            print(f"  FAIL - diff={v['diff_minutes']} minutes (bug not fixed if ~180-300)")
        else:
            print(f"  ERROR - could not capture")


if __name__ == "__main__":
    asyncio.run(main())
