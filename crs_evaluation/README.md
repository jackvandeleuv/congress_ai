The files in this directory are used to run CRS-based search evaluation, as outlined in the final project report.

# get_crs_reports.ipynb

This file downloads and processes PDFs of individual CRS reports. To find the links of the PDFs to download, go to the CRS website, and download all available reports, which will come back as a csv named SearchResults.csv. 

# crs_transform.ipynb

This file is an alternate method for processing PDFs of individual CRS reports, which captures Congress session information along with bill codes. Run this script after downloading all desired CRS reports using get_crs_reports.

# crs_evaluation.ipynb

After running the previous two files, you can run this file to generate scores for Congress.gov and CongressGPT's respective search engines. Before running this notebook, you should run each query you want to test through Congress.gov's advanced search portal (following the instructions in the notebook), and download the csv off results from Congress.gov. These should be placed in the congress_gov_searches file.