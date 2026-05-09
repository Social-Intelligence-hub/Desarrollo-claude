import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(locale="es-DO")
        
        # URL of CAPEX
        url = "https://www.google.com/maps/place/CAPEX/@19.4682025,-70.7327663,17z/data=!4m8!3m7!1s0x8eaab09228eb1935:0xa4d4d6b625078a05!8m2!3d19.4682025!4d-70.7301914!9m1!1b1!16s%2Fg%2F1tcwgmbm?entry=ttu"
        await page.goto(url)
        await page.wait_for_timeout(3000)
        
        cards = await page.locator('.jftiEf').all()
        print(f"Found {len(cards)} cards")
        
        for card in cards[:3]:
            # find share button
            share_btn = card.locator('button[aria-label="Compartir"], button[aria-label="Share"], button[data-tooltip="Compartir"]').first
            if await share_btn.is_visible():
                print("Clicking share...")
                await share_btn.click()
                await page.wait_for_timeout(2000)
                
                # find input with link
                link_input = page.locator('input[readonly]').first
                if await link_input.is_visible():
                    val = await link_input.input_value()
                    print("SHARE LINK:", val)
                
                # close modal
                close_btn = page.locator('button[aria-label="Cerrar"], button[aria-label="Close"]').first
                if await close_btn.is_visible():
                    await close_btn.click()
                await page.wait_for_timeout(1000)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
