from compiler import Db, Entity
from compiler import ARTIFACT, BUILDING, COIN, GEM, SCULPTURE, SITE, VASE, ARTIFACT_TYPES
from compiler import AA, AAT, CRM, IMAGE, SCHEMA


def test_access(shared_datadir):
    db = Db()
    db.load(shared_datadir / "test_rdf.ttl")

    assert len(db.entities) == 2

    id = "aa_3988"
    e = db.entity(id)
    assert e.id == id

def test_types(shared_datadir):
    db = Db()
    db.load(shared_datadir / "test_rdf.ttl")

    vases = db.entities_by_type(VASE)
    assert len(list(vases)) == 2

    assert len(list(db.vases)) == 2


def test_vase_props(shared_datadir):
    db = Db()
    db.load(shared_datadir / "test_rdf.ttl")

    assert len(db.vase_props()) == 2
