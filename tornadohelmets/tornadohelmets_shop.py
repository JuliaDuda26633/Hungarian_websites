from playwright.sync_api import sync_playwright, Page
import time
import logging as log
import json
from urllib.parse import urlparse, parse_qs

log.basicConfig(level=log.INFO)

selectors = {
    'menu_links' : '#category-nav a.nav-link',
    'pagination' : 'ul.pagination.m-0',
    'pagination_last_page' : 'a.page-link.page-last',
    'product' : 'a.btn.btn-outline-primary',
    'product_title' : 'span.product-page-product-name',
    'product_desc_1' : '#productcustomcontent-wrapper div.module-body',
    'product_desc_2' : '#tab-productdescriptionnoparameters',
    'product_desc_3' : 'td.param-value.product-short-description'
}

def _scrape_menu():
    elements = page.query_selector_all(selectors['menu_links'])
    links = [element.get_attribute('href') for element in elements if element.get_attribute('href')]
    log.info(f"Found {len(links)} main menu links.")
    print(f"Main menu links:\n {links} \n")
    save_links_to_json(links, 'tornadohelmets/tornadohelmets_links.json')
    return links

def has_pagination(page: Page) -> bool:
    element = page.query_selector(selectors['pagination'])
    return element is not None

def get_last_page_number(page: Page) -> int:
    """
    1. Looks for the 'last page' link a.page-link.page-last.
    2. Takes the href attribute (?page=N) from it and extracts the number N.
    3. Returns N as an int, and if it fails - returns 1.
    """
    last_page_link = page.query_selector(selectors['pagination_last_page'])
    if not last_page_link:
        return 1 
    href = last_page_link.get_attribute("href")
    if not href:
        return 1
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    if 'page' in qs and qs['page']:
        try:
            return int(qs['page'][0])
        except ValueError:
            return 1
    return 1

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
            url = f"{base_url}&page={p}"
        else:
            url = f"{base_url}?page={p}"
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
    desc_element = page.query_selector(selectors["product_desc_1"])
    if desc_element:
        return desc_element.inner_text().strip()
    desc_element = page.query_selector(selectors["product_desc_2"])
    if desc_element:
        return desc_element.inner_text().strip()
    desc_element = page.query_selector(selectors["product_desc_3"])
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
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def load_links_from_json(filename: str) -> list[str]:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data
    
def remove_empty_desc_objects(input_filename: str, output_filename: str):
    """
    Loads a JSON file containing a list of dictionaries.
    Removes any dictionary where the 'desc' key is empty (after stripping whitespace).
    Saves the filtered list to a new JSON file.
    """
    data = load_links_from_json(input_filename)
    filtered = [item for item in data if item.get("desc", "").strip() != ""]
    save_links_to_json(filtered, output_filename)
    
 
    
with sync_playwright() as p:
    browser = p.chromium.launch(headless = False)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(1000*60)
    page.set_default_navigation_timeout(1000*60)

    page.goto("https://www.tornadohelmets.hu/")
    """#scraping main links first:
    menu_links = _scrape_menu()
    log.info(f"Loaded {len(menu_links)} menu links . . .\n")
    time.sleep(2)
    collected_links = set()
    for link in menu_links:
            print(f"\nI am visiting the website: {link} . . .\n")
            page.goto(link, wait_until='load', timeout=100000)
            time.sleep(2)
            #checking if there is pagination in the page
            if not has_pagination(page):
                print("No pagination, going to next link...\n")
                collected_links.add(link)
                continue
            #getting the last number from the page
            last_page_num = get_last_page_number(page)
            print(f"The last page is: {last_page_num} . . .\n")
            #getting all the pages base on last paage and generating the rest of them
            reversed_page_links = scrape_pages_in_reverse(
                page=page,
                base_url=link,
                last_page=last_page_num
            )
            for url in reversed_page_links:
                collected_links.add(url)
                print(f"\nUrl: {url} saved to the list. . .\n")
            all_links_list = list(collected_links) 
            save_links_to_json(all_links_list, "tornadohelmets/tornadohelmets_page_links.json")
            print(f"\nSaved {len(all_links_list)} unique links to the json file. . .\n")
    #scraping products links from the page links
    time.sleep(2)
    log.info(f"\nScraping products from pages has began. . .\n")
    scrape_product_from_pages(
        page=page,
        json_filename="tornadohelmets/tornadohelmets_page_links.json",
        output_jsonfile="tornadohelmets/tornadohelmets_products_links.json"
    )
    time.sleep(2)
    log.info("\n Scarping product infromation has began. . .\n")"""
    #scarping products text from product links
    scrape_text_from_product(
        page=page,
        input_json="tornadohelmets/tornadohelmets_products_links.json",
        output_json="tornadohelmets/tornadohelmets_final_output.json"
    )
    #cleaning the empty desc if there is some in the file
    remove_empty_desc_objects(
        'tornadohelmets/tornadohelmets_final_output.json',
        'tornadohelmets/tornadohelmets_final_output_clean.json')

    browser.close()