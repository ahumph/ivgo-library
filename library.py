import fitz
import io
import os.path
import pickle
import googleapiclient
import psycopg2

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

DATABASE_HOST = os.environ.get("DATABASE_HOST")
DATABASE_NAME = os.environ.get("DATABASE_NAME")
DATABASE_USER = os.environ.get("DATABASE_USER")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")

# If modifying these scopes, delete the file token.json.
SCOPES = [
  "https://www.googleapis.com/auth/drive"
]

INSTRUMENTS = {
  "Horn": ["French Horns", "French Horn", "Horns in F", "Horn in F", "Horn in Bb", "F. Horn", "F Horn", "Horns", "Horn"],
}

FOLDERS = {
  "Horn": "1lv4I1CBe5TKm3PGl3jQJi26RKp2sWMI9",
  "Lower Brass": "155Tr9gLrSHgbOopag7A6u6x4lVjhAevK",
  "Trumpet": "1kGZ8Hr3eTQUIGFwZwuJICOaS2Ih7tEe4",
  "Bass Clarinet": "16PJz8yAjAABtd9tQbV-UzA8rwVr5Q6yg",
  "Clarinet": "1itaYOezy66f61j20n-H2VBzvpexBjhaR",
  "Sax": "1IfvHMGccSvVFoH-FsokhOn4TJvOAGS_t",
  "Bassoon": "1P7pfqbbriKkZKheEE3hArfweOnTpJJnA",
  "Flutes": "1j7_vN0_uEBWM5aLQXFgwv7yJr56E5wPJ",
  "Oboe": "1M_IPSFni_L5dqm8_-S07WEPppjU98BhO",
  "Whistle": "1tIe7biSnbb9OrbYGmavP3ETXlBYq2fF9",
  "Acoustic Guitar": "1EqzHK7zQ0rl06A4LalHjjzeXehqy3t9x",
  "Electric Bass": "1SFeiD3MPNbIT-dMQohDpAEeRY3zLTybj",
  "Electric Guitar": "1bjxILXC8q7nfmJs0YsGS_HmMpXbFHXe1",
  "Cello": "1VAVlL5Rk03q0y5tOdocpW6lxLZtdx_FA",
  "Bass": "1lIK66u_gvYIovKOEwEyvslou_LK-RYYG",
  "Viola": "1TxxlNJMbg31obflDW4Ub17KUqRKPlmsh",
  "Percussion": "1p0ET_m81s8Q0tTF06rrEC_dor6DdhZXN",
  "Piano": "1joIJOxEk0dPAiLiHB89MMPxRRjcXJHsi",
  "Keys": "1irxzjpqUVclbGrpuxNwZZ07TTHJ5mJq2",
  "Violin1": "1rJgi1kTIgIHurL7wf11-MxJv5Krysdvd",
  "Violin2": "1oDMXOqeimW19rUdYXnAW9NoQmxymOnCb",
  "Vocals": "1FhrcsFNHZLwLHFtsgS5ySIkKwSIOXTJ9",
}

CURRENT_REP = "18M2IHnoO5clCbQulHw0Ru0MHp_oaIDC9"
service = None

def cache_result(data, filename):
  with open(filename, "wb") as f:
    pickle.dump(data, f)

def load_cached_result(filename):
  try:
    with open(filename, "rb") as f:
      return pickle.load(f)
  except (FileNotFoundError, EOFError, pickle.UnpicklingError):
    return None

def get_repertoire_files(service):
  resultsByFolder = {}

  for k, folderId in FOLDERS.items():
    # Initial request setup with all necessary parameters
    request_params = {
        "corpora": "drive",
        "driveId": "0AJcIG4T_o7QUUk9PVA",
        "includeItemsFromAllDrives": True,
        "supportsAllDrives": True,
        "q": f"mimeType='application/pdf' and '{folderId}' in parents",
        "orderBy": "name",
        "pageSize": 10,
        "fields": "nextPageToken, files(id, name, parents)",
    }

    # List all files in the shared drive 'IVGO Public'
    results = service.files().list(**request_params).execute()

    # Iterate through the pages of results
    while results:
      files = []
      items = results.get("files", [])
      for item in items:
        files.append({"id": item["id"], "name": item["name"]})
      
      resultsByFolder[k] = files

      # Check if there are more pages
      nextToken = results.get("nextPageToken")
      if nextToken:
        request_params.update({"pageToken": nextToken})
        results = service.files().list(**request_params).execute()
      else:
        break

  return resultsByFolder

def rename_file(service, file_id, file_name):
  # check the current name of the file and parse out the instrument name and piece name
  # if the instrument name is not in the file name, add it
  # the piece name is the text that does NOT match the possible values for instrument name
  piece_name = None

  # file_name is the current name of the file, check if it contains the instrument name
  for name in FOLDERS.keys():
    # match file_name against all possible values in INSTRUMENTS[name], break on the first match
    for instrument in INSTRUMENTS[name]:
      if instrument in file_name:
        # if the instrument name is in the file name, break the loop
        print(f"{file_name}: Found instrument name: {name}")
        # get the piece name from the remaining text which does not match the instrument
        piece_name = file_name.replace(instrument, "")
        # print(f"Piece name: {piece_name}")
        break
      else:
        print(f"{file_name}: Instrument name not found")
    break
  
  # delete the file from the local directory
  os.remove(file_name)



def file_matches_pattern(file_name):
  # check if the file name matches the pattern for the instrument
  for name in FOLDERS.keys():
    for instrument in INSTRUMENTS[name]:
      if instrument in file_name:
        return True
  return False

def connect_to_db():
  try:
    conn = psycopg2.connect(
      host=DATABASE_HOST,
      database=DATABASE_NAME,
      user=DATABASE_USER,
      password=DATABASE_PASSWORD,
    )
    print("Connected to database")
    return conn
  except (Exception, psycopg2.DatabaseError) as error:
    print(f"Error connecting to database: {error}")
    return None

def main():
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
  
  # connect to database
  conn = connect_to_db()

  try:
    service = build("drive", "v3", credentials=creds)

    # Get results to work with
    cache_name = 'repertoire_files.pkl'
    cached_data = load_cached_result(cache_name)
    results = None
    if cached_data is not None:
      results = cached_data
      print("Loaded cached data...")
    else:
      results = get_repertoire_files(service)
      print("Caching results...")
      cache_result(results, cache_name)

    for section in results.keys():
      print(f"Section: {section}")
      for file in results[section]:
        if file_matches_pattern(file["name"]):
          print(f"File: {file['name']} is ok")
        else:
          print(f"File: {file['name']} needs renaming")
          rename_file(service, file["id"], file["name"])
      break

  except HttpError as error:
    # TODO(developer) - Handle errors from drive API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()