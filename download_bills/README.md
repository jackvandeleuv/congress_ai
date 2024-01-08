The notebooks in this directory download the corpus of Congress data and process them into a SQLite database, which is stored on the Django web server.

## GovInfoCrawler.ipynb

Run this file first. It will pull all available bills, summaries, and metadata from the GovInfo website.

## xml_to_sql.ipynb

This file will take a long time to run. It processes the raw XML data from the documents scraped in the previous step into a structure format, stored in an indexed format in SQLite. Some reconfiguration of the file paths may be required based on your local directory structure. 

## index_bm25.ipynb

This file configures the SQLite database created in the previous step for FTS / BM25 search, which enables efficient search across different text fields.