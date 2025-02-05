from playwright.sync_api import sync_playwright, Page
import time
import logging as log
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import json

log.basicConfig(level=log.INFO)
selectors = {
    'main_menu': '#category-nav a.nav-link',
    'product' : '#snapshot_vertical a.img-thumbnail-link',
    'pagination_last_page' : 'a.page-link.page-last',
    'pagination' : 'ul.pagination.m-0',
    'product_desc' : 'span.product-desc',
    'product_title' : '#product > div > div > div.col-12.col-md-6.product-page-left > h1',
    'blog_links' : 'h5.card-title a',
    'blog_head' : '#body > div.page-wrap > main > div > div > section > div > div.page-head > h1',
    'blog_text' : 'div.information-item-description *'
}

def _scrape_menu():
    elements = page.query_selector_all(selectors['main_menu'])
    links = [element.get_attribute('href') for element in elements if element.get_attribute('href')]
    log.info(f"Found {len(links)} main menu links.")
    print(f"Main menu links:\n {links} \n")
    return links

def _scrape_product(page):
    log.info("Scraping product links\n")
    product_links = page.query_selector_all(selectors['product'])
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

def _scrape_blog_link(page):
    log.info("Scraping product links\n")
    product_links = page.query_selector_all(selectors['blog_links'])
    links = [link.get_attribute('href') for link in product_links if link.get_attribute('href')]
    log.info(f"Found {len(links)} products links.")
    print(f"Products links:\n {links} \n")
    return links

def scrape_products_from_pages(page: Page, json_filename: str) -> list[str]:
    """
    1. Reads a list of URLs from `json_filename`.
    2. For each URL, goes to that page and scrapes product links (using _scrape_product).
    3. Collects all product links in a set (to avoid duplicates).
    4. Returns a list of all unique product links.
    """
    with open(json_filename, "r", encoding="utf-8") as f:
        links_list = json.load(f)
    log.info(f"Loaded {len(links_list)} links from {json_filename}")
    all_product_links = set()
    for url in links_list:
        log.info(f"Visiting: {url}")
        page.goto(url, timeout=30000)  #30s timeout, adjust if needed
        product_links = _scrape_product(page)
        log.info(f"Scraped {len(product_links)} products on this page.")
        for plink in product_links:
            all_product_links.add(plink)
    final_list = list(all_product_links)
    log.info(f"Total unique product links after scraping all pages: {len(final_list)}")

    return final_list

def scrape_blog_from_pages(page: Page, json_filename: str) -> list[str]:
    """
    1. Reads a list of URLs from `json_filename`.
    2. For each URL, goes to that page and scrapes product links (using _scrape_product).
    3. Collects all product links in a set (to avoid duplicates).
    4. Returns a list of all unique product links.
    """
    with open(json_filename, "r", encoding="utf-8") as f:
        links_list = json.load(f)
    log.info(f"Loaded {len(links_list)} links from {json_filename}")
    all_product_links = set()
    for url in links_list:
        log.info(f"Visiting: {url}")
        page.goto(url, timeout=30000)  #30s timeout, adjust if needed
        product_links = _scrape_blog_link(page)
        log.info(f"Scraped {len(product_links)} products on this page.")
        for plink in product_links:
            all_product_links.add(plink)
    final_list = list(all_product_links)
    log.info(f"Total unique product links after scraping all pages: {len(final_list)}")

    return final_list

def scrape_blog_links(page) -> list[str]:
    """
    Scrapes all blog links from the blog homepage.
    It collects all <a> elements whose href attribute starts with '/blog/',
    converts relative URLs to absolute URLs, and returns a list of links.
    (Note: This version preserves duplicates.)
    """
    base_url = "https://www.motoroazis.hu/blog"
    page.goto(base_url)
    page.wait_for_load_state("load")
    anchors = page.query_selector_all("a[href^='/blog/']")
    links = []
    for a in anchors:
        href = a.get_attribute("href")
        if href:
            if href.startswith("/"):
                absolute_url = "https://www.motoroazis.hu" + href
            else:
                absolute_url = href
            links.append(absolute_url)
    
    unique_links = list(set(links))
    return unique_links

def scrape_blog_page(page: Page, url: str) -> dict:
    """
    Visits the given blog page URL, scrapes the title (using the 'blog_head' selector)
    and the full text (using the 'blog_text' selector), and returns a dictionary with:
       - url: the URL of the page,
       - title: the text of the blog head element,
       - text: the concatenated text from the blog text element.
    """
    log.info(f"Visiting blog page: {url}")
    page.goto(url, timeout=60000)  
    time.sleep(2)
    title = page.locator(selectors["blog_head"]).inner_text().strip()
    text_parts = page.locator(selectors["blog_text"]).all_inner_texts()
    full_text = "\n".join(part.strip() for part in text_parts if part.strip())
    return {
        "url": url,
        "title": title,
        "text": full_text
    }

def scrape_all_blog_pages(page: Page, links: list[str]) -> list[dict]:
    """
    Iterates over the list of blog page URLs, scrapes each page for its title and text,
    and returns a list of dictionaries with keys: 'url', 'title', and 'text'.
    """
    results = []
    for url in links:
        try:
            data = scrape_blog_page(page, url)
            results.append(data)
        except Exception as e:
            log.error(f"Error scraping {url}: {e}")
    return results

def scrape_product_description(page: Page) -> str:
    """
    Scrapes the product description from the currently loaded product page.
    Expects an element matching selectors['product_desc'].
    Returns the text content as a string, or an empty string if not found.
    """
    desc_element = page.query_selector(selectors["product_desc"])
    if desc_element:
        return desc_element.inner_text().strip()
    return ""

