from pathlib import Path
import logging
import sys
from compiler import Db, ImageTableCompiler

rdf_dir = Path("/Users/wulfmanc/repos/gh/perseus-aa/rdf")
out_dir = Path("/tmp/output")
out_file = out_dir / Path('image_table.csv')

# Configure logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)


def main():
    db:Db = Db()
    db.load_all(rdf_dir)
    db.load_all(rdf_dir / Path("object_image_graphs"))

    c = ImageTableCompiler(db)
    
    c.compile(out_file)



if __name__ == "__main__":
    main()
