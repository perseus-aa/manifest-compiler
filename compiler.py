from pathlib import Path
from enum import Enum
from rdflib import Namespace, Graph, RDF, RDFS, URIRef
from iiif_prezi3 import Manifest, ManifestRef, Canvas, config, KeyValueString, Collection
from jinja2 import Environment, PackageLoader, select_autoescape
import httpx

# Namespaces
AAT = Namespace("http://vocab.getty.edu/aat/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
AA = Namespace("http://perseus.tufts.edu/ns/aa/")
SCHEMA = Namespace("https://schema.org/")
IMAGE = Namespace("https://iiif.perseus.tufts.edu/iiif/3/")

class AA_Namespaces(Enum):
    AA = AA
    AAT = AAT
    CRM = CRM
    IMAGE = IMAGE
    SCHEMA = SCHEMA
    RDF = RDF
    RDFS = RDFS

AA_NAMESPACES = {
    "crm" : CRM,
    "aat" : AAT,
    "aa" : AA,
    "image" : IMAGE,
    "schema" : SCHEMA,
    "rdf": RDF,
    "rdfs": RDFS
    
    }


# Constants
ARTIFACT = AAT['300117127']
BUILDING = AAT['building']
COIN = AAT['coin']
GEM = AAT['300011172']
SCULPTURE = AAT['sculpture']
SITE = AAT['site']
VASE = AAT['300132254']

ARTIFACT_TYPES = [BUILDING, COIN, GEM, SCULPTURE, SITE, VASE]


# Configuration for iiif_prezi3
config.configs['helpers.auto_fields.AutoLang'].auto_lang = "en"

base_url = "https://www.perseus.tufts.edu/api"

def base_graph() -> Graph:
    graph:Graph = Graph()
    [graph.bind(k,v) for k,v in AA_NAMESPACES.items()]
    return graph


def series(id:str):
    i  = int(id.split('_')[-1])
    if i < 1000:
        return "0000"
    elif i < 2000:
        return "1000"
    elif i < 3000:
        return "2000"
    elif i < 4000:
        return "3000"
    elif i < 5000:
        return "4000"
    else:
        return "5000"
    
def artifact_type_directory(type:URIRef):
    if type == BUILDING:
        return Path('buildings')
    elif type == COIN:
        return Path('coins')
    elif type == SCULPTURE:
        return Path('sculptures')
    elif type == SITE:
        return Path('sites')
    elif type == GEM:
        return Path('gems')
    elif type == VASE:
        return Path('vases')
    else:
        return Path('unknown')
    

class Image:
    def __init__(self, uri:URIRef, graph:Graph):
        self.uri = uri
        self.graph = graph

    @property
    def notes(self):
        result = self.graph.objects(subject=self.uri,
                           predicate=CRM['P3_has_note'])
        return [str(note) for note in result]



class Entity:

    env:Environment = Environment(
        loader=PackageLoader("compiler"),
        autoescape=select_autoescape()
    )


    def __init__(self, uri:URIRef, graph:Graph):
        self.uri = uri
        self.graph = graph
        self._manifest = None
        self._images = None
        self._web_page = None



    @property
    def id(self):
        return self.uri.split('/')[-1]

    @property
    def type(self):
        qresults = self.graph.objects(subject=self.uri,
                                      predicate=RDF['type'])
        artifact_type =  [type for type in qresults if type != CRM['E22_Human_Made_Object']][0]
        return artifact_type
    


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
                           predicate=CRM['P3_has_note'])

        props = {}
        if self.thumbnail:
            props['thumbnail'] = self.thumbnail

        for note in result:
            try:
                p,v = str(note).split(':')
                props[p] = v.strip()
            except ValueError:
                pass
        return props


    @property
    def images(self):
        if self._images is None:
            lst = list(self.graph.objects(self.uri, CRM["P138i_is_represented_by"]))
            self._images = [Image(i, self.graph) for i in lst]
        return self._images
    

    @property
    def thumbnail(self):
        if self.images:
            thumb = self.images[0]
            resp = httpx.get(f"{thumb.uri}/info.json")
            if resp.status_code not in [404, 500]:
                return f"{str(self.images[0].uri)}/full/100,/0/default.png"
        else:
            return None


    @property
    def manifest(self):
        if self._manifest is None:
            metadata = [KeyValueString(label=k,value=v) for k,v in self.props.items()]
            self._manifest = Manifest(id=f"{base_url}/{self.id}",
                                      label={'en': [f"{self.label}"]},
                                      metadata=metadata
                                      )
            if self.images:
                thumb = self.images[0]
                resp = httpx.get(f"{thumb.uri}/info.json")
                if resp.status_code in [404, 500]:
                    print(f"Thumbnail image not found: {thumb.uri}")
                else:
                    print("adding thumbnail")
                    self._manifest.add_thumbnail(str(self.images[0].uri))
        

            for image in self.images:
                # print(f"canvasifying image {image.uri}")
                resp = httpx.get(f"{image.uri}/info.json")
                if resp.status_code in [404, 500]:
                    print(f"Image not found: {image.uri}")
                else:
                    canvas:Canvas = self._manifest.create_canvas_from_iiif(image.uri)
                    # print(f"added canvas for {image.uri}")
                    for note in image.notes:
                        canvas.add_label(language="en", value=note)                      
                    self._manifest.add_item(canvas)
        return self._manifest
    
    @property
    def web_page(self):
        if self._web_page is None:
            template = self.env.get_template('artifact.html')
            
            print(f"series={series(self.id)}\tid={self.id}")
            self._web_page = template.render(series=series(self.id), id=self.id)
        return self._web_page





