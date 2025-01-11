from compiler.models import Db, Entity, Image
from compiler import entity
from rdflib import Graph, RDFS

def test_properties(shared_datadir):
    db = Db()
    db.load(shared_datadir / "images.ttl")
    db.load(shared_datadir / "artifacts.ttl")
    assert len(db.entities) == 4

    e = db.entity(entity['aa_1000'])
    assert e.id == "aa_1000"
    assert e.label == "Boston 12.440"
    assert len(e.images) == 2

    notes = e.images[0].notes
    assert len(notes) == 2
    assert notes[0] == "Obverse: Helmeted head of Roma"

    manifest = e.manifest