def scrape_descriptions_from_products(page: Page, input_json: str, output_json: str):
    """
    1. Loads a list of product URLs from `input_json`.
    2. Visits each product page, scrapes the product title and description.
    3. If the description is empty, the product is skipped.
    4. Collects the data in a list of dictionaries with keys: 'url', 'title', and 'desc'.
    5. Saves the list as JSON in `output_json`.
    """
    with open(input_json, "r", encoding="utf-8") as f:
        product_links = json.load(f)
    log.info(f"Loaded {len(product_links)} product links from {input_json}.")
    results = []  #
    for link in product_links:
        log.info(f"Visiting product page: {link}")
        try:
            page.goto(link, timeout=100000)  
        except Exception as e:
            log.error(f"Timeout or error loading {link}: {e}")
            continue
        title = scrape_product_title(page)
        desc = scrape_product_description(page)
        log.info(f"Scraped product data: title length: {len(title)} characters, description length: {len(desc)} characters.")

        if not desc.strip():
            log.info(f"Skipping product at {link} because description is empty.")
            continue
        product_data = {
            "url": link,
            "title": title,
            "desc": desc
        }
        results.append(product_data)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log.info(f"Saved scraped product data for {len(results)} products to {output_json}.")

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

def remove_page_param(url: str) -> str:
    """
    Removes 'page' parameters from the URL if present, e.g.:
    '...?page=11' => '...?'
    '...?foo=bar&page=2' => '...?foo=bar'
    Returns a "cleaned" URL to avoid the situation
    '?page=11?page=1'
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "page" in qs:
        qs.pop("page")
    new_query = urlencode(qs, doseq=True) 
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


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
    '''#testing 
    page.goto("https://www.motoroazis.hu/")
    print("Strona wczytana 1.")
    _scrape_menu()
    
    #testing 
    collected_links = []

    page.goto("https://www.motoroazis.hu/blog")

    last_page_num = get_last_page_number(page)
    print(f"The last page is: {last_page_num}")
    blog_pages = scrape_pages_in_reverse(
        page=page,
        base_url="https://www.motoroazis.hu/blog",
        last_page=last_page_num
    )
    collected_links.extend(blog_pages)

    save_links_to_json(collected_links, "blog_links_output.json")
    print(f"Saved {len(collected_links)} links to 'blog_links_output.json'")'''

    '''blog_links = scrape_blog_links_from_pages(
        page,
        "blog_links_output.json"
    )
    save_links_to_json(blog_links, "blog_pages_links.json")'''
    


    '''blog_links = scrape_blog_links(page)
    log.info(f"Found {len(blog_links)} blog links:")
    for link in blog_links:
        log.info(link)
    
    # Save the scraped links to JSON file
    save_links_to_json(blog_links, "blog_pages_links.json")
    log.info("Saved blog links to 'blog_pages_links.json'.")
    time.sleep(5)
    input_file = "blog_pages_links.json"  
    output_file = "blog_pages_output.json"
    blog_links = load_links_from_json(input_file)
    log.info(f"Loaded {len(blog_links)} blog page links from {input_file}")
    scraped_blog_data = scrape_all_blog_pages(page, blog_links)
    log.info(f"Scraped data from {len(scraped_blog_data)} blog pages")

    save_links_to_json(scraped_blog_data, output_file)
    log.info(f"Saved scraped blog data to {output_file}")'''


    '''#testing blog text
    page.goto("https://www.motoroazis.hu/blog/igy-valassz-tokeletes-motoros-csizmat-gyakorlati-utmutato-105")
    elements = page.locator(selectors['blog_head']).all_inner_texts()
    print(elements)
    test2 = page.locator(selectors['blog_text']).all_inner_texts()
    print(test2)'''

    '''#testing
    page.goto("https://www.motoroazis.hu/bukosisak_motoros_bukosisakok/zart_bukosisakok_54/arai-bukosisakok-153")
    _scrape_product(page)
    time.sleep(5)'''

    #testing
    input_file = "products_output.json"
    output_file = "product_descriptions.json"
    scrape_descriptions_from_products(page, input_file, output_file)




    '''
    menu_links = _scrape_menu()
    collected_links = set()
    for link in menu_links:
            print(f"\nI am visiting the website: {link}")
            page.goto(link)

            # 2) Sprawdzamy, czy na tej stronie jest paginacja
            if not has_pagination(page):
                print("No pagination, going to next link...")
                collected_links.add(link)
                continue

            # 3) Jeśli jest paginacja, pobieramy liczbę ostatniej strony
            last_page_num = get_last_page_number(page)
            print(f"The last page is: {last_page_num}")

            base_url_clean = remove_page_param(link)

            reversed_page_links = scrape_pages_in_reverse(
                page=page,
                base_url=base_url_clean,
                last_page=last_page_num
            )

            for url in reversed_page_links:
                collected_links.add(url)
                print(f" - {url}")
            all_links_list = list(collected_links) 
            save_links_to_json(all_links_list, "links_output.json")
            print(f"\nZapisano {len(all_links_list)} unikalnych linków do pliku links_output.json.")

    #testing
    product_links = scrape_products_from_pages(page, "links_output.json")

    save_links_to_json(product_links, "products_output.json")
    log.info(f"Saved {len(product_links)} product links to products_output.json")
    time.sleep(10)'''
    time.sleep(10)

browser.close()




