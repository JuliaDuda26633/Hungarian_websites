from playwright.sync_api import sync_playwright, Page
import time
import logging as log
import json

log.basicConfig(level=log.INFO)

selectors = {
    'product_links' : 'div.row > div > div > h3 a',
    'product_title' : '#productnew > div > h3 *',
    'product_desc' : '#productnew > section *',
    'pagination' : '#pagination-container'
}

def has_pagination(page: Page) -> bool:
    element = page.query_selector(selectors['pagination'])
    return element is not None

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

    #testing 
    test = page.goto("https://jaszmotor.hu/kategoria/235/robogok")
    

    browser.close()
