from playwright.sync_api import sync_playwright, Page
import time
import logging as log
import json

log.basicConfig(level=log.INFO)

selectors = {
    'product_links' : 'h3.name a',
    'product_title' : '#top-and-menu > div > div > div.col-xs-12.col-sm-12.col-md-9.homebanner-holderr > div.productnew > div.row.wow_.fadeInUp_.single-product.p > h3',
    'product_desc' : 'span.prtext',
    'pagination' : '#top-and-menu > div > div > div.col-xs-12.col-sm-12.col-md-9.homebanner-holderr > div.search-result-container > div.col.col-sm-6.col-md-6.text-right > div'
}

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
    desc_element = page.locator(selectors["product_desc"])
    if desc_element:
        return desc_element.text_content().strip()
    return ""

def scrape_pagination_links(page: Page, input_json: str, output_json: str) -> list[str]:
    """
    Loads a list of URLs from `input_json`.
    For each URL, visits the page and checks for a pagination element using the selector defined in selectors['pagination'].
    If pagination is present, retrieves all <a> elements within the pagination container and extracts their href attributes.
    If no pagination is found, it skips that page.
    Finally, all collected pagination links are saved in one JSON file (`output_json`) and returned.
    """
    urls = load_links_from_json(input_json)
    log.info(f"Loaded {len(urls)} links from {input_json}")
    collected_links = []
    for url in urls:
        log.info(f"Visiting: {url}")
        log.info(f"Saving base url to list. . .\n")
        collected_links.append(url)
        try:
            page.goto(url, timeout=60000)
            page.wait_for_load_state("load")
        except Exception as e:
            log.error(f"Error loading {url}: {e}")
            raise Exception(f"Error loading {url}: {e}")
        pagination_container = page.query_selector(selectors["pagination"])
        if pagination_container:
            log.info("Pagination found on this page.")
            pagination_links = page.query_selector_all(f"{selectors['pagination']} a")
            for link_element in pagination_links:
                href = link_element.get_attribute("href")
                if href:
                    full_url = f"https://jaszmotor.hu/{href}"
                    if full_url not in collected_links:
                        collected_links.append(full_url)
        else:
            log.info("No pagination on this page. Moving to the next URL.")
    save_links_to_json(collected_links, output_json)
    log.info(f"Saved {len(collected_links)} pagination links to {output_json}")
    
    return collected_links

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
            full_url = f"https://jaszmotor.hu/{plink}"
            all_post_links.add(full_url)
    final_list = list(all_post_links)
    log.info(f"Total unique posts links after scraping all pages: {len(final_list)}")
    save_links_to_json(final_list, output_jsonfile)

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
    

    #testing
    scrape_text_from_product(
        page = page,
        input_json = "jaszmotor/jaszmotor_all_products_list.json",
        output_json = "jaszmotor/jaszmotor_finall_output.json"
    )
    

    browser.close()
