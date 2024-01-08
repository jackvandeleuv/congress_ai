from typing import *
import sqlite3
import pandas as pd
import numpy as np
import os
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import ast
import time
import pickle

class QueryBuilder:
    """
    This class provides a structured way to build search queries for the SQLite database.    
    """
    def __init__(self, conn) -> None:
        self.__select = []
        self.__equalities = []
        self.__exact_matches = []
        self.__search_query = ''
        self.__limit = ''
        self.__conn = conn


    def set_search_query(self, search_query: str) -> None:
        """
        Add a search query, which will be matched against the documents in the database.
        """
        assert search_query is not None, 'Query cannot be None.'
        self.__search_query = search_query


    def set_limit(self, limit: int | None) -> None:
        """
        Limit the bills to be returned.
        """
        assert type(limit) == int, 'Limit must be an integer.'
        if limit is None:
            self.__limit = None
        else:
            self.__limit = limit


    def add_equality(self, column: str, value: str, operator: str) -> None:
        """
        Add a WHERE clause term. The column and value are compared with the operator.
        """
        assert type(column) == str, 'Column must be str.'
        assert operator in ['=', '<', '>', '<=', '>='], 'Unrecognized operator.'
        self.__equalities.append({'column': column, 'value': value, 'operator': operator}) 


    def add_select(self, value: str) -> None:
        """
        Add columns to return in the SELECT clause.
        """
        assert type(value) == str, 'Value must be str.'
        assert value not in self.__select, 'Value already in select.'
        self.__select.append(value)


    def add_exact_match_string(self, string: str) -> None:
        """
        Add substring which must match the bill text, title, or summary exactly.
        """
        assert type(string) == str, 'String must be str.'
        self.__exact_matches.append(string)


    def __assemble_where(self) -> str:
        """
        Internal method for assembling the WHERE clause.
        """
        where = " where congress_bm25 match ? "
        for equality in self.__equalities:
            where = where + ' and ' + equality['column'] + ' ' + equality['operator'] + ' ?'

        for _ in self.__exact_matches:
            where = where + " and (bs.summary_text like ? or ft.text like ? or ft.title like ?)"

        # This can filter the results down to only HR bills, for comparability with Congress.gov during CRS evaluation.
        # where = where + " and (ft.file_chamber = 'hr') "

        return where


    def __assemble_select(self) -> str:
        """
        Internal method for assembling the SELECT clause.
        """
        return 'select ' + ', '.join(self.__select)
    

    def __assemble_params(self) -> List[str]:
        """
        Internal method for collecting the parameters to insert into the sanitized SQLite query.
        """
        params = [' OR '.join(list(set(self.__search_query.split(' '))))]

        params.append(str(self.__limit))

        # params = params + [equality['value'] for equality in self.__equalities]
        # for string in self.__exact_matches:
        #     params = params + (['%' + string + '%'] * 3)

        params.append(str(self.__limit))

        return params


    def evaluate(self) -> pd.DataFrame:
        """
        Evaluate the assembled query and retrieve the results.
        """
        # select = self.__assemble_select()
        # where = self.__assemble_where()
        where = " where ft.file_chamber = 'hr' "

        query = 'select ft.id as id ' + '\n' + """ from full_texts ft  
         join (
            select ft_id, bm25(congress_bm25) as score
            from congress_bm25
            where congress_bm25 match ? 
            order by score
            limit ?
        ) as bm25_ft on ft.id = bm25_ft.ft_id """ + '\n' + where + '\n' + f' limit ? '

        params = self.__assemble_params()

        return pd.read_sql_query(query, self.__conn, params=params)


