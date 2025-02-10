from playwright.sync_api import sync_playwright, Page
import time
import logging as log
import json

log.basicConfig(level=log.INFO)

selectors = {
    'main_menu' : 'ul.menu.top-level-menu a',
    'product_links' : 'div.button-container a',
    'product_title' : '#prod_name',
    'product_desc' : 'div.rte'
}

def _scrape_menu():
    elements = page.query_selector_all(selectors['main_menu'])
    links = [element.get_attribute('href') for element in elements if element.get_attribute('href')]
    log.info(f"Found {len(links)} main menu links.")
    prefix = "https://pardi.hu/shop/"
    final_links = [prefix + link for link in links]
    print(f"Main menu links:\n {final_links} \n")
    return final_links

def _scrape_product(page):
    log.info("Scraping product links\n")
    product_links = page.query_selector_all(selectors['product_links'])
    links = [link.get_attribute('href') for link in product_links if link.get_attribute('href')]
    log.info(f"Found {len(links)} products links.")
    print(f"Products links:\n {links} \n")
    return links

def scrape_product_title(page: Page) -> str:
    """
    Scrapes the product title from the current product page.
    Adjust the selector to match the actual HTML.
    """
    title_element = page.query_selector(selectors["product_title"])
    if title_element:
        return title_element.inner_text().strip()
    return ""

def scrape_product_desc(page: Page) -> str:
    """
    Scrapes the product text from the currently loaded product page.
    Expects an element matching selectors['product_desc'].
    Returns the text content as a string, or an empty string if not found.
    """
    desc_element = page.query_selector(selectors["product_desc"])
    if desc_element:
        return desc_element.inner_text().strip()
    return ""

def scrape_products_links(page: Page, jsonfile_input: str, jsonfile_output: str):
    """
    1. Loads a list of URLs from the JSON file specified by jsonfile_input.
    2. For each URL, visits the page and checks if the product links selector exists.
       If the selector is not found, go to the another link.
    3. If found, scrapes product links using _scrape_product(page) and adds them to a set.
    4. Finally, saves the collected unique product links to the file specified by jsonfile_output.
    """
    links = load_links_from_json(jsonfile_input)
    log.info(f"Loaded {len(links)} links from {jsonfile_input}...\n")
    all_product_links = set()
    for url in links:
        log.info(f"Visiting: {url}")
        try:
            page.goto(url, timeout=100000, wait_until='load')
            # time.sleep(2)
        except Exception as e:
            log.error(f"Error loading {url}: {e}")
            raise Exception(f"Error loading {url}: {e}")
        #checking if the product link selector exists on this page
        if page.query_selector(selectors['product_links']):
            post_links = _scrape_product(page)
            log.info(f"Scraped {len(post_links)} posts on this page.\n")
            for plink in post_links:
                all_product_links.add(plink)
        else:
            log.info("Product links selector not found on this page. Skipping this URL.")
    final_list = list(all_product_links)
    log.info(f"Total unique post links after scraping all pages: {len(final_list)}")
    save_links_to_json(final_list, jsonfile_output)

def scrape_text_from_product(page: Page, input_json: str, output_json: str):
    """
    1. Loads a list of product URLs from input_json.
    2. Visits each product page, scrapes the product title and description.
    3. If the description is empty, the product is skipped.
    4. Collects the data in a list of dictionaries with keys: 'url', 'title', and 'desc'.
    5. Saves the list as JSON in output_json.
    """
    product_links = load_links_from_json(input_json)
    log.info(f"Loaded {len(product_links)} product links from {input_json}.")
    results = [] 
    for link in product_links:
        log.info(f"Visiting product page: {link}")
        try:
            page.goto(link, timeout=100000, wait_until='load') 
            time.sleep(2)
        except Exception as e:
            log.error(f"Timeout or error loading {link}: {e}")
            raise Exception(f"Timeout or error loading {link}: {e}")
            
        title = scrape_product_title(page)
        desc = scrape_product_desc(page)
        log.info(f"Scraped product data: title length: {len(title)} characters, description length: {len(desc)} characters.")

        if desc and title and not desc.strip() and not title.strip():
            log.info(f"Skipping product at {link} because description and title is empty.")
            continue
        product_data = {
            "url": link,
            "title": title,
            "desc": desc
        }
        results.append(product_data)
    save_links_to_json(results, output_json)

    log.info(f"Saved scraped product data for {len(results)} products to {output_json}.")

def save_links_to_json(links: list[str], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def load_links_from_json(filename: str) -> list[str]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(1000*60)
    page.set_default_navigation_timeout(1000*60)

    scrape_text_from_product(
        page=page,
        input_json='pardi/pardi_all_products.json',
        output_json='pardi/pardi_finall_output.json'
    )

    #testing
    """page.goto("https://pardi.hu/shop/index.php")
    test = page.locator(selectors['main_menu']).screenshot(path="pardi/screenshot.png")"""



    browser.close()