import asyncio
import os
import sys

from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="es-DO")
        
        url = "https://www.google.com/maps/place/CAPEX/@19.4682025,-70.7327663,17z/data=!4m8!3m7!1s0x8eaab09228eb1935:0xa4d4d6b625078a05!8m2!3d19.4682025!4d-70.7301914!9m1!1b1!16s%2Fg%2F1tcwgmbm?entry=ttu"
        await page.goto(url)
        await page.wait_for_timeout(5000)
        
        html = await page.content()
        with open("maps_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("HTML dumped to maps_dump.html")
        await browser.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run())
