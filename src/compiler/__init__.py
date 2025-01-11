from rdflib import Namespace
from iiif_prezi3 import config

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

# Constants
BUILDING = aat['building']
COIN = aat['coin']
SCULPTURE = aat['sculpture']
SITE = aat['site']
GEM = aat['300011172']
VASE = aat['300132254']

ARTIFACT_TYPES = [BUILDING, COIN, SCULPTURE, SITE, GEM, VASE]

# Configuration for iiif_prezi3
config.configs['helpers.auto_fields.AutoLang'].auto_lang = "en"
base_url = "https://www.perseus.tufts.edu/api"
