from itemadapter import ItemAdapter
from datetime import datetime
from pymongo import MongoClient
from elasticsearch import Elasticsearch


class TextPipeline:
    def process_item(self, item, spider):

    # Traitement des ratings
        if 'date' in item:
            item['ratings'] = self.process_ratings(item['ratings'])
        
    # Traitement des dates
        if 'date' in item:
            item['date'] = self.process_date(item['date'])
    
    # Traitement des personnes du casting
        if 'cast' in item:
            item['cast'] = self.process_cast(item['cast'])

        return item


    def process_ratings(self, ratings):    
        press = ratings.get('press')
        spectators = ratings.get('spectators')
        # Traitement note presse
        if press == '--':   
            press = 'not rated'  # Indique 'not rated' si le film n'a pas reçu de note
        else:
            press = float(press.replace(',','.'))   # Convertit la note (string) en float

        # Traitement note spectateurs
        if spectators =='--':
            spectators = 'not rated'
        else:
            spectators = float(spectators.replace(',','.'))

        ratings = {'press': press, 'spectators': spectators}
        return ratings


    def process_date(self, date):
        date = date.strip() # Retire les '\n'

        month = date.split(' ')[1] # Convertit le mois en nombre
        if month=="janvier":
            month='1'
        elif month=="février":
            month='2'
        elif month=="mars":
            month='3'
        elif month=="avril":
            month='4'
        elif month=="mai":
            month='5'
        elif month=="juin":
            month='6'
        elif month=="juillet":
            month='7'
        elif month=="août":
            month='8'
        elif month=="septembre":
            month='9'
        elif month=="octobre":
            month='10'
        elif month=="novembre":
            month='11'
        elif month=="décembre":
            month='12'

        # Si rien ne correspond, c'est que la date est inconnue
        else:
            date = 'inconnue'
            return date
        
        # Conversion de la date en objet datetime
        date_components = date.split(' ')
        date_components[1] = month
        date = ' '.join(date_components)
        date = datetime.strptime(date, "%d %m %Y")
        return date


    def process_cast(self, cast):
        # Ne conserve pas les personnes qui ont un rôle mais pas de nom (Erreur d'affichage sur le site affichant le role en doublon)
        cast = [person for person in cast if person['name'] is not None]
        # Dictionnaire pour stocker les différents roles d'une personne (Un membre du casting peut avoir plusieurs rôles. Exemple : Réalisateur et Acteur)
        person_roles_dict = {}

        for person in cast:
            name = person['name']
            role = person['role'].strip() # Retire les '\n'

            if name is not None:
                # Si la personne est déjà dans le dictionnaire, on ajoute son role à sa liste de roles
                if name in person_roles_dict:
                    person_roles_dict[name]['role'].append(role)
                else:
                    # Sinon on crée une nouvelle paire
                    person_roles_dict[name] = {'name': name, 'role': [role]}

        # Convertit le dictionnaire en liste
        processed_cast = list(person_roles_dict.values())
        return processed_cast



class MongoDBPipeline(object):

    def open_spider(self, spider):
        self.client = MongoClient('mongo', 27017)
        self.db = self.client["allocine"]
        self.db.drop_collection("movie_collection")
    
    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        movie_data = dict(item)                             # Convertit l'item en dictionnaire
        self.db.movie_collection.insert_one(movie_data)     # Charge le film dans la base de données

        return item                                         # On retourne l'item pour qu'il puisse ensuite etre traité par la pipeline elasticsearch


# Ajout d'une pipeline Elasticsearch pour la recherche rapide de texte (titre, synopsis, membres du casting)
class ElasticsearchPipeline(object):
    def __init__(self):
        self.es_client = Elasticsearch("http://elasticsearch:9200/")
        self.index_name = "movies_index"
        self.doc_type = "movie"

    def process_item(self, item, spider):
        movie_data = {
            'title': item['title'],
            'synopsis': item['synopsis'],
            'cast': item['cast']
        }

        movie_id = item['_id']      # L'id du film est le même dans elasticsearch et mongo. Cela permettra de croiser les informations

        self.es_client.index(index=self.index_name, doc_type=self.doc_type, body=movie_data, id=movie_id)
