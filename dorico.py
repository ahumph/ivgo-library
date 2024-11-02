import zipfile
import xml.etree.ElementTree as ET

def read_dorico_metadata(file_path):
  # open the dorico file as a zip file
  with zipfile.ZipFile(file_path, "r") as z:
    # read the contents of the file
    contents = z.namelist()
    # find the file that contains the metadata
    [print(f) for f in contents]
    metadata_file = [f for f in contents if "scoreinfo.xml" in f][0]
    # read the metadata file
    with z.open(metadata_file) as f:
        # parse the xml file
        tree = ET.parse(f)
        root = tree.getroot()
        # find the title and composer of the piece
        title = root.find(".//kTitle").text
        composer = root.find(".//kComposer").text
        return title, composer
  return None, None

def main():
    print("This is the dorico module")
    file_path = "Playstation.dorico"
    title, composer = read_dorico_metadata(file_path)
    print(f"Title: {title}, Composer: {composer}")

if __name__ == "__main__":
  main()