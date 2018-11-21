# coding:utf8

# spacy pour la recherche d'entités nommées
import spacy
# justext pour le détourage du contenu HTML
import justext
# re pour la récupération de certains éléments dans le contenu textuel
import re
# urlopen.urllib pour la lecture de fichier HTML depuis un lien HTTP
from urllib import urlopen

# Load English tokenizer, tagger, parser, NER and word vectors

# Fonction recherchant les entités nommées correspondant à une ontologie de films, depuis 
# le contenu d'un fichier HTML
# params :
#	- link : l'URL du fichier à fouiller
# returns :
#	- un dictionnaire des entités nommées trouvées
def find(link):
	# Dictionnaires des réalisateurs, titres et langages potentiels (key=texte évalué, value=occurrences valides)
	# -> le "plus fréquent" dans chaque dictionnaire (value=max) est accepté comme résultat
	allPotentialReal = {}
	potential_titles = {}
	potential_languages = {}
	# Chargement du modèle linguistique pour l'anglais
	nlp = spacy.load('en')
	# Initialisation du dictionnaire résultat
	result = {"title":"", "director":"", "genre":"", "category":"", "language":"", "footage":""}
	# Extraction du contenu textuel correspondant à l'anglais dans le fichier
	texte = urlopen(link).read()
	paragraphs = justext.justext(texte, justext.get_stoplist("English"))
	condensedText = ""
	# Pas de tri avec is_boilerplate() car sur les sources Wikipédia, cela élimine tout le texte
	# "du début" de l'article, qui contient la majorité des informations désirées dans un format
	# pratique à traiter (formulations et structures de phrases souvent les mêmes d'un article à l'autre)
	# -> On élimine les sauts de ligne car ils sont considérés comme des termes après le passage de spacy
	for paragraph in paragraphs:
		condensedText = condensedText + paragraph.text.replace("\n"," ")
	# Détermination automatique des entités par spacy
	doc = nlp(condensedText)
	# On découpe le texte en phrases pour les fouilles à venir
	docsentences = re.split('[.]', condensedText)

	# Parcours des entités trouvées par spacy
	# Pour chacune, on observe le nombre de phrases qui contiennent l'entité (allPotentialSentences)
	# et qui satisfont des critères de tri supplémentaires. La double vérification induite est nécessaire
	# pour passer au travers des anomalies retournées parfois par spacy

	# Liste d'entités avec le label 'PERSON'
	allPerson = []
	for entity in doc.ents:
		# Recherche des réalisateurs potentiels : entités avec le label 'PERSON' et composées de deux mots au moins
		if entity.label_ == "PERSON" and len(entity.text.split(" ")) >= 2 :
			# On enregistre les entités nouvelles
			if not entity.text in allPerson:
				allPerson.append(entity.text)
				allPotentialSentences = 0
				# On compte le nombre de phrases contenant l'entité avec le terme 'directed' autour d'eux
				# à raison de 20 caractères
				for sentence in docsentences :
					if sentence.find(entity.text) >= 0 and sentence[sentence.find(entity.text) - 20 : sentence.find(entity.text)+ len(entity.text)+ 20].find("directed") >= 0 :
						allPotentialSentences += 1
				# Si une phrase contient l'entité dans les conditions voulues, on initialise le compteur d'occurrences
				if allPotentialSentences > 0:
					allPotentialReal[entity.text] = 1
			# Si le réalisateur est déjà trouvé avec les conditions de phrasé, on incrémente le compteur d'occurrences
			# --> ce système permet de considérer les entités comme "Robert" et "Zemeckis" comme celle de valeur
			# "Robert Zemeckis" (par exemple)
			elif entity.text in allPotentialReal :
				allPotentialReal[entity.text] += 1
		# Recherche de titres potentiels : entités avec le label 'ORG', 'EVENT', 'WORK_OF_ART' ou 'PRODUCT' (recherche large)
		# et commençant par une lettre majuscule
		# On emploie cette fois un setting du compteur d'occurrences avec le nombre d'occurrences trouvées dans le texte
		# (pas de forçage comme pour les réalisateurs)
		elif (entity.label_ == "ORG" or entity.label_ == "EVENT" or entity.label_ == "WORK_OF_ART" or entity.label_ == "PRODUCT") and entity.text[0].isupper() :
			if not entity.text in potential_titles :
				allPotentialSentences = 0	
				# On compte le nombre de phrases contenant l'entité suivie du mot 'film' dans les 50 caractères suivant
				for sentence in docsentences :
					if sentence.find(entity.text) >= 0 and (  sentence[sentence.find(entity.text): sentence.find(entity.text)+ len(entity.text) + 50].find("is a") >= 0 and sentence.find("film") >= 0 ):
						allPotentialSentences += 1
				if allPotentialSentences > 0:
					potential_titles[entity.text] = allPotentialSentences
		# Recherche de langages potentiels : enttés avec le label 'LANGUAGE'
		# Même comptage que pour les titres avec plus de simplicité : pas besoin pour les langues de vérifier d'autres
		# conditions dans cette boucle
		elif entity.label_==u'LANGUAGE':
			if not entity.text in potential_languages :
				potential_languages[entity.text] = 1
			else :
				potential_languages[entity.text] += 1
	# Si aucun langage n'a été trouvé avec les labels, on utilise les suffixes les plus probables
	if len(potential_languages.items())==0:
		for entity in [i for i in doc.ents]:
			if len(entity.text.split(' ')) == 1 and (entity.text.endswith(u'can') or entity.text.endswith(u'ian') or entity.text.endswith(u'ese') or entity.text.endswith(u'ish') or entity.text.endswith(u'nch')):
				potential_languages[entity.text] = potential_languages[entity.text]+1 if potential_languages.has_key(entity.text) else 1
	# Setting du rélisateur
	result['director'] = allPotentialReal.keys()[0]
	for potentialReal in allPotentialReal :
		if allPotentialReal[potentialReal] > allPotentialReal[result['director']]:
			result['director'] = potentialReal
	# Setting du titre
	for intitle in potential_titles.keys() :
		for title in potential_titles.keys() :
			if title.find(intitle) >= 0 and title != intitle :
				potential_titles[title] += potential_titles[intitle] 
	if len(potential_titles) > 0 :
		titleMax = 0
		for k, v in potential_titles.items():
			if v > titleMax:
				titleMax = v
				result['title'] = k
		if result['title'] == "":
			result['title'] = potential_titles.keys()[1]
	# Titre vide si aucun valide trouvé (peut arriver selon les films)
	else :
		result['titre'] = ""
	# Détermination du langage
	langMax = 0
	for k, v in potential_languages.items():
		if v > langMax:
			langMax = v
			result['language'] = k
	if result['language'] == "":
		result['language'] = potential_languages.keys()[1]
	return result

