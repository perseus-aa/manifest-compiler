from pathlib import Path
import logging
import sys
from compiler import Db, Compiler

rdf_dir = Path("/Users/wulfmanc/repos/gh/perseus-aa/rdf")
out_dir = Path("/tmp/output")
manifest_out = out_dir / Path("manifests")
webpage_out = out_dir / Path("webpages")


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

    c = Compiler(db)
    c.compile_manifests(manifest_out)
    c.compile_web_pages(webpage_out)


if __name__ == "__main__":
    main()
