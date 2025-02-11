from playwright.sync_api import sync_playwright, Page
import time
import logging as log
import json
from urllib.parse import urlparse, parse_qs
import os

log.basicConfig(level=log.INFO)

selectors = {
    'pagination' : 'div.pagination.d-flex.flex-column',
    'pagination_last_page' : 'body > section.container-fluid.products-category > div.pagination.d-flex.flex-column > div.JSPaginationContent > div > ul > li:nth-child(7)',
    'product' : 'a.single-product-main',
    'product_title' : 'div.product-header h1',
    'product_desc' : 'div.info-containers *'
}

def has_pagination(page: Page) -> bool:
    element = page.query_selector(selectors['pagination'])
    return element is not None

def get_last_page_number(page: Page) -> int:
    """
    1. Looks for the 'last page' link a.page-link.page-last.
    2. Takes the href attribute (?page=N) from it and extracts the number N.
    3. Returns N as an int, and if it fails - returns 1.
    """
    last_page_link = page.query_selector(selectors['pagination_last_page']).inner_text()
    if not last_page_link:
        return 1
    return int(last_page_link)

def scrape_pages_in_reverse(page: Page, base_url: str, last_page: int) -> list[str]:
    """
    Creates a list of links in descending order (from last_page to 1).
    Assumes that there is no ?page=... parameter in base_url,
    or can handle adding &page=... if necessary.
    Example: last_page=5 => [base_url?page=5, base_url?page=4, ..., base_url?page=1]
    """
    links = []
    for p in range(last_page, 0, -1):
        if "?" in base_url:
            url = f"{base_url}&iPage={p}#filter-anchor"
        else:
            url = f"{base_url}?iPage={p}#filter-anchor"
        links.append(url)
    return links

def _scrape_product(page):
    log.info("Scraping product links\n")
    product_links = page.query_selector_all(selectors['product'])
    links = [link.get_attribute('href') for link in product_links if link.get_attribute('href')]
    log.info(f"Found {len(links)} products links.")
    print(f"Products links:\n {links} \n")
    return links

def scrape_product_from_pages(page: Page, json_filename: str, output_jsonfile):
    """
    1. Reads a list of URLs from `json_filename`.
    2. For each URL, goes to that page and scrapes product links (using _scrape_post).
    3. Collects all product links in a set (to avoid duplicates).
    4. Returns a list of all unique product links.
    """
    data = load_links_from_json(json_filename)
    log.info(f"Loaded {len(data)} links from {json_filename}")
    all_post_links = set()
    for url in data:
        log.info(f"Visiting: {url}")
        try:
            page.goto(url, timeout=100000, wait_until='load')
            #time.sleep(2)
        except Exception as e:
            log.error(f"Error loading {url}: {e}")
            raise Exception(f"Error loading {url}: {e}")
        post_links = _scrape_product(page)
        log.info(f"Scraped {len(post_links)} posts on this page.\n")
        for plink in post_links:
            all_post_links.add(plink)
    final_list = list(all_post_links)
    log.info(f"Total unique posts links after scraping all pages: {len(final_list)}")
    save_links_to_json(final_list, output_jsonfile)

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

def save_links_to_json(links: list[str], filename: str):
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def load_links_from_json(filename: str) -> list[str]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data
    
def process_item(url: str, page: Page) -> dict:
    """
    Given a product URL and a Playwright page, navigates to the URL,
    scrapes product title and description, and returns a dictionary.
    """
    log.info(f"Processing product URL: {url}")
    page.goto(url, timeout=100000, wait_until='load')
    time.sleep(2)
    title = scrape_product_title(page)
    desc = scrape_product_desc(page)
    log.info(f"Scraped product: title length {len(title)}, description length {len(desc)}.")
    return {"url": url, "title": title, "desc": desc}

# --- Function with checkpointing to process a long JSON file of product URLs ---

def process_long_json_with_page(page: Page, input_file: str, output_file: str, checkpoint_file: str):
    """
    Processes product URLs from input_file one by one using process_item().
    Saves processed items to output_file.
    Uses checkpoint_file to remember the index of the next item to process.
    If interrupted, the process can resume from the last checkpoint.
    """
    items = load_links_from_json(input_file)
    total_items = len(items)
    log.info(f"Total items to process: {total_items}")

    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = int(f.read().strip())
        log.info(f"Resuming from checkpoint: {checkpoint}")
    else:
        checkpoint = 0
    #Load previous output if exists; otherwise, start with an empty list.
    if os.path.exists(output_file):
        output_data = load_links_from_json(output_file)
    else:
        output_data = []
    for i in range(checkpoint, total_items):
        try:
            log.info(f"Processing item {i+1}/{total_items}")
            result = process_item(items[i], page)
            output_data.append(result)
        except Exception as e:
            log.error(f"Error processing item {i} - {e}")
            save_links_to_json(output_data, output_file)
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                f.write(str(i))
            raise e
        else:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                f.write(str(i+1))
        if (i + 1) % 10 == 0:
            save_links_to_json(output_data, output_file)
            log.info(f"Checkpoint updated at item {i+1}")
    save_links_to_json(output_data, output_file)
    log.info(f"Processing complete. Processed {len(output_data)} items.")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(1000*60)
    page.set_default_navigation_timeout(1000*60)

    page.goto("https://www.motozem.hu/motoros-oltozekek/#filter-anchor")
    test = page.query_selector(selectors['pagination_last_page']).inner_text()
    print(test)
    # Scraping main links first:
    """menu_links = load_links_from_json('motozem/motozen_menu_links.json')
    log.info(f"Loaded {len(menu_links)} menu links . . .\n")
    time.sleep(2)

    collected_links = set()

    for link in menu_links:
        print(f"\nI am visiting the website: {link} . . .\n")
        # Navigate to the current menu link
        page.goto(link, wait_until='load', timeout=100000)
        time.sleep(2)
        
        # Check if there is pagination on the page
        if not has_pagination(page):
            print("No pagination, going to next link...\n")
            collected_links.add(link)
        else:
            # Get the last page number from the current page
            last_page_num = get_last_page_number(page)
            print(f"The last page is: {last_page_num} . . .\n")
            # Generate all pagination links based on the last page number
            reversed_page_links = scrape_pages_in_reverse(page=page, base_url=link, last_page=last_page_num)
            for url in reversed_page_links:
                collected_links.add(url)
                print(f"\nUrl: {url} saved to the list. . .\n")

    # Save all collected links after processing all menu links
    all_links_list = list(collected_links)
    save_links_to_json(all_links_list, "motozem/motozen_page_links.json")
    print(f"\nSaved {len(all_links_list)} unique links to the json file. . .\n")

    # Scraping product links from the page links
    time.sleep(2)
    log.info(f"\nScraping products from pages has begun. . .\n")
    scrape_product_from_pages(
        page=page,
        json_filename="motozem/motozen_page_links.json",
        output_jsonfile="motozem/motozen_products_links.json"
    )
    time.sleep(2)"""

    log.info("\nScraping product information has begun. . .\n")
    # Scraping product text from product links
    process_long_json_with_page(
        page=page,
        input_file="motozem/motozen_products_links.json",
        output_file="motozem/motozen_final_output.json",
        checkpoint_file="motozem/products_checkpoint.txt"
    )
    """scrape_text_from_product(
        page=page,
        input_json="motozem/motozen_products_links.json",
        output_json="motozem/motozen_final_output.json"
    )"""

    browser.close()