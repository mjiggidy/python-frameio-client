import requests
import math
import os

class FrameioDownloader(object):
  def __init__(self, asset, download_folder):
    self.asset = asset
    self.download_folder = download_folder

  def download(self):
    # TODO add test to chere here to make sure the URL we download is coming from our S3 buckets
    # Grab the filename from the passed dictionary and store it.
    original_filename = self.asset['name']
    final_destination = os.path.join(self.download_folder, original_filename)
    
    # Grab the origial_url from the passed dictionary, then download the file
    url = self.asset['original']
    r = requests.get(url)
    open(final_destination, 'wb').write(r.content)
    