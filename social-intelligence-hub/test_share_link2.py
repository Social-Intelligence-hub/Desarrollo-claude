import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-DO")
        
        # Search for CAPEX and go to reviews
        await page.goto("https://www.google.com/maps")
        await page.wait_for_timeout(2000)
        
        # Accept cookies if present
        try:
            await page.locator('button:has-text("Aceptar todo")').first.click(timeout=2000)
        except:
            pass

        await page.fill('input#searchboxinput', 'CAPEX Santiago Republica Dominicana')
        await page.press('input#searchboxinput', 'Enter')
        await page.wait_for_timeout(5000)
        
        # Click reviews tab
        reviews_btn = page.locator('button[aria-label*="Reseñas"], button[aria-label*="Opiniones"], button[aria-label*="Reviews"], .hh76qc').first
        if await reviews_btn.is_visible():
            await reviews_btn.click()
            await page.wait_for_timeout(3000)
            
        cards = await page.locator('.jftiEf, div[data-review-id]').all()
        print(f"Found {len(cards)} cards")
        
        results = []
        for card in cards[:3]:
            try:
                # author
                author_el = card.locator('.d4r55').first
                if not await author_el.is_visible():
                    author_el = card.locator('.XE87Be').first
                author_name = await author_el.text_content() if await author_el.count() > 0 else "Anónimo"
                
                # text
                text_el = card.locator('.wiI7pd').first
                more_btn = card.locator('button:has-text("Ver más"), button:has-text("See more")').first
                if await more_btn.is_visible():
                    await more_btn.click()
                    await page.wait_for_timeout(300)
                text = await text_el.text_content() if await text_el.count() > 0 else ""
                
                # Click share
                share_btn = card.locator('button[aria-label*="Compartir"], button[aria-label*="Share"], button[data-tooltip*="Compartir"]').first
                if await share_btn.is_visible():
                    await share_btn.click()
                    await page.wait_for_timeout(2000)
                    
                    link_input = page.locator('input[readonly]').first
                    if await link_input.is_visible():
                        val = await link_input.input_value()
                        results.append({
                            "author_name": author_name,
                            "text": text,
                            "url": val
                        })
                        print("Got link:", val)
                    
                    # Close modal
                    close_btn = page.locator('button[aria-label*="Cerrar"], button[aria-label*="Close"]').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                print("Error with card:", e)
                
        print("Results:")
        for r in results:
            print(f"- {r['author_name']}: {r['url']}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
