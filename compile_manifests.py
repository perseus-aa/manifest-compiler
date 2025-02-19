from pathlib import Path
from compiler import Db, Compiler

rdf_dir = Path("/Users/wulfmanc/repos/gh/perseus-aa/rdf")

db:Db = Db()


db.load_all(rdf_dir)
db.load_all(rdf_dir / Path("object_image_graphs"))

c = Compiler(db)
