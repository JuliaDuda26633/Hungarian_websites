import urllib.parse
from playwright.sync_api import sync_playwright, Page
import time
import logging as log
import json
import urllib

log.basicConfig(level=log.INFO)
selectors = {
    'last_page' : 'body > div.container.border.rovat-container > div.cikk-torzs > div > nav > ul > li:nth-child(5) > a',
    'post_link' : 'div.blog-poszt > h2 > a',
    'post_link_other' : 'h4.cim a',
    'post_title' : '#content > div.cikk-header-container > div > div > div > h1 > span',
    'post_text' : 'div.cikk-torzs'
}

def _remove_dex(json_filename: str) -> list[str]:
    links = load_links_from_json(json_filename)
    log.info("JSON file was loaded . . .\n")
    cleaned_links = []
    for link in links: 
        url = urllib.parse.unquote(link)
        if url.count('http') > 1:
            parts = url.split('http')
            url = 'http' + parts[-1]
        cleaned_links.append(url)
        log.info("Clean url added to the list . . . \n")
    save_links_to_json(cleaned_links, "clear_totalbike_posts.json")
    log.info(f"Finished saving clean links to the new file. Cleaned urls: {len(cleaned_links)}")
    return cleaned_links

def generate_pagination_links(base_url: str, last_page: int) -> list[str]:
    links = []
    for p in range(last_page, -1, -1):
        if "?" in base_url:
            url = f"{base_url}&p={p}"
        else:
            url = f"{base_url}?p={p}"
        links.append(url)
    return links

def _scrape_post(page):
    log.info("Scraping post links\n")
    product_links = page.query_selector_all(selectors['post_link'])
    links = [link.get_attribute('href') for link in product_links if link.get_attribute('href')]
    log.info(f"Found {len(links)} post links.")
    print(f"Post links:\n {links} \n")
    return links

def scrape_post_title(page: Page) -> str:
    """
    Scrapes the post title from the current post page.
    Adjust the selector to match the actual HTML.
    """
    title_element = page.query_selector(selectors["post_title"])
    if title_element:
        return title_element.inner_text().strip()
    return ""

def scrape_post_text(page: Page) -> str:
    """
    Scrapes the post text from the currently loaded post page.
    Expects an element matching selectors['post|_text'].
    Returns the text content as a string, or an empty string if not found.
    """
    desc_element = page.query_selector(selectors["post_text"])
    if desc_element:
        return desc_element.inner_text().strip()
    return ""

def scrape_post_from_pages(page: Page, json_filename: str) -> list[str]:
    """
    1. Reads a list of URLs from `json_filename`.
    2. For each URL, goes to that page and scrapes product links (using _scrape_post).
    3. Collects all product links in a set (to avoid duplicates).
    4. Returns a list of all unique product links.
    """
    data = load_links_from_json("totalbike_pages.json")
    log.info(f"Loaded {len(data)} links from {json_filename}")
    all_post_links = set()
    for url in data:
        log.info(f"Visiting: {url}")
        try:
            page.goto(url, timeout=100000, wait_until='load')
            time.sleep(2)
        except Exception as e:
            log.error(f"Error loading {url}: {e}")
            raise Exception(f"Error loading {url}: {e}")
            #continue #unacceptable way of handling errors
        post_links = _scrape_post(page)
        log.info(f"Scraped {len(post_links)} posts on this page.\n")
        for plink in post_links:
            all_post_links.add(plink)
    final_list = list(all_post_links)
    log.info(f"Total unique posts links after scraping all pages: {len(final_list)}")

    return final_list

def scrape_text_from_post(page: Page, input_json: str, output_json: str):
    """
    1. Loads a list of product URLs from input_json.
    2. Visits each product page, scrapes the product title and description.
    3. If the description is empty, the product is skipped.
    4. Collects the data in a list of dictionaries with keys: 'url', 'title', and 'desc'.
    5. Saves the list as JSON in output_json.
    """
    post_links = load_links_from_json(input_json)
    log.info(f"Loaded {len(post_links)} post links from {input_json}.")
    results = [] 
    for link in post_links:
        log.info(f"Visiting post page: {link}")
        try:
            page.goto(link, timeout=100000, wait_until='load') 
            time.sleep(2)
        except Exception as e:
            log.error(f"Timeout or error loading {link}: {e}")
            raise Exception(f"Timeout or error loading {link}: {e}")
            # continue # this is a terrible way of handling errors if you don't track what are you skipping
        title = scrape_post_title(page)
        desc = scrape_post_text(page)
        log.info(f"Scraped post data: title length: {len(title)} characters, description length: {len(desc)} characters.")

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
    with open(filename, "a", encoding="utf-8") as f:
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

    #getting all page links from the webside
    """base_url = "https://totalbike.hu/technika/nepperuzo/" 
    last_page = 22
    pagination_links = generate_pagination_links(base_url, last_page)
    save_links_to_json(pagination_links, "totalbike_pages.json")"""

    #getting all the posts from the web pages
    """totalbike_posts = scrape_post_from_pages(page,"totalbike_pages.json")
    save_links_to_json(totalbike_posts, "totalbike_posts.json")
    log.info(f"Saved {len(totalbike_posts)} posts links to json file.")"""

    #clearing the urls in json file and creating new clear version
    """_remove_dex("totalbike_posts.json")"""

    #scrapping all the data from the blog
    scrape_text_from_post(
        page,
        input_json= "clear_totalbike_posts.json",
        output_json= "totalbike_final_output.json"
    )

    #testing
    """goto(page,"https://totalbike.hu/technika/nepperuzo/2018/02/20/penge_de_megbizhato_elmenymotor/")
    text = page.locator(selectors["post_text"]).all_inner_texts()
    print(text)
    test1 = scrape_post_text(page)
    print(test1)"""

    time.sleep(10)
    browser.close()