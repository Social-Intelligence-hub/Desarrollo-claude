import asyncio
from playwright.async_api import async_playwright
import re
import json

async def debug_maps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="es-DO")
        page = await context.new_page()
        
        url = "https://www.google.com/maps/search/CAPEX+Centro+de+Innovación+y+Capacitación+Profesional+Santiago"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        tabs = await page.locator('div[role="tablist"] button').all_inner_texts()
        
        links = await page.locator('a[href*="/maps/place/"]').all_inner_texts()
        link_elements = await page.locator('a[href*="/maps/place/"]').all()
        
        if not tabs and link_elements:
            print("Clicking first place link...")
            await link_elements[0].click()
            await page.wait_for_timeout(3000)
            tabs = await page.locator('div[role="tablist"] button').all_inner_texts()
        
        buttons = await page.locator('button').all_text_contents()
        
        output = {
            "tabs": [t.strip() for t in tabs if t.strip()],
            "buttons": [b.strip() for b in set(buttons) if b.strip()],
            "links": [l.strip() for l in links if l.strip()]
        }
        
        with open("debug_gmaps.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_maps())
