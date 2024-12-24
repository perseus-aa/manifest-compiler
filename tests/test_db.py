from manifester import Db, Entity


def test_db(shared_datadir):
    db = Db()
    db.load(shared_datadir / "images.ttl")
    db.load(shared_datadir / "artifacts.ttl")
    assert len(db.entities) == 4

    e = db.entity("aa_1000")
    assert e.id == "aa_1000"