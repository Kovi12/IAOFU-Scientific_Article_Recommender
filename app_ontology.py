import re
from flask import Flask, render_template, request, jsonify
from rdflib import Graph, Namespace, URIRef, RDF
import logging

# Create a custom filter to exclude specific warnings related to invalid URIs
class NoURIWarningFilter(logging.Filter):
    def filter(self, record):
        # Check if the message contains the specific pattern for URI warnings
        return not re.match(r'.*does not look like a valid URI.*', record.getMessage())

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Set the logging level to INFO (so INFO and higher messages are shown)
logger.setLevel(logging.DEBUG)

# Create a StreamHandler and add the custom filter
handler = logging.StreamHandler()
handler.addFilter(NoURIWarningFilter())  # Apply the filter here
logger.addHandler(handler)

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
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

# Helper function to fetch labels or titles for references
def resolve_reference(uri):
    """Resolve the reference to its title or fallback to the URI as a string."""
    if (uri, RDF.type, EX.Document) in graph:
        # Try to fetch the title of the document
        title = next(graph.objects(uri, EX.hasTitle), None)
        if title:
            return str(title)
    # If not a document or no title, return the URI or its label
    return get_label(uri)

# Helper function to fetch labels for URIs
def get_label(uri):
    """Fetch the rdfs:label or return the string version of the URI."""
    # First, try to get the rdfs:label for the URI
    label = next(graph.objects(uri, RDFS.label), None)
    return str(label) if label else str(uri)

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
            doi = next(graph.objects(doc, EX.hasDOI), None)
            num_citations = next(graph.objects(doc, EX.hasCitations), None)
            authors = [get_label(author) for author in graph.objects(doc, EX.hasAuthor)]
            concepts = [get_label(concept) for concept in graph.objects(doc, EX.hasConcept)]
            references = [resolve_reference(ref) for ref in graph.objects(doc, EX.hasReference)]

            articles.append({
                'title': str(title) if title else 'No Title',
                'abstract': str(abstract) if abstract else 'No Abstract',
                'year': str(year) if year else 'Unknown',
                'num_citations': str(num_citations) if num_citations else len(references),
                'authors': authors,
                'concepts': concepts,
                'references': references,
                'doi': doi
            })

        logging.info(f"Total articles fetched: {len(articles)}")
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
            year = next(graph.objects(doc, EX.hasYear), None)
            doi = next(graph.objects(doc, EX.hasDOI), None)
            num_citations = next(graph.objects(doc, EX.hasCitations), None)
            authors = [get_label(author) for author in graph.objects(doc, EX.hasAuthor)]
            concepts = [get_label(concept) for concept in graph.objects(doc, EX.hasConcept)]
            references = [resolve_reference(reference) for reference in graph.objects(doc, EX.hasReference)]

            # Filter results based on the search query
            if search_type == 'author' and any(query == author.lower() for author in authors):
                results.append({
                    'title': str(title) if title else 'No Title',
                    'abstract': str(abstract) if abstract else 'No Abstract',
                    'year': str(year) if year else 'Unknown',
                    'num_citations': str(num_citations) if num_citations else len(references),
                    'authors': authors,
                    'concepts': concepts,
                    'references': references,
                    'doi': doi
                })
                seen.add(doc)

            elif search_type == 'concept' and any(query == concept.lower() for concept in concepts):
                results.append({
                    'title': str(title) if title else 'No Title',
                    'abstract': str(abstract) if abstract else 'No Abstract',
                    'year': str(year) if year else 'Unknown',
                    'num_citations': str(num_citations) if num_citations else len(references),
                    'authors': authors,
                    'concepts': concepts,
                    'references': references,
                    'doi': doi
                })
                seen.add(doc)

            elif search_type == 'reference' and any(query == reference.lower() for reference in references) or query == doi:
                results.append({
                    'title': str(title) if title else 'No Title',
                    'abstract': str(abstract) if abstract else 'No Abstract',
                    'year': str(year) if year else 'Unknown',
                    'num_citations': str(num_citations) if num_citations else len(references),
                    'authors': authors,
                    'concepts': concepts,
                    'references': references,
                    'doi': doi
                })
                seen.add(doc)

            elif any(query == detail.lower() for detail in references + concepts + authors) or query in (str(title).lower() if title else ''):
                results.append({
                    'title': str(title) if title else 'No Title',
                    'abstract': str(abstract) if abstract else 'No Abstract',
                    'year': str(year) if year else 'Unknown',
                    'num_citations': str(num_citations) if num_citations else len(references),
                    'authors': authors,
                    'concepts': concepts,
                    'references': references,
                    'doi': doi
                })
                seen.add(doc)

        logging.debug(f"Search results count: {len(results)}")
    except Exception as e:
        logging.error(f"Error during search: {e}")
        return jsonify(error="An error occurred while processing your search request."), 500

    return jsonify(results=results)

if __name__ == '__main__':
    app.run(debug=True)