class Db:
    """
    An abstraction of a database of graph data about entities
    and images, with methods for generating manifests and web pages
    for them.
    """
    def __init__(self):
        self.graph:Graph = base_graph()
        self._entities = None

    def load(self, rdf_file:Path)->None:
        self.graph.parse(rdf_file)

    def load_all(self, rdf_dir:Path) -> None:
        for f in rdf_dir.glob("*.ttl"):
            self.load(f)


    def entity(self, uri:URIRef):
        return Entity(uri=uri, graph=self.graph)

    @property
    def entities(self):
        if self._entities is None:
            self._entities = []
            gen = self.graph.subjects(
                predicate=RDF['type'],
                object=CRM['E22_Human-Made_Object'])
            self._entities = [Entity(e, self.graph) for e in gen]
        return self._entities
    

    def entities_by_type(self, entity_type):
        return filter(lambda x: x.type == entity_type, self.entities)


    @property
    def vases(self):
        return filter(lambda x: x.type == VASE, self.entities)
    
    @property
    def buildings(self):
        return filter(lambda x: x.type == BUILDING, self.entities)

    @property
    def coins(self):
        return filter(lambda x: x.type == COIN, self.entities)
    
    @property
    def sculptures(self):
        return filter(lambda x: x.type == SCULPTURE, self.entities)

    @property
    def sites(self):
        return filter(lambda x: x.type == SITE, self.entities)
    
    @property
    def gems(self):
        return filter(lambda x: x.type == GEM, self.entities)
    


    
    def compile_props(self, outdir):
        props = {}
        for e in self.entities:
            if e.props:
                props[e.id] = e.props
        return props
    

    def vase_props(self):
        props = []
        for x in self.vases:
            props.append(x.props)
        return props
        


class Compiler:
    def __init__(self, db:Db):
        self.db = db
        self._manifests = []


    def compile_manifest(self, entity_id:str):
        try:
            entity = [e for e in self.db.entities if e.id == entity_id][0]
            return entity.manifest
        except IndexError:
            print(f"{entity_id} not found")
        

    def compile_manifests(self, outdir):
        for e in self.db.entities:
            subdir:Path = Path(outdir) / Path(series(e.id))
            subdir.mkdir(parents=True, exist_ok=True)
            outfile:Path = subdir / Path(f"{e.id}.json")
            if outfile.exists():
                print(f"skipping {outfile}")
            else:
                print(f"compiling manifest for entity {e.id}")
                manifest = e.manifest
                print(f"writing manifest to {outfile}")
                with open(outfile,"w", encoding="utf-8") as f:
                    print(manifest.json(indent=2), file=f)


    def compile_web_pages(self, outdir):
        for e in self.db.entities:
            print(f"compiling web page for {e.id}")
            # subdir:Path = Path(outdir) / Path(series(e.id))
            print(e.props)

            subdir:Path = Path(outdir) / artifact_type_directory(e.type)
            subdir.mkdir(parents=True, exist_ok=True)
            
            outfile:Path = subdir / Path(f"{e.id}.html")
            with open(outfile, 'w', encoding="utf-8") as f:
                print(e.web_page, file=f)
