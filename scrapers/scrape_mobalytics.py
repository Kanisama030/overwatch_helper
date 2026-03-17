import json
import asyncio
from playwright.async_api import async_playwright
import os

async def scrape_mobalytics():
    os.makedirs('dataset', exist_ok=True)
    
    all_data = {
        "heroes": [],
        "meta_commentary": []
    }
    
    hero_map = {} 

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Scrape the standard tier list page
        print("Navigating to Mobalytics Standard Tier List...")
        try:
            await page.goto("https://mobalytics.gg/overwatch/tier-lists/standard", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5) 
        except Exception as e:
            print(f"Error loading tier list page: {e}")
            
        print("Extracting tier list and commentary data...")
        tier_data = await page.evaluate('''() => {
            const TARGET_CLASS = 'x1exxlbk';
            const tierDivs = Array.from(document.querySelectorAll('div')).filter(d => 
                ['S','A','B','C','D'].includes(d.innerText.trim()) && d.classList.contains(TARGET_CLASS)
            );
            
            let result = {};
            tierDivs.forEach(div => {
                let tier = div.innerText.trim();
                let container = div;
                while(container && container.parentElement && container.tagName !== 'MAIN') {
                    const potentialHeroes = container.innerText.trim().split('\\n').filter(t => t.length > 2 && !['S','A','B','C','D'].includes(t));
                    if (potentialHeroes.length > 3) {
                        potentialHeroes.forEach(h => {
                            if (h !== tier) result[h] = tier;
                        });
                        break;
                    }
                    container = container.parentElement;
                }
            });
            return result;
        }''')
        
        print(f"✅ Tiers detected for {len(tier_data)} heroes.")

        meta_commentary = await page.evaluate('''() => {
            let sections = [];
            const headings = document.querySelectorAll('h2, h3');
            let currentMeta = null;
            
            for (let h of headings) {
                let text = h.innerText.trim();
                if (text.endsWith(' Commentary') || text === 'Tiers Explained' || text === 'Overview') {
                    if (currentMeta) sections.push(currentMeta);
                    currentMeta = { category: text, heroes: [] };
                } else if (currentMeta && h.tagName === 'H3') {
                    let heroName = text.split('\\n')[0];
                    let paragraphs = [];
                    let next = h.nextElementSibling;
                    while(next && next.tagName === 'P') {
                        paragraphs.push(next.innerText.trim());
                        next = next.nextElementSibling;
                    }
                    if (paragraphs.length > 0) currentMeta.heroes.push({ name: heroName, text: paragraphs });
                } else if (currentMeta && h.tagName === 'H2' && !text.endsWith(' Commentary')) {
                    sections.push(currentMeta);
                    currentMeta = null;
                }
            }
            if (currentMeta) sections.push(currentMeta);
            return sections;
        }''')
        all_data["meta_commentary"] = meta_commentary

        for hero_name, tier in tier_data.items():
            hero_map[hero_name] = {
                "Hero": hero_name,
                "Tier": tier,
                "Guide": []
            }

        # 2. Scrape guide pages
        print("Finding hero guide links...")
        try:
            await page.goto("https://mobalytics.gg/overwatch/heroes", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
        except Exception: pass
            
        hero_links = await page.evaluate('''() => {
            const links = document.querySelectorAll('a[href*="/heroes/"]');
            let result = {};
            for (let link of links) {
                let name = link.innerText.trim().split('\\n')[0]; 
                let href = link.getAttribute('href');
                if (name && (href.includes('-guide') || href.includes('/heroes/'))) {
                    result[name] = href;
                }
            }
            return result;
        }''')
        
        heroes_to_scrape = list(hero_map.keys())
        if not heroes_to_scrape: heroes_to_scrape = list(hero_links.keys())

        for hero in heroes_to_scrape:
            url = ""
            if hero in hero_links:
                href = hero_links[hero]
                url = "https://mobalytics.gg" + href if href.startswith('/') else href
            else:
                hero_slug = hero.lower().replace('.', '').replace(':', '').replace(' ', '-')
                url = f"https://mobalytics.gg/overwatch/heroes/{hero_slug}-guide"
                
            print(f"Scraping DEDUPLICATED guide for: {hero}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(1.5)
                
                full_guide = await page.evaluate('''(heroName) => {
                    const main = document.querySelector('main');
                    if (!main) return [];
                    
                    const elements = Array.from(main.querySelectorAll('h2, h3, h4, p, li'));
                    let flattened = [];
                    let counters = [0, 0, 0]; 
                    
                    // Track seen content to avoid repeats across the guide
                    let globalSeen = new Set();
                    
                    for (let el of elements) {
                        let text = el.innerText.trim();
                        if (!text || ['Privacy Policy', 'Terms of Service', 'Table of Contents'].includes(text)) continue;
                        
                        // Noise filter for specific unwanted strings
                        if (text.startsWith("In this Overwatch") && text.includes("guide")) continue;

                        const tag = el.tagName;
                        if (tag.startsWith('H')) {
                            const level = parseInt(tag.substring(1));
                            const adjustedLevel = level - 1; // H2 -> 1, H3 -> 2, H4 -> 3
                            if (adjustedLevel < 1 || adjustedLevel > 3) continue;

                            counters[adjustedLevel-1]++;
                            for (let i = adjustedLevel; i < 3; i++) counters[i] = 0;
                            
                            const id = counters.slice(0, adjustedLevel).join('.');
                            
                            let cleanTitle = text.replace(heroName + ' ', '').replace(heroName, '').trim();
                            if (!cleanTitle) cleanTitle = text; 
                            
                            flattened.push({
                                id: id,
                                title: cleanTitle,
                                content: []
                            });
                        } else {
                            if (flattened.length === 0) continue; 
                            
                            const lastSection = flattened[flattened.length - 1];
                            
                            // SMART DEDUPLICATION:
                            // 1. Skip if exactly same as any previously seen text
                            if (globalSeen.has(text)) continue;
                            
                            // 2. Skip if it's a substring of the previously added line in THIS section
                            if (lastSection.content.length > 0) {
                                let prev = lastSection.content[lastSection.content.length - 1];
                                if (prev.includes(text) || text.includes(prev)) {
                                   // If new text is longer, replace the previous one
                                   if (text.length > prev.length) {
                                       lastSection.content[lastSection.content.length - 1] = text;
                                       globalSeen.add(text);
                                   }
                                   continue;
                                }
                            }
                            
                            lastSection.content.push(text);
                            globalSeen.add(text);
                        }
                    }
                    
                    return flattened.map(section => {
                        if (section.content && section.content.length === 0) {
                            delete section.content;
                        }
                        return section;
                    }).filter(section => section.title || (section.content && section.content.length > 0));
                }''', hero)
                
                if hero not in hero_map:
                    hero_map[hero] = {"Hero": hero, "Tier": "Unknown", "Guide": []}
                hero_map[hero]["Guide"] = full_guide
                
            except Exception as e:
                print(f"Error scraping {hero}: {e}")
                
        await browser.close()
        
        all_data["heroes"] = list(hero_map.values())
        
        if all_data["heroes"]:
            out_file = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "mobalytics_heroes.json")
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print(f"\n✅ Successfully saved cleaned, deduplicated, and substring-filtered guide to {out_file}")
            return all_data
        else:
            print("No data collected!")
            return None

if __name__ == "__main__":
    asyncio.run(scrape_mobalytics())
