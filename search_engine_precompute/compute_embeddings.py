from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import *
import sqlite3
from sqlite3 import Connection
from flask_cors import CORS
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModel
from transformers import BertModel, BertTokenizer
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import tensorflow as tf

nltk.download('punkt')
nltk.download('stopwords')

path = "nlpaueb/legal-bert-small-uncased"
# path = 'nlpaueb/legal-bert-base-uncased'

bert_tokenizer = AutoTokenizer.from_pretrained(path)
bert_model = AutoModel.from_pretrained(path)

bert_model.eval()


def get_bert_embedding(text):
    inputs = bert_tokenizer(
        text, return_tensors="pt", max_length=512, truncation=True
    )
    outputs = bert_model(**inputs)
    return outputs.last_hidden_state.mean(dim=1)


def bert_score_sequence(text1, text2):
    embedding1 = get_bert_embedding(text1)
    embedding2 = get_bert_embedding(text2)
    similarity = cosine_similarity(
        embedding1.detach().numpy(), embedding2.detach().numpy()
    )[0][0]
    return similarity

conn = sqlite3.Connection('./congress-data_v2.1.db')
cur = conn.cursor()

drop = "drop table if exists bert_embeddings"
cur.execute(drop)
conn.commit()

create = """
    CREATE TABLE IF NOT EXISTS bert_embeddings (
        id INTEGER PRIMARY KEY,
        full_text_id INTEGER,
        embedding BLOB,
        FOREIGN KEY (full_text_id) REFERENCES full_texts(id)
    )
"""

cur.execute(create)
conn.commit()


import json

def remove_stopwords_and_stem(text):
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    stemmer = PorterStemmer()
    stemmed_words = [stemmer.stem(word) for word in tokens if word not in stop_words]
    return " ".join(stemmed_words)


def tensor_to_json(tensor):
    return json.dumps(tensor.detach().numpy().tolist())


insert = """insert into bert_embeddings (embedding, full_text_id) values (?, ?)"""

df = pd.read_sql_query(f"""
    select 
        id, 
        title || ' ' || substr(coalesce(text, ''), 1, 800) as passage1, 
        title || ' ' || substr(coalesce(text, ''), 600, 1400) as passage2,
        title || ' ' || substr(coalesce(text, ''), 1200, 2000) as passage3,   
        title || ' ' || substr(coalesce(text, ''), 1800, 2600) as passage4,   
        title || ' ' || substr(coalesce(text, ''), 2400, 3200) as passage5  
    from full_texts
""", conn, chunksize=5)

for i, chunk in enumerate(df):
    print('Processing:', i)
               
    chunk['passage1'] = chunk.passage1.apply(remove_stopwords_and_stem)
    chunk['passage2'] = chunk.passage2.apply(remove_stopwords_and_stem)
    chunk['passage3'] = chunk.passage3.apply(remove_stopwords_and_stem)
    chunk['passage4'] = chunk.passage4.apply(remove_stopwords_and_stem)
    chunk['passage5'] = chunk.passage5.apply(remove_stopwords_and_stem)

    chunk['passage1_embeddings'] = chunk.passage1.apply(get_bert_embedding).apply(tensor_to_json)
    chunk['passage2_embeddings'] = chunk.passage2.apply(get_bert_embedding).apply(tensor_to_json)
    chunk['passage3_embeddings'] = chunk.passage3.apply(get_bert_embedding).apply(tensor_to_json)
    chunk['passage4_embeddings'] = chunk.passage4.apply(get_bert_embedding).apply(tensor_to_json)
    chunk['passage5_embeddings'] = chunk.passage5.apply(get_bert_embedding).apply(tensor_to_json)
    
    df_embeddings = pd.melt(
        chunk, id_vars=['id'], 
        value_vars=['passage1_embeddings', 'passage2_embeddings', 'passage3_embeddings', 'passage4_embeddings', 'passage5_embeddings'],
        value_name='passage_embedding'
    )
    
    cur.executemany(insert, df_embeddings[['passage_embedding', 'id']].values)
    conn.commit()


# import torch
# import ast

# for row in df.iterrows():
#     e = get_bert_embedding(remove_stopwords_and_stem('china'))
#     # # e2 = pd.read_sql('select embedding from bert_embeddings', conn).values[0][0]
#     df['hydrated'] = df.passage1_embeddings.apply(lambda x: torch.nn.functional.cosine_similarity(e, torch.Tensor(np.array(ast.literal_eval(x)))))
#     # # Compute cosine similarity using PyTorch
#     # cosine_sim = torch.nn.functional.cosine_similarity(e, torch.Tensor(np.array(ast.literal_eval(e2))))
#     # cosine_similarity(e, torch.tensor(ast.literal_eval(e2)).detach().numpy())
#     # cosine_sim