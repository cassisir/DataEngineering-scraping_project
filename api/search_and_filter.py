from elasticsearch import Elasticsearch

es_client = Elasticsearch("http://elasticsearch:9200/")
index_name = "movies_index"
doc_type = "movie"


def apply_filters(collection, genre_request, sort_by_request, sort_order_request, exclude_not_rated, search_query):
    query = genre_filter(genre_request)                         # Requete filtre genre
    sort = sort_filter(sort_by_request, sort_order_request)     # Requete filtre tri + ordre du tri
    researched_movies = search_movies(search_query)             # Requete recherche elasticsearch (retourne les ids des films)
    
    if exclude_not_rated:
        query[sort.get('field')] = {'$ne': 'not rated'}         # Exclure les films non notés si checkbox coché
    
    if search_query:
        query['_id'] = {'$in': researched_movies}               # On récupère les informations des ids correspondant dans la base de données Mongo
    
    movies = list(collection.find(query).sort(sort.get('field'), sort.get('order'))) # Sélection des films correspondants aux requetes
    return movies

def genre_filter(selected_genre):
    # Genre des films à sélectionner
    genre_filter = {'genre': selected_genre} if selected_genre else {}
    return genre_filter

def sort_filter(sort_by, sort_order):
    # Champs selon lequel trier
    if sort_by == 'press_rating':
        sort_field = 'ratings.press'
    elif sort_by == 'spectators_rating':
        sort_field = 'ratings.spectators'
    else:
        sort_field = 'date'

    # Sens du tri
    order = 1 if sort_order == 'ascending' else -1

    return {'field':sort_field, 'order':order}

# Recherche texte avec elasticsearch
def search_movies(search_query):
    query = {
        "query": {
            "multi_match": {                                        # Retourne tous les films
                "query": search_query,                              # contenant la string search_query
                "fields": ["title", "synopsis", "cast.name"],       # dans leur titre, leur synopsis, ou leur cast
                "type": "phrase_prefix",                            # Recherche de phrase sur les prefixes des mots
            }
        }
    }
    search_results = es_client.search(index=index_name, doc_type=doc_type, body=query, size=2000)
    movies_results = search_results['hits']['hits']
    movies_ids = [movie['_id'] for movie in movies_results] # On récupère les ids des films correspondant à la recherche
    return movies_ids
