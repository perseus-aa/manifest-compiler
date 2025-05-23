from pathlib import Path
import logging
from enum import Enum
from rdflib import Namespace, Graph, RDF, RDFS, URIRef
from iiif_prezi3 import Manifest, ManifestRef, Canvas, config, KeyValueString, Collection
from jinja2 import Environment, PackageLoader, select_autoescape
import httpx
import csv

logger = logging.getLogger(__name__)

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

# base_url = "https://www.perseus.tufts.edu/api"

# Set the base URI for the manifests.  It is the URL
# for Tufts's production metadata server.
base_url = "https://iiif-metadata.perseus.tufts.edu"


def base_graph() -> Graph:
    """Generates an empty Graph object with namespaces bound."""

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


    def exists(self) -> bool:
        try:
            resp = httpx.get(f"{self.uri}/info.json")
        except httpx.RemoteProtocolError:
            logging.error(f"RemoteProtocolError when trying to get {self.uri}/info.json")
            return False

        return resp.status_code not in [404, 500]

    @property
    def id(self)->str:
        return self.uri.split('/')[-1]

    @property
    def thumbnail(self):
        if self.exists():
            return f"{str(self.uri)}/full/pct:20/0/default.png"
        else:
            return None
    @property
    def small(self):
        if self.exists():
            return f"{str(self.uri)}/full/pct:50/0/default.png"
        else:
            return None

    @property
    def caption(self):
        result = self.graph.objects(subject=self.uri,
                                    predicate=SCHEMA['caption'])
        if result:
            return next(result)
        else:
            return None

    @property
    def creditText(self):
        result = self.graph.objects(subject=self.uri,
                                    predicate=SCHEMA['creditText'])
        if result:
            return next(result)
        else:
            return None


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
        self._thumbnail = None



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
    def title(self)->str:
        return self.label


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
            return self.images[0].thumbnail
        else:
            return None

    @property
    def manifest(self):
        if self._manifest is None:
            if not self.images:
                logger.warning(f"No images for {self.uri}; no manifest generated")
            else:
                metadata = [KeyValueString(label=k,value=v) for k,v in self.props.items()]
                self._manifest = Manifest(id=f"{base_url}/{self.id}/manifest.json",
                                          label={'en': [f"{self.label}"]},
                                          metadata=metadata
                                          )
                
                if self.thumbnail:
                    self._manifest.add_thumbnail(self.thumbnail)
                    
                    
                for idx, image in enumerate(self.images):
                    # make sure the image actually exists before
                    # trying to make a canvas.
                    if not image.exists():
                        logger.warning(f"Image not found: {image.uri}")
                    else:
                        canvas:Canvas = self._manifest.create_canvas_from_iiif(image.uri,
                                                                               id=f"{base_url}/{self.id}/p{idx+1}")
                        
                        if image.caption:
                            canvas.add_label(image.caption, language="en")
                            
                        if image.creditText:
                            canvas.add_label(image.creditText, language="en")
                        
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
    def __init__(self, db:Db) -> None:
        self.db = db

    def compile(self, directory:str) -> None:
        raise NotImplementedError("Subclasses must implement this")



class ManifestCompiler(Compiler):
    def __init__(self, db:Db) -> None:
        super().__init__(db)

    def compile(self, directory:str) -> None:
        dir_path:Path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        for e in self.db.entities:
            outfile:Path = dir_path / Path(f"{e.uri}.json")
            if outfile.exits:
                logger.info(f"manifest already exists; skipping {outfile}")
                continue

            logger.info(f"compiling manifest for entity {e.id}")
            manifest = e.manifest
            if manifest:
                logger.info(f"writing manifest to {outfile}")
                with open(outfile,"w", encoding="utf-8") as f:
                    print(manifest.json(indent=2), file=f)
            else:
                logger.info("no manifest generated")

                
            
class WebPageCompiler(Compiler):
    def __init__(self, db:Db) -> None:
        super().__init__(db)


    def compile(self, outdir):
        for e in self.db.entities:
            logger.info(f"compiling web page for {e.id}")
            # subdir:Path = Path(outdir) / Path(series(e.id))
            # print(e.props)

            subdir:Path = Path(outdir) / artifact_type_directory(e.type)
            subdir.mkdir(parents=True, exist_ok=True)
            
            outfile:Path = subdir / Path(f"{e.id}.html")
            with open(outfile, 'w', encoding="utf-8") as f:
                print(e.web_page, file=f)


class ImageTableCompiler(Compiler):
    def __init__(self, db:Db) -> None:
        super().__init__(db)


    # just compiles vase table for development
    def compile(self, outfile:Path) -> None:
        fieldnames = ['objectid', 'parentid', 'title', 'image_alt_text', 'object_location', 'image_small', 'image_thumb', 'display_template', 'format', 'description', 'source', 'type']
        with open(outfile, 'w', encoding='utf-8') as f:
            writer:DictWriter = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for entity in self.db.vases:
                for image in entity.images:
                    if image.exists():
                        row = {}
                        row['objectid'] = image.id
                        row['parentid'] = entity.id
                        row['title'] = image.id
                        row['image_alt_text'] = image.caption
                        row['object_location'] = image.uri
                        row['image_small'] = image.small
                        row['image_thumb'] = image.thumbnail
                        row['display_template'] = 'image'
                        row['format'] = 'image/jpeg'
                        
                        row['description'] = image.caption
                        row['source'] = image.creditText
                        row['type'] = 'Image;StillImage'
                        
                        writer.writerow(row)



class EntityTableCompiler(Compiler):
    def __init__(self, db:Db) -> None:
        super().__init__(db)


    # just compiles vase table for development
    
    def compile(self, outfile) -> None:
        fieldnames = ['objectid', 'title', 'object_location', 'image_small',
                      'image_thumb', 'display_template', 'format', 'description',
                      'source', 'type']

        with open(outfile, 'w', encoding='utf-8') as f:
            writer:DictWriter = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for entity in self.db.vases:
                row = {}
                row['objectid'] = entity.id
                row['title'] = entity.label
                row['object_location'] = entity.uri
                row['format'] = 'compound_object'
                row['type'] = 'record'
                row['display_template'] = 'compound_object'

                if entity.images:
                    image = entity.images[0]
                    if image.exists:
                        row['image_small'] = entity.images[0].small
                        row['image_thumb'] = entity.images[0].thumbnail

                writer.writerow(row)
