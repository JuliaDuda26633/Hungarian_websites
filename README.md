# Hungarian Websites Scraping

This repository contains web scraping scripts for various Hungarian websites. Each folder contains dedicated scripts to extract data (such as product links, descriptions, blog posts, etc.) using Playwright and Python.

## Folder Structure

- **jaszmotor**  
  Contains scripts for scraping [jaszmotor.hu](https://jaszmotor.hu).

- **motozem**  
  Contains scripts for scraping [motozem.hu](https://www.motozem.hu).

- **pardi**  
  Contains scripts for scraping [pardi.hu](https://pardi.hu).

- **totalbike**  
  Contains scripts for scraping [totalbike.hu](https://totalbike.hu).

- **tornadohelmets**  
  Contains scripts for scraping a website related to helmets.[tornadohelmets.hu](https://www.tornadohelmets.hu/).

- **mototoazis**
Contains scripts for scraping [mototoazis.hu](https://www.motoroazis.hu/)

## Requirements

- **Python 3.8+**
- **[Playwright](https://playwright.dev/python/)**  
  Install via pip:
  ```bash
  pip install playwright
  playwright install

## Checkpointing
Some scripts include checkpointing mechanisms. In case the scraping process is interrupted or encounters an error, these scripts can resume processing from the last saved checkpoint.

## License
This project is licensed under the MIT License.