# Exécution du programme sur les pages Web suivantes et affichage en console des résultats
# (titre, réalisateur et langage seulement -> trop de complexité pour obtenir une précision
# raisonnable avec les autres informations et donc très long à mettre en place...)
for link in ["https://en.wikipedia.org/wiki/Forrest_Gump",
"https://en.wikipedia.org/wiki/The_Terminator",
"https://en.wikipedia.org/wiki/A_Clockwork_Orange_(film)",
"https://en.wikipedia.org/wiki/Full_Metal_Jacket",
"https://en.wikipedia.org/wiki/World_Assembly_of_Youth_(film)",
"https://en.wikipedia.org/wiki/Visitor_Q",
"https://en.wikipedia.org/wiki/Reservoir_Dogs",
"https://en.wikipedia.org/wiki/Pulp_Fiction",
"https://en.wikipedia.org/wiki/Jackie_Brown",
"https://en.wikipedia.org/wiki/The_Fifth_Element",
"https://en.wikipedia.org/wiki/Memento_(film)",
"https://en.wikipedia.org/wiki/The_Prestige_(film)",
"https://en.wikipedia.org/wiki/La_Dolce_Vita",
"https://en.wikipedia.org/wiki/The_Voice_of_the_Moon",
"https://en.wikipedia.org/wiki/Boccaccio_%2770",
"https://en.wikipedia.org/wiki/Drive_(2011_film)",
"https://en.wikipedia.org/wiki/Swiss_Army_Man"
]:
	info = find(link)
	print(link,info["title"],info["director"],info["language"])
