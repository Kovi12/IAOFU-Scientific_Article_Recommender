import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF

# Define namespaces
EX = Namespace("http://example.org/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

# Load the RDF graph
graph = Graph()
ontology_file = "data/ontology.xml"
try:
    graph.parse(ontology_file, format="xml")
    print("Ontology loaded successfully.")
except Exception as e:
    print(f"Error loading ontology: {e}")
    raise RuntimeError("Failed to load RDF data.")

# Function to clean and format URIs
def format_uri(name):
    return URIRef(f"http://example.org/{name.replace('-', '_').replace(' ', '_').lower()}")

# Function to check if a triple exists in the graph
def add_if_not_exists(graph, subject, predicate, obj):
    if not (subject, predicate, obj) in graph:
        graph.add((subject, predicate, obj))

# Function to add an article to the ontology
def add_article_to_ontology(article_data, graph):
    for doi, details in article_data.items():
        # Create a URI for the article
        article_uri = URIRef(f"http://example.org/{details['id']}")
        add_if_not_exists(graph, article_uri, RDF.type, EX.Document)

        # Add title
        add_if_not_exists(graph, article_uri, EX.hasTitle, Literal(details['title']))

        # Add year
        if "year" in details:
            add_if_not_exists(graph, article_uri, EX.hasYear, Literal(details['year'], datatype=RDF.integer))

        # Add number of citations
        if "num_citations" in details:
            add_if_not_exists(graph, article_uri, EX.hasCitations, Literal(details['num_citations'], datatype=RDF.integer))

        # Add authors as instances and link to the article
        authors = [author.strip() for author in details['authors'].replace("and", ",").split(",")]
        for author_name in authors:
            author_uri = format_uri(author_name)
            add_if_not_exists(graph, author_uri, RDF.type, EX.Author)
            add_if_not_exists(graph, author_uri, RDFS.label, Literal(author_name))
            add_if_not_exists(graph, article_uri, EX.hasAuthor, author_uri)

        # Add concepts (categories, subjects, and top_terms)
        concepts = [details['category']] + details.get('subjects', []) + details.get('top_terms', [])
        for concept_name in concepts:
            concept_uri = format_uri(concept_name)
            add_if_not_exists(graph, concept_uri, RDF.type, EX.Concept)
            add_if_not_exists(graph, concept_uri, RDFS.label, Literal(concept_name))
            add_if_not_exists(graph, article_uri, EX.hasConcept, concept_uri)

        # Add references
        for reference in details.get('references', []):
            reference_uri = URIRef(f"http://example.org/{reference.replace('/', '_')}")
            add_if_not_exists(graph, reference_uri, RDF.type, EX.Document)  # Treat references as articles
            add_if_not_exists(graph, article_uri, EX.hasReference, reference_uri)

        # Add DOI as an additional identifier
        add_if_not_exists(graph, article_uri, EX.hasDOI, Literal(doi))

    print("Articles added to the ontology.")

# Main function to load JSON and process articles
def main():
    # Load JSON data
    json_file = "articles.json"
    try:
        with open(json_file, "r") as f:
            article_data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        return

    # Add articles to the ontology
    add_article_to_ontology(article_data, graph)

    # Save the updated ontology back to file
    try:
        graph.serialize(destination=ontology_file, format="xml")
        print("Ontology updated and saved successfully.")
    except Exception as e:
        print(f"Error saving updated ontology: {e}")

if __name__ == "__main__":
    main()
