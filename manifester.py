from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from iiif_prezi3 import Manifest, Canvas, config, KeyValueString


crm = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
aat = Namespace("http://vocab.getty.edu/aat/")
entity = Namespace("http://perseus.tufts.edu/ns/entities/")
artifact = Namespace("http://perseus.tufts.edu/ns/artifact/")
vase = Namespace("http://perseus.tufts.edu/ns/artifact/vase/")
gem = Namespace("http://perseus.tufts.edu/ns/artifact/gem/")
sculpture = Namespace("http://perseus.tufts.edu/ns/artifact/sculpture/")
coin = Namespace("http://perseus.tufts.edu/ns/artifact/coin/")
building = Namespace("http://perseus.tufts.edu/ns/building/")
site = Namespace("http://perseus.tufts.edu/ns/artifact/site/")
image = Namespace("https://iiif-dev.perseus.tufts.edu/iiif/3/")

# Configuration for iiif_prezi3
config.configs['helpers.auto_fields.AutoLang'].auto_lang = "en"
base_url = "https://www.perseus.tufts.edu/api"

class Image:
    def __init__(self, uri:URIRef, graph:Graph):
        self.uri = uri
        self.graph = graph

    @property
    def notes(self):
        result = self.graph.objects(subject=self.uri,
                           predicate=crm['P3_has_note'])
        return [str(note) for note in result]

        


class Entity:
    def __init__(self, uri:URIRef, graph:Graph):
        self.uri = uri
        self.graph = graph
        self._manifest = None
        self._images = None

    @property
    def id(self):
        return self.uri.split('/')[-1]


    @property
    def label(self)->str:
        qresults = self.graph.objects(subject=self.uri,
                                        predicate=RDFS['label'])
        try:
            return str(list(qresults)[0])
        except IndexError:
            return "no label"



    @property
    def props(self):
        result = self.graph.objects(subject=self.uri,
                           predicate=crm['P3_has_note'])

        props = {}
        for note in result:
            p,v = str(note).split(':')
            props[p] = v.strip()
        return props


    
    @property
    def images(self):
        if self._images is None:
            lst = list(self.graph.objects(self.uri, crm["P138i_is_represented_by"]))
            self._images = [Image(i, self.graph) for i in lst]
        return self._images
    
    @property
    def manifest(self):
        if self._manifest is None:
            metadata = [KeyValueString(label=k,value=v) for k,v in self.props.items()]
            self._manifest = Manifest(id=f"{base_url}/{self.id}",
                                      label={'en': [f"{self.label}"]},
                                      metadata=metadata
                                      )

            for image in self.images:
                canvas:Canvas = self._manifest.create_canvas_from_iiif(image.uri)
                for note in image.notes:
                    canvas.add_label(language="en", value=note)                      
                self._manifest.add_item(canvas)


        return self._manifest



class Db:
    def __init__(self):
        self.graph:Graph = Graph()
        self.graph.bind("crm", crm)
        self.graph.bind("entity", entity)
        self.graph.bind("aat", aat)
        self.graph.bind("image", image)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)

        self._entities = None


    def load(self, rdf_file:Path)->None:
        self.graph.parse(rdf_file)


    def entity(self, uri:URIRef):
        return Entity(uri=uri, graph=self.graph)

    @property
    def entities(self):
        if self._entities is None:
            self._entities = []
            gen = self.graph.subjects(
                predicate=RDF['type'],
                object=crm['E22_Human-Made_Object'])
            self._entities = [Entity(e, self.graph) for e in gen]
        return self._entities