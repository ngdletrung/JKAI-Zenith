import asyncio
from playwright.async_api import async_playwright
import sys
import time
import os

async def run_ui_test(question, output_image):
    async with async_playwright() as p:
        # Use the CloakBrowser binary if possible, or just standard chromium
        # Since we are inside the container, we use standard chromium for simplicity
        # or find the cloakbrowser binary.
        browser_path = "/root/.cloakbrowser/chromium-146.0.7680.177.5/chrome"
        if not os.path.exists(browser_path):
             browser_path = "/root/.cloakbrowser/chromium-146.0.7680.177.3/chrome"
             
        if os.path.exists(browser_path):
            browser = await p.chromium.launch(executable_path=browser_path, headless=True)
        else:
            browser = await p.chromium.launch(headless=True)
            
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print(f"Navigating to mission-control:9999...")
        await page.goto("http://mission-control:9999/", wait_until="networkidle")
        
        # Handle welcome modal or overlays
        print("Checking for overlays...")
        await asyncio.sleep(2)
        await page.keyboard.press("Escape") # Try to close modal with ESC
        await asyncio.sleep(1)
        
        # Wait for textarea
        await page.wait_for_selector("textarea", timeout=10000)
        print(f"Typing question: {question}")
        await page.fill("textarea", question)
        
        # Click send button (lucide-send icon is usually inside a button)
        # We look for a button with the icon or just the button near the textarea
        send_button = await page.query_selector("button:has(.lucide-send), button:has-text('Send'), .lucide-send")
        if send_button:
            try:
                await send_button.click(timeout=5000)
            except Exception:
                print("Click failed, trying forced click...")
                await send_button.click(force=True)
        else:
            # Fallback: press Enter
            await page.keyboard.press("Enter")
            
        print("Waiting for response...")
        # Wait for the "cursor" or "typing indicator" to disappear
        # In this UI, it usually shows a loading state. 
        # We'll wait for a few seconds or until a new message appearing.
        await asyncio.sleep(30) # Increased wait for completion
        
        # Capture screenshot
        evidence_path = f"/app/screenshots/{output_image}"
        os.makedirs("/app/screenshots", exist_ok=True)
        await page.screenshot(path=evidence_path)
        print(f"Screenshot saved to {evidence_path}")
        
        # Extract last message
        # Messages are usually in a chat container
        messages = await page.query_selector_all(".chat-message, .message") # Adjust selector based on actual UI
        if messages:
            last_msg = await messages[-1].inner_text()
            print(f"JKAI: {last_msg}")
        else:
            print("Could not extract answer text.")
            
        await browser.close()

if __name__ == "__main__":
    q = sys.argv[1]
    img = sys.argv[2]
    asyncio.run(run_ui_test(q, img))
