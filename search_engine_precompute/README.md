These notebooks generate BERT embeddings for the bill text in our SQLite database. They should be run after the notebooks in the download_bills directory.

## compute_embeddings.py

This file will generate bert embeddings for all bills in the SQLite database and store them as a separate table in the same database. It may take over 24 hours to run. For this reason, it has been configured to use minimal memory, so it can run slowly and quietly in the background. Originally, this notebook was run on a cheap Digital Ocean droplet. 

!!! Important! This notebook should have stored each embedding as a serialized NumPy array, but it mistakenly stored the embedding as a text string. This took up double the space it should have, and leaded to slower processing. If you are seeking to replicate this database, you should ensure that a pickled/serialized NumPy array is correctly stored as a BLOB type in the SQLite database. (It may also be wise to consider using a specialized vector database for this like pgvector, which is included in PostgreSQL.)

## change_to_blob.ipynb

This notebook converted the embeddings to the correct format, as outlined above.