from pathlib import Path
import urllib3
from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from iiif_prezi3 import Manifest, Canvas, config, KeyValueString
from jinja2 import Environment, PackageLoader, select_autoescape


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
    if type == aat['building']:
        return Path('buildings')
    elif type == aat['coin']:
        return Path('coins')
    elif type == aat['sculpture']:
        return Path('sculptures')
    elif type == aat['site']:
        return Path('sites')
    elif type == aat['300011172']:
        return Path('gems')
    elif type == aat['300132254']:
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
                           predicate=crm['P3_has_note'])
        return [str(note) for note in result]


class Entity:

    env:Environment = Environment(
        loader=PackageLoader("manifester"),
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
            try:
                p,v = str(note).split(':')
                props[p] = v.strip()
            except ValueError:
                print(f"badly formed note: {note}")
        return props


    @property
    def type(self):
        qresults = self.graph.objects(subject=self.uri,
                                      predicate=RDF['type'])
        artifact_type =  [type for type in qresults if type != crm['E22_Human_Made_Object']][0]
        return artifact_type



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
                # print(f"canvasifying image {image.uri}")
                resp = urllib3.request("GET", image.uri)
                if resp.status in [404, 500]:
                    print(f"Image not found: {image.uri}")
                else:
                    canvas:Canvas = self._manifest.create_canvas_from_iiif(image.uri)
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


    def compile_manifests(self, outdir):
        for e in self.entities:
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
        for e in self.entities:
            print(f"compiling web page for {e.id}")
            # subdir:Path = Path(outdir) / Path(series(e.id))
            print(e.props)

            subdir:Path = Path(outdir) / artifact_type_directory(e.type)
            subdir.mkdir(parents=True, exist_ok=True)
            
            outfile:Path = subdir / Path(f"{e.id}.html")
            with open(outfile, 'w', encoding="utf-8") as f:
                print(e.web_page, file=f)
