from flask import Flask, render_template, request, jsonify
from rdflib import Graph, Namespace, URIRef, RDF
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)

# Load RDF data
graph = Graph()
try:
    graph.parse('data/ontology.xml', format='xml')
    logging.info("Ontology loaded successfully.")
except Exception as e:
    logging.error(f"Error loading ontology: {e}")
    raise RuntimeError("Failed to load RDF data.")

# Define custom namespace
EX = Namespace("http://example.org/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


# Helper function to fetch labels for URIs
def get_label(uri):
    """Fetch the rdfs:label or return the string version of the URI."""
    # First, try to get the rdfs:label for the URI
    label = next(graph.objects(uri, RDFS.label), None)

    # If label exists, return it; else, return the URI as string.
    return str(label) if label else str(uri)


# Helper function to fetch articles from RDF data
# Updated function to fetch articles
def get_articles(limit=None):
    articles = []
    seen = set()

    try:
        for doc in graph.subjects(predicate=RDF.type, object=EX.Document):
            if doc in seen:
                continue  # Avoid duplicates
            seen.add(doc)

            title = next(graph.objects(doc, EX.hasTitle), None)
            abstract = next(graph.objects(doc, EX.hasAbstract), None)
            year = next(graph.objects(doc, EX.hasYear), None)
            num_citations = next(graph.objects(doc, EX.hasCitations), None)
            authors = [get_label(author) for author in graph.objects(doc, EX.hasAuthor)]
            concepts = [get_label(concept) for concept in graph.objects(doc, EX.hasConcept)]
            references = [get_label(ref) for ref in graph.objects(doc, EX.hasReference)]

            articles.append({
                'title': str(title) if title else 'No Title',
                'abstract': str(abstract) if abstract else 'No Abstract',
                'year': str(year) if year else 'Unknown',
                'num_citations': str(num_citations) if num_citations else len(references),
                'authors': authors,
                'concepts': concepts,
                'references': references,
            })

        logging.debug(f"Total articles fetched: {len(articles)}")
    except Exception as e:
        logging.error(f"Error fetching articles: {e}")

    return articles[:limit] if limit else articles



@app.route('/')
def index():
    try:
        # Display the first 10 articles by default
        default_articles = get_articles(limit=10)
        logging.debug(f"Default articles for display: {default_articles}")
        return render_template('index.html', articles=default_articles)
    except Exception as e:
        logging.error(f"Error in index route: {e}")
        return "An error occurred while loading the index page.", 500


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip().lower()
    search_type = request.args.get('type', '').strip().lower()  # New parameter
    logging.info(f"Search query: {query}, Type: {search_type}")
    results = []
    seen = set()  # Track processed articles to avoid duplicates

    if not query:
        logging.warning("Empty search query received.")
        return jsonify(results=[])

    try:
        for doc in graph.subjects(predicate=RDF.type, object=EX.Document):
            if doc in seen:
                continue  # Skip duplicates

            title = next(graph.objects(doc, EX.hasTitle), None)
            abstract = next(graph.objects(doc, EX.hasAbstract), None)
            authors = [get_label(author) for author in graph.objects(doc, EX.hasAuthor)]
            concepts = [get_label(concept) for concept in graph.objects(doc, EX.hasConcept)]

            if search_type == 'author' and any(query == author.lower() for author in authors):
                results.append({
                    'title': str(title) if title else 'No Title',
                    'abstract': str(abstract) if abstract else 'No Abstract',
                    'authors': authors,
                    'concepts': concepts
                })
                seen.add(doc)

            elif search_type == 'concept' and any(query == concept.lower() for concept in concepts):
                results.append({
                    'title': str(title) if title else 'No Title',
                    'abstract': str(abstract) if abstract else 'No Abstract',
                    'authors': authors,
                    'concepts': concepts
                })
                seen.add(doc)

        logging.debug(f"Search results count: {len(results)}")
    except Exception as e:
        logging.error(f"Error during search: {e}")
        return jsonify(error="An error occurred while processing your search request."), 500

    return jsonify(results=results)



if __name__ == '__main__':
    app.run(debug=True)
