import csv

from iiif_prezi3 import Manifest, Canvas, config


config.configs['helpers.auto_fields.AutoLang'].auto_lang = "en"
base_url = "https://www.perseus.tufts.edu/api"

data_file = "~/Downloads/vase_data.csv"

def main():
    images = {}
    labels = {}
    with open(data_file, "r", encoding="utf-8") as f:
        reader:csv.DictReader = csv.DictReader(f)
        for row in reader:
            if not(labels.get(row['entity'])):
                labels[row['entity']] = row['label']

            if not (images.get(row['entity'])):
                images[row['entity']] = []
            images[row['entity']].append(images['image'])




if __name__ == "__main__":
    main()
