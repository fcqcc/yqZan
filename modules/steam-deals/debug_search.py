"""Debug search page HTML parsing"""
import asyncio, httpx, re

async def debug():
    url = 'https://store.steampowered.com/search/'
    params = {'specials': 1, 'cc': 'cn', 'l': 'zh-cn', 'filter': 'globaltopsellers', 'page': 1}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
        text = resp.text
        
        matches = list(re.finditer(
            r'<a\s+[^>]*data-ds-appid="(\d+)"[^>]*class="search_result_row[^"]*"[^>]*>',
            text
        ))
        print(f'Found {len(matches)} row starts')
        
        for i, m in enumerate(matches[:5]):
            app_id = m.group(1)
            start = m.start()
            end_pos = text.find('</a>', start)
            if end_pos < 0:
                continue
            row = text[start:end_pos + 4]
            
            name = re.search(r'<span class="title">(.*?)</span>', row)
            disc = re.search(r'<div class="discount_pct"[^>]*>(-?\d+)%', row)
            prices = re.findall(r'¥(\d+\.?\d*)', row)
            print(f'\nRow {i}: app_id={app_id}')
            print(f'  Name: {name.group(1).strip() if name else "NOT FOUND"}')
            print(f'  Discount: {disc.group(1) if disc else "NOT FOUND"}')
            print(f'  Prices: {prices}')
            # Also print a snippet to see the structure
            print(f'  Snippet: {row[200:500]}')

asyncio.run(debug())
