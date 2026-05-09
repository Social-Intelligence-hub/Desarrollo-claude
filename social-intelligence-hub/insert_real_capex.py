import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client
from playwright.async_api import async_playwright

load_dotenv("scraper/.env")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

async def run():
    print("Starting Playwright to get REAL reviews...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(locale="es-DO")
        
        print("Navigating to maps...")
        await page.goto("https://www.google.com/maps")
        await page.wait_for_timeout(2000)
        
        try:
            await page.locator('button:has-text("Aceptar todo"), button:has-text("Accept all"), form button').first.click(timeout=3000)
            await page.wait_for_timeout(2000)
        except Exception:
            pass
            
        await page.fill('input#searchboxinput', 'CAPEX Santiago Republica Dominicana')
        await page.press('input#searchboxinput', 'Enter')
        await page.wait_for_timeout(5000)
        
        reviews_btn = page.locator('button[aria-label*="Reseñas"], button[aria-label*="Opiniones"], button[aria-label*="Reviews"], .hh76qc').first
        if await reviews_btn.is_visible():
            await reviews_btn.click()
            await page.wait_for_timeout(3000)
            
        await page.screenshot(path="maps_error.png", full_page=True)
        
        cards = await page.locator('.jftiEf').all()
        print(f"Found {len(cards)} cards")
        
        if not cards:
            print("Trying fallback selector...")
            cards = await page.locator('div[data-review-id]').all()
            print(f"Found {len(cards)} cards with fallback")
            
        results = []
        for card in cards[:3]:
            try:
                author_el = card.locator('.d4r55').first
                if not await author_el.is_visible():
                    author_el = card.locator('.XE87Be').first
                author_name = await author_el.text_content() if await author_el.count() > 0 else "Anónimo"
                
                text_el = card.locator('.wiI7pd').first
                more_btn = card.locator('button:has-text("Ver más"), button:has-text("See more")').first
                if await more_btn.is_visible():
                    await more_btn.click()
                    await page.wait_for_timeout(300)
                text = await text_el.text_content() if await text_el.count() > 0 else ""
                
                # Get Share link!
                share_btn = card.locator('button[aria-label*="Compartir"], button[aria-label*="Share"], button[data-tooltip*="Compartir"]').first
                link_url = url # fallback
                if await share_btn.count() > 0 and await share_btn.is_visible():
                    print(f"Clicking share for {author_name}...")
                    await share_btn.click()
                    await page.wait_for_timeout(2000)
                    
                    link_input = page.locator('input[readonly]').first
                    if await link_input.count() > 0 and await link_input.is_visible():
                        val = await link_input.input_value()
                        if val:
                            link_url = val
                            print(f"Got exact link: {link_url}")
                    
                    close_btn = page.locator('button[aria-label*="Cerrar"], button[aria-label*="Close"]').first
                    if await close_btn.count() > 0 and await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(1000)
                else:
                    print("Share button not found for", author_name)
                
                results.append({
                    "author_name": author_name,
                    "text_original": text or "Reseña en Google Maps",
                    "source_url": link_url,
                    "star_rating": 5,
                    "sentiment_label": "positive",
                    "confidence_score": 0.95
                })
            except Exception as e:
                print("Error parsing card:", e)
                
        await browser.close()

    print(f"Got {len(results)} reviews, inserting into Supabase...")
    entity_res = supabase.table("entities").select("id").eq("slug", "capex-institucion").execute()
    source_res = supabase.table("sources").select("id").eq("slug", "google_reviews").execute()
    entity_id = entity_res.data[0]["id"]
    source_id = source_res.data[0]["id"]
    
    for r in results:
        r["entity_id"] = entity_id
        r["source_id"] = source_id
        try:
            supabase.table("mentions").insert(r).execute()
            print(f"Inserted: {r['author_name']} -> {r['source_url']}")
        except Exception as e:
            print("Error inserting to DB:", e)
            
    print("Done!")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run())
