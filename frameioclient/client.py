import re
import sys
import requests
import warnings
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from .download import FrameioDownloader
from .exceptions import PresentationException

if sys.version_info.major >= 3:
  from .py3_uploader import FrameioUploader
else:
  from .py2_uploader import FrameioUploader

class PaginatedResponse(object):
  def __init__(self, results=[], page=0, page_size=0, total=0, total_pages=0):
    super(PaginatedResponse, self).__init__()
    self.results = results
    self.page = int(page)
    self.page_size = int(page_size)
    self.total = int(total)
    self.total_pages = int(total_pages)
  
  def __iter__(self):
    return iter(self.results)

class FrameioClient(object):
  def __init__(self, token, host='https://api.frame.io'):
    self.token = token
    self.host = host
    self.retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429],
        method_whitelist=["POST", "OPTIONS", "GET"]
    )
    self.client_version = self._get_version()

  def _get_version(self):
    try:
        from importlib import metadata
    except ImportError:
        # Running on pre-3.8 Python; use importlib-metadata package
        import importlib_metadata as metadata

    return metadata.version('frameioclient')

  def _api_call(self, method, endpoint, payload={}):
    url = '{}/v2{}'.format(self.host, endpoint)

    headers = {
      'Authorization': 'Bearer {}'.format(self.token),
      'x-frameio-client': 'python/{}'.format(self.client_version)
    }

    adapter = HTTPAdapter(max_retries=self.retry_strategy)

    http = requests.Session()
    http.mount("https://", adapter)

    r = http.request(
      method,
      url,
      json=payload,
      headers=headers,
    )

    if r.ok:
      if r.headers.get('page-number'):
        if int(r.headers.get('total-pages')) > 1:
          return PaginatedResponse(
            results=r.json(), 
            page=r.headers['page-number'], 
            page_size=r.headers['per-page'],
            total_pages=r.headers['total-pages'],
            total=r.headers['total']
          )

      return r.json()
    
    if r.status_code == 422 and "presentation" in endpoint:
      raise PresentationException

    return r.raise_for_status()

  def get_me(self):
    """
    Get the current user.
    """
    return self._api_call('get', '/me')

  def create_team(self, account_id, **kwargs):
    """
    Create a Team.

    :Args:
      account_id (string): The account id you want to create this Team under.
    :Kwargs:
      (optional) kwargs: additional request parameters.

      Example::

        client.create_team(
          account_id="6bdcb4d9-4548-4548-4548-27a6c024ae6b",
          name="My Awesome Project",
        )
    """
    warnings.warn('Note: Your token must support team.create scopes')
    endpoint = '/accounts/{}/teams'.format(account_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def get_teams(self, account_id, **kwargs):
    """
    Get teams owned by the account. 
    (To return all teams, use get_all_teams())
    
    :Args:
      account_id (string): The account id.
    """
    endpoint = '/accounts/{}/teams'.format(account_id)
    return self._api_call('get', endpoint, kwargs)
  
  def get_team(self, team_id):
    """
    Get's a team by id

    :Args:
      team_id (string): the team's id
    """
    endpoint  = '/teams/{}'.format(team_id)
    return self._api_call('get', endpoint)

  def get_all_teams(self, **kwargs):
    """
    Get all teams for the authenticated user.

    :Args:
      account_id (string): The account id.
    """
    endpoint = '/teams'
    return self._api_call('get', endpoint, kwargs)

  def get_projects(self, team_id, **kwargs):
    """
    Get projects owned by the team.

    :Args:
      team_id (string): The team id.
    """
    endpoint = '/teams/{}/projects'.format(team_id)
    return self._api_call('get', endpoint, kwargs)
  
  def get_project(self, project_id):
    """
    Get an individual project

    :Args:
      project_id (string): the project's id
    """
    endpoint = '/projects/{}'.format(project_id)
    return self._api_call('get', endpoint)
  
  def get_collaborators(self, project_id, **kwargs):
    """
    Get collaborators for a project

    :Args:
      project_id (string): the project's id
    """
    endpoint = "/projects/{}/collaborators".format(project_id)
    return self._api_call('get', endpoint, kwargs)

  def get_pending_collaborators(self, project_id, **kwargs):
    """
    Get pending collaborators for a project

    :Args:
      project_id (string): the project's id
    """
    endpoint = "/projects/{}/pending_collaborators".format(project_id)
    return self._api_call('get', endpoint, kwargs)

  def create_project(self, team_id, **kwargs):
    """
    Create a project.

    :Args:
      team_id (string): The team id.
    :Kwargs:
      (optional) kwargs: additional request parameters.

      Example::

        client.create_project(
          team_id="123",
          name="My Awesome Project",
        )
    """
    endpoint = '/teams/{}/projects'.format(team_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def get_asset(self, asset_id):
    """
    Get an asset by id.

    :Args:
      asset_id (string): The asset id.
    """
    endpoint = '/assets/{}'.format(asset_id)
    return self._api_call('get', endpoint)

  def get_asset_children(self, asset_id, **kwargs):
    """
    Get an asset's children.

    :Args:
      asset_id (string): The asset id.
    """
    endpoint = '/assets/{}/children'.format(asset_id)
    return self._api_call('get', endpoint, kwargs)

  def move_asset(self, destination_folder, **kwargs):
    """
    Move an asset.

    :Args:
      asset_id (string): The asset you're trying to move.
    :Kwargs:
      destination_folder (string): The destination folder you're moving the file into

      Example::

        client.move_asset(
          destination_folder="123abc",
          id="123abc",
        )
    """
    endpoint = '/assets/{}/move'.format(destination_folder)
    return self._api_call('post', endpoint, payload=kwargs)

  def bulk_move_assets(self, destination_folder_id, asset_list=[]):
    """
    Bulk copy assets

    :Args:
      destination_folder_id (string): The id of the folder you want to move your assets into.
    :Kwargs:
      asset_list (list): A list of the asset IDs you want to move.

      Example::
        client.bulk_copy_assets("adeffee123342", asset_list=["7ee008c5-49a2-f8b5-997d-8b64de153c30", \ 
        "7ee008c5-49a2-f8b5-997d-8b64de153c30"])
    """
    
    payload = {"batch": []}
    new_list = list()

    for asset in asset_list:
      payload['batch'].append({"id": asset})

    print(payload)

    endpoint = '/batch/assets/{}/move'.format(destination_folder_id)
    return self._api_call('post', endpoint, payload)

  def create_asset(self, parent_asset_id, **kwargs):
    """
    Create an asset.

    :Args:
      parent_asset_id (string): The parent asset id.
    :Kwargs:
      (optional) kwargs: additional request parameters.

      Example::

        client.create_asset(
          parent_asset_id="123abc",
          name="ExampleFile.mp4",
          type="file",
          filetype="video/mp4",
          filesize=123456
        )
    """
    endpoint = '/assets/{}/children'.format(parent_asset_id)
    return self._api_call('post', endpoint, payload=kwargs)
  
  def update_asset(self, asset_id, **kwargs):
    """
    Updates an asset

    :Args:
      asset_id (string): the asset's id
    :Kwargs:
      the fields to update

      Example::
        client.update_asset("adeffee123342", name="updated_filename.mp4")
    """
    endpoint = '/assets/{}'.format(asset_id)
    return self._api_call('put', endpoint, kwargs)

  def copy_asset(self, destination_folder_id, **kwargs):
    """
    Copy an asset

    :Args:
      destination_folder_id (string): The id of the folder you want to copy into.
    :Kwargs:
      id (string): The id of the asset you want to copy.

      Example::
        client.copy_asset("adeffee123342", id="7ee008c5-49a2-f8b5-997d-8b64de153c30")
    """
    endpoint = '/assets/{}/copy'.format(destination_folder_id)
    return self._api_call('post', endpoint, kwargs)

  def bulk_copy_assets(self, destination_folder_id, asset_list=[], copy_comments=False):
    """
    Bulk copy assets

    :Args:
      destination_folder_id (string): The id of the folder you want to copy into.
    :Kwargs:
      asset_list (list): A list of the asset IDs you want to copy.
      copy_comments (boolean): Whether or not to copy comments: True or False.

      Example::
        client.bulk_copy_assets("adeffee123342", asset_list=["7ee008c5-49a2-f8b5-997d-8b64de153c30", \ 
        "7ee008c5-49a2-f8b5-997d-8b64de153c30"], copy_comments=True)
    """
    
    payload = {"batch": []}
    new_list = list()

    if copy_comments:
      payload['copy_comments'] = "all"

    for asset in asset_list:
      payload['batch'].append({"id": asset})

    endpoint = '/batch/assets/{}/copy'.format(destination_folder_id)
    return self._api_call('post', endpoint, payload)

  def delete_asset(self, asset_id):
    """
    Delete an asset

    :Args:
      asset_id (string): the asset's id
    """
    endpoint = '/assets/{}'.format(asset_id)
    return self._api_call('delete', endpoint)

  def upload(self, asset, file):
    """
    Upload an asset. The method will exit once the file is uploaded.

    :Args:
      asset (object): The asset object.
      file (file): The file to upload.

      Example::

        client.upload(asset, open('example.mp4')) // TODO fix this example (bad way of opening file)
    """
    uploader = FrameioUploader(asset, file)
    uploader.upload()
  
  def download(self, asset, download_folder):
    """
    Download an asset. The method will exit once the file is downloaded.

    :Args:
      asset (object): The asset object.
      download_folder (path): The location to download the file to.

      Example::

        client.download(asset, "~./Downloads")
    """
    downloader = FrameioDownloader(asset, download_folder)
    downloader.download()

  def get_comment(self, comment_id, **kwargs):
    """
    Get a comment.

    :Args:
      comment_id (string): The comment id.
    """
    endpoint = '/comments/{}'.format(comment_id)
    return self._api_call('get', endpoint, **kwargs)

  def get_comments(self, asset_id, **kwargs):
    """
    Get an asset's comments.

    :Args:
      asset_id (string): The asset id.
    """
    endpoint = '/assets/{}/comments'.format(asset_id)
    return self._api_call('get', endpoint, **kwargs)

  def create_comment(self, asset_id, **kwargs):
    """
    Create a comment.

    :Args:
      asset_id (string): The asset id.
    :Kwargs:
      (optional) kwargs: additional request parameters.

      Example::

        client.create_comment(
          asset_id="123abc",
          text="Hello world"
        )
    """
    endpoint = '/assets/{}/comments'.format(asset_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def update_comment(self, comment_id, **kwargs):
    """
    Update a comment.

    :Args:
      comment_id (string): The comment id.
    :Kwargs:
      (optional) kwargs: additional request parameters.

      Example::

        client.create_comment(
          comment_id="123abc",
          text="Hello world"
        )
    """
    endpoint = '/comments/{}'.format(comment_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def delete_comment(self, comment_id):
    """
    Delete a comment.

    :Args:
      comment_id (string): The comment id.
    """
    endpoint = '/comments/{}'.format(comment_id)
    return self._api_call('delete', endpoint)

  def get_review_links(self, project_id):
    """
    Get the review links of a project

    :Args:
      asset_id (string): The asset id.
    """
    endpoint = '/projects/{}/review_links'.format(project_id)
    return self._api_call('get', endpoint)

  def create_presentation_link(self, asset_id, **kwargs):
    """
    Create a presentation link.

    :Args:
      asset_id (string): The asset id.
    :Kwargs:
      kwargs: additional request parameters.

      Example::

        client.create_presentation_link(
          asset_id="9cee7966-4066-b326-7db1-f9e6f5e929e4",
          title="My fresh presentation",
          password="abc123"
        )
    """
    endpoint = '/assets/{}/presentations'.format(asset_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def create_review_link(self, project_id, **kwargs):
    """
    Create a review link.

    :Args:
      project_id (string): The project id.
    :Kwargs:
      kwargs: additional request parameters.

      Example::

        client.create_review_link(
          project_id="123",
          name="My Review Link",
          password="abc123"
        )
    """
    endpoint = '/projects/{}/review_links'.format(project_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def get_review_link(self, link_id, **kwargs):
    """
    Get a single review link

    :Args:
      link_id (string): The review link id.
    """
    endpoint = '/review_links/{}'.format(link_id)
    return self._api_call('get', endpoint, payload=kwargs)

  def update_review_link_assets(self, link_id, **kwargs):
    """
    Add or update assets for a review link.

    :Args:
      link_id (string): The review link id.
    :Kwargs:
      kwargs: additional request parameters.

      Example::

        client.update_review_link_assets(
          link_id="123",
          asset_ids=["abc","def"]
        )
    """
    endpoint = '/review_links/{}/assets'.format(link_id)
    return self._api_call('post', endpoint, payload=kwargs)

  def update_review_link(self, link_id, **kwargs):
    """
    Updates review link settings.

    :Args:
      link_id (string): The review link id.
    :Kwargs:
      kwargs: additional request parameters.

      Example::

        client.update_review_link(
          link_id,
          expires_at="2020-04-08T12:00:00+00:00",
          is_active=False,
          name="Review Link 123",
          password="my_fun_password",
        )
    """
    endpoint = '/review_links/{}'.format(link_id)
    return self._api_call('put', endpoint, payload=kwargs)

  def get_review_link_items(self, link_id):
    """
    Get items from a single review link.

    :Args:
      link_id (string): The review link id.

      Example::

        client.get_review_link_items(
          link_id="123"
        )
    """
    endpoint = '/review_links/{}/items'.format(link_id)
    return self._api_call('get', endpoint)

  def get_audit_logs(self, account_id):
    """
    Get audit logs for the currently authenticated account.

    :Args:

      Example::

        client.get_audit_logs(
          account_id="6bdcb4d9-9a2e-a765-4548-ae6b27a6c024"
        )
    """
    endpoint = '/accounts/{}/audit_logs'.format(account_id)
    return self._api_call('get', endpoint)