class SearchEngine:
    """
    The search engine class allows for searching across all bills to retrieve summaries,
    and searching within one bill to retrieve matching text passages.
    """
    def __init__(self):
        legal_bert_path = "nlpaueb/legal-bert-small-uncased"
        sentence_bert_path = "sentence-transformers/msmarco-MiniLM-L6-cos-v5"

        # For retrieving full text chunks
        self.__max_chunks_to_bert_score = 25

        # For retrieving summaries
        self.__bm25_ranking_depth = 150  
        self.__reranking_depth = 150   
        self.__bert_tokenizer = AutoTokenizer.from_pretrained(legal_bert_path)
        self.__bert_model = AutoModel.from_pretrained(legal_bert_path)
        
        self.__sentence_bert_tokenizer = AutoTokenizer.from_pretrained(sentence_bert_path)
        self.__sentence_bert_model = AutoModel.from_pretrained(sentence_bert_path)

        self.__bert_model.eval()
        self.__stemmer = PorterStemmer()
        nltk.download('stopwords')
        self.__stop_words = set(stopwords.words('english'))


    def __remove_stopwords_and_stem(self, text):
        """
        Remove stopwords and stem using the SearchEngine's stemmer.
        """
        tokens = word_tokenize(text)
        stemmed_words = [self.__stemmer.stem(word) for word in tokens if word not in self.__stop_words]
        return " ".join(stemmed_words)
    

    def remove_stopwords(self, text):
        """
        Remove stopwords as identified by SearchEngine's stopword list.
        """
        tokens = word_tokenize(text)
        tokens = [word for word in tokens if word not in self.__stop_words]
        return " ".join(tokens)
    

    def __chunk_text(self, text, chunk_size, overlap) -> List[str]:
        """
        Separate out a string into chunks. Chunk size determines the number of tokens.
        Overlap is the number of shared tokens between two adjacent chunks.
        """
        words = text.split(' ')
        if chunk_size <= overlap:
            raise ValueError("Chunk size must be larger than overlap size.")
        
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)
            if i + chunk_size >= len(words):
                break

        return chunks
    

    @staticmethod
    def get_conn() -> sqlite3.Connection:
        """
        Centralized method for generating new SQLite DB connections.
        """
        LATEST_VERSION_PATH = './congress-data_v2.4.db'
        if not os.path.exists(LATEST_VERSION_PATH):
            raise FileNotFoundError(f"""
                Database file not found at {LATEST_VERSION_PATH}. 
                You may need to update your database. 
                The latest version is available at: https://drive.google.com/drive/u/2/folders/1JSDAVjIinG_7PVEt_J8Tam7Uiz2ctzvn
            """)
        return sqlite3.Connection(LATEST_VERSION_PATH)


    def __get_full_text_chunks(self, query: str, full_text_id: int) -> pd.DataFrame:
        """
        Given a search query and a full text id, return matching passages from the identified bill.
        """       
        query = self.remove_stopwords(query)

        conn = SearchEngine.get_conn()
        df = pd.read_sql_query('select text from full_texts where id = ?', conn, params=(full_text_id,))
        
        chunks = self.__chunk_text(df.text.values[0], 150, 15)

        chunks = [x.replace('\t', ' ') for x in chunks]

        scorable_chunks = [self.remove_stopwords(chunk) for chunk in chunks]

        # Use two stage retreival if there are too many chunks
        if len(scorable_chunks) > self.__max_chunks_to_bert_score:             
            word_vector_scores = [self.__score_word_based_vectors(query, chunk) for chunk in scorable_chunks]

            # Sort chunks and scorable chunks based on the simple word-based vector scores
            chunks = sorted(zip(chunks, word_vector_scores), key=lambda x: x[1], reverse=True)
            scorable_chunks = sorted(zip(scorable_chunks, word_vector_scores), key=lambda x: x[1], reverse=True)

            # Convert back to list and select the top n
            chunks = list(chunks)[:self.__max_chunks_to_bert_score]
            scorable_chunks = list(scorable_chunks)[:self.__max_chunks_to_bert_score]

            chunks = [x[0] for x in chunks]
            scorable_chunks = [x[0] for x in scorable_chunks]

        scores = [self.__bert_score_sequence(query, chunk) for chunk in scorable_chunks]

        return list(sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True))


    def __get_bert_embedding(self, text: str, tokenizer, model):
        """
        Generate BERT embeddings specified model and tokenizer.
        """
        assert type(text) == str, 'Type of text must be str.'
        inputs = tokenizer(
            text, return_tensors="pt", max_length=512, truncation=True
        )
        outputs = model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).detach().numpy()


    def __bert_score_sequence(self, text1, text2):
        """
        Given two strings, generate a BERT similarity score with Sentence BERT.
        """
        assert type(text1) == str, 'Type of text1 must be str.'
        assert type(text2) == str, 'Type of text2 must be str.'

        embedding1 = self.__get_bert_embedding(text1, self.__sentence_bert_tokenizer, self.__sentence_bert_model)
        embedding2 = self.__get_bert_embedding(text2, self.__sentence_bert_tokenizer, self.__sentence_bert_model)
        similarity = np.dot(
            embedding1, np.transpose(embedding2)
        )[0][0]
        return similarity


    def __search_summaries(self, params: Dict[str, Any], conn) -> List[Dict]:
        """
        PARAMS = {
            'query': '',
            'number_to_return': <int>,
            'exact_match_strings': [],  
            'date_range': {
                'start_year': 1970,
                'start_month': 1,
                'start_day': 1,
                'end_year': 2050,
                'end_month': 12,
                'end_day': 31
            },
            'get_sponsors': False,
            'chamber': 'any',
            'require_bipartisan': False
        }
        """

        query_builder = QueryBuilder(conn)

        if params['chamber'] == 'U.S. House of Representatives' or params['chamber'] == 'U.S. Senate':
            query_builder.add_equality('publisher', params['chamber'], '=')
        elif params['chamber'] == 'any':
            pass
        else:
            raise ValueError('Unrecognized value for chamber parameter.')
        
        if 'date_range' in params:
            start_date = f"{params['date_range']['start_year']}-{params['date_range']['start_month']}-{params['date_range']['start_day']}"
            query_builder.add_equality('ft.date', start_date, '>=' )

            end_date = f"{params['date_range']['end_year']}-{params['date_range']['end_month']}-{params['date_range']['end_day']}"
            query_builder.add_equality('ft.date', end_date, '<=', )

        # Remove punctuation
        query = params['query'] \
            .replace(',', ' ').replace('+', ' ').replace('.', ' ').replace("'", ' ')
        query = self.__remove_stopwords_and_stem(query)
        query_builder.set_search_query(query)

        for string in params['exact_match_strings']:
            query_builder.add_exact_match_string(string)

        if params['require_bipartisan'] is True:
            query_builder.add_equality('ft.multiple_parties', True, '=')

        select_cols = [
            'ft.id',
            'coalesce(bs.summary_text, substr(ft.text, 1, 300)) as summary_text', 
            'ft.title', 
            'ft.text',
            'ft.official_title',
            'ft.available_chunks',
            'ft.multiple_parties',
            'ft.generated_url',
            'ft.file_stage as stage_in_process',
            'ft.file_number as bill_number',
            'ft.file_chamber as bill_type',
            'ft.file_congress as congress',
            'ft.date',
            'ft.legis_type',
            'ft.committee_name',
            'ft.publisher',
            'ft.current_chamber',
            'ft.session'
        ]

        for col in select_cols:
            query_builder.add_select(col)

        query_builder.set_limit(int(self.__bm25_ranking_depth))

        results = query_builder.evaluate()

        return results.to_dict(orient='records')


    def __retrieve_sponsors(self, full_text_id, conn):
        """
        For a given bill, retrieve sponsors and cosponsors.
        """
        cur = conn.cursor()
        select = "select loc_id, name, full_name, chamber, party from sponsors where bill_sponsored = ?"
        cur.execute(select, (full_text_id,))
        sponsors = cur.fetchall()
        result = []
        for s in sponsors:
            result.append({'loc_id': s[0], 'name': s[1], 'full_name': s[2], 'chamber': s[3], 'party': s[4]})
        return result
    

    def __get_precomputed_embeddings(self, ft_ids: np.array, conn) -> pd.DataFrame:
        """
        Retrieve precomputed BERT embeddings from the SQLite database.
        """
        return pd.read_sql_query(f"""
            select full_text_id as id, embedding_blob as embedding 
            from bert_embeddings 
            where full_text_id in ({','.join('?' * len(ft_ids))}) 
        """, conn, params=ft_ids)


    def __rerank_with_bert(self, documents: List[Dict], params: Dict[str, Any], conn) -> List[Dict]:
        """
        Reorder the given list of documents using BERT score. 
        """
        embeddings = self.__get_precomputed_embeddings(tuple([str(d['id']) for d in documents]), conn)

        # clean_query = self.__remove_stopwords_and_stem(params['query'])

        query_embedding = self.__get_bert_embedding(params['query'], self.__bert_tokenizer, self.__bert_model)

        embeddings['score'] = embeddings.embedding.apply(
            lambda x: np.dot(query_embedding, np.transpose(pickle.loads(x)))
        )

        scores = embeddings.groupby('id') \
            .score \
            .mean() \
            .sort_values(ascending=False) \
            .reset_index()
                                
        sorted_ids = scores['id'].tolist()
        return list(sorted(documents, key=lambda x: sorted_ids.index(x['id'])))
    

    def __get_full_summary_data(self, documents: List[Dict]) -> List[Dict]:
        """
        Get the full set of data and metadata for a list of bills. Use this method at the end of the search process
        once the final, narrowed down set of top results have been determined.
        """
        conn = self.get_conn()

        sorted_ids = [d['id'] for d in documents]

        query = """
            select 
                ft.id,
                coalesce(bs.summary_text, substr(ft.text, 1, 300)) as summary_text, 
                ft.title, 
                ft.official_title,
                ft.available_chunks,
                ft.multiple_parties,
                ft.generated_url,
                ft.file_stage as stage_in_process,
                ft.file_number as bill_number,
                ft.file_chamber as bill_type,
                ft.file_congress as congress,
                ft.date,
                ft.legis_type,
                ft.committee_name,
                ft.publisher,
                ft.current_chamber,
                ft.session
            from full_texts ft left join bill_summaries bs 
                on ft.summaries_match = bs.id
            where ft.id in (
        """

        query = query + ' '.join(['?,' for _ in range(len(documents))])
        query = query[:-1] + ')'

        df = pd.read_sql_query(query, conn, params=sorted_ids)
        results = df.to_dict(orient='records')

        return list(sorted(results, key=lambda x: sorted_ids.index(x['id'])))
    


    def __score_word_based_vectors(self, text1: str, text2: str):
        """
        Perform simple (non-deep learning-based) cosine similarity calcuation to determine similarity between two texts.
        Each text is a vector, where unique word is a dimension, the value of which is the frequency of that word in the
        text.
        """
        tokens1 = text1.split(' ')
        tokens2 = text2.split(' ')

        vocabulary = set(tokens1 + tokens2)  

        vector1 = [0] * len(vocabulary)
        vector2 = [0] * len(vocabulary)

        word_to_index = {word: index for index, word in enumerate(vocabulary)}

        for word in tokens1:
            vector1[word_to_index[word]] += 1

        for word in tokens2:
            vector2[word_to_index[word]] += 1

        vector1 = np.array(vector1).reshape(1, -1)
        vector2 = np.array(vector2).reshape(1, -1)

        return np.dot(vector1, np.transpose(vector2))
    

    def retrieve_full_text_chunks(self, params: Dict[str, Any], full_text_id: int) -> List[Dict]:
        """
        Public method for getting matching passages within a bill.
        """
        result = self.__get_full_text_chunks(params['query'], full_text_id)
        return result[:params['number_to_return']]


    def retrieve_summary(self, params: Dict[str, Any]) -> List[Dict]:
        """
        Public method for searching for matching bills and their summaries. 
        """
        default_params = {
            'query': '',
            'number_to_return': 5,
            'exact_match_strings': [],  
            'date_range': {
                'start_year': 1970,
                'start_month': 1,
                'start_day': 1,
                'end_year': 2050,
                'end_month': 12,
                'end_day': 31
            },
            'get_sponsors': False,
            'chamber': 'any',
            'require_bipartisan': False
        }

        conn = SearchEngine.get_conn()

        for key, value in default_params.items():
            if key not in params:
                params[key] = value

        documents: List[Dict] = self.__search_summaries(params, conn)

        top_n = documents[:self.__reranking_depth]
        top_n = self.__rerank_with_bert(top_n, params, conn)

        documents = top_n + documents[self.__reranking_depth:]

        documents = documents[:params['number_to_return']]

        documents = self.__get_full_summary_data(documents)

        if params['get_sponsors'] is True:
            for i, document in enumerate(documents):
                sponsors = self.__retrieve_sponsors(document['ft_id'], conn)
                documents[i]['sponsors'] = sponsors

        return documents
