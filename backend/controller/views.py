# Copyright 2018 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""General section."""
import threading
from threading import Lock
import subprocess

from flask import Blueprint
from flask import jsonify
from flask_restful import Api
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import reqparse
from flask_restful import Resource

from controller import ads_auth_code
from controller import app_data
from controller import database
from controller import models

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# from google.appengine.api import urlfetch

blueprint = Blueprint('general', __name__)
api = Api(blueprint)

parser = reqparse.RequestParser()
parser.add_argument('variables', type=list, location='json')

settings_parser = reqparse.RequestParser()
settings_parser.add_argument('settings', type=list, location='json')

param_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'type': fields.String,
    'value': fields.Raw(attribute='api_value'),
}

setting_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'value': fields.String,
}

settings_fields = {
    'settings': fields.List(fields.Nested(setting_fields)),
}

# Global variable to track the upgrade status
upgrade_status = {
    'status': 'idle',  # Possible values: 'idle', 'in_progress', 'completed', 'failed'
    'message': ''
}

configuration_fields = {
    'sa_email': fields.String,
    'variables': fields.List(fields.Nested(param_fields)),
    'settings': fields.List(fields.Nested(setting_fields)),
    # Added value
    'google_ads_auth_url': fields.String,
}

global_variables_fields = {
    'variables': fields.List(fields.Nested(param_fields)),
}


class Configuration(Resource):
  """Fetches configuration parameters."""

  @marshal_with(configuration_fields)
  def get(self):
    # urlfetch.set_default_fetch_deadline(300)
    query = models.Param.where(pipeline_id=None, job_id=None)
    params = query.order_by(models.Param.name)
    settings = models.GeneralSetting.query.order_by(models.GeneralSetting.name)

    # Get client id and secret from input fields stored in database
    client_id = models.GeneralSetting.where(name='client_id').first().value
    # Url to redirect
    url = ads_auth_code.get_url(client_id)

    return {
        'sa_email': app_data.APP_DATA['sa_email'],
        'variables': params,
        'settings': settings,
        # Added url to config
        'google_ads_auth_url': url,
    }


class GlobalVariable(Resource):
  """Updates a global parameter."""

  @marshal_with(global_variables_fields)
  def put(self):
    args = parser.parse_args()
    models.Param.update_list(args.get('variables'))
    return {
        'variables': models.Param.where(pipeline_id=None, job_id=None).all()
    }


class GeneralSettingsRoute(Resource):
  """Updates general settings, among them Google Ads authentication."""

  @marshal_with(settings_fields)
  def put(self):
    args = settings_parser.parse_args()
    # Get client id and secret from input fields stored in database
    client_id = models.GeneralSetting.where(name='client_id').first().value
    client_secret = models.GeneralSetting.where(
        name='client_secret').first().value

    # Gets value from the google_ads_authentication_code field
    ads_code = [d['value'] for d in args['settings']
                if d['name'] == 'google_ads_authentication_code'][0]
    if ads_code:
      token = ads_auth_code.get_token(client_id, client_secret, ads_code)
    else:
      token = None

    settings = []
    for arg in args['settings']:
      setting = models.GeneralSetting.where(name=arg['name']).first()
      if setting:
        if setting.name == 'google_ads_refresh_token' and token:
          setting.update(value=token)
        elif setting.name == 'google_ads_authentication_code':
          setting.update(value='')
        else:
          setting.update(value=arg['value'])
      settings.append(setting)
    return settings


class ResetStatuses(Resource):
  """Endpoint to reset pipelines and jobs statuses."""

  def post(self):
    try:
      database.reset_jobs_and_pipelines_statuses_to_idle()
      return '', 200
    except Exception as e:
      return {'error': str(e)}, 500



upgrade_status_lock = Lock()

class UpgradeApplication(Resource):
  """Endpoint to upgrade the application."""
  def post(self):
    with upgrade_status_lock:
      if upgrade_status['status'] == 'in_progress':
        return {'error': 'Upgrade already in progress'}, 400

      # Start the upgrade process in a separate thread
      upgrade_thread = threading.Thread(target=self.perform_upgrade)
      upgrade_thread.start()
      return '', 202

  def get(self):
    with upgrade_status_lock:
      return jsonify(upgrade_status)

  def perform_upgrade(self):
    global upgrade_status
    with upgrade_status_lock:
      upgrade_status['status'] = 'in_progress'
      upgrade_status['message'] = 'Upgrade started'

    try:
      # Execute the upgrade command
      command = ["bash", "-c", "bash <(curl -Ls https://raw.githubusercontent.com/instant-bqml/crmint/master/scripts/install.sh) master --bundle"]
      result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      with upgrade_status_lock:
        # Update the status to completed
        upgrade_status['status'] = 'completed'
        upgrade_status['message'] = 'Upgrade completed successfully'
        logger.info('Upgrade completed successfully')
    except subprocess.CalledProcessError as e:
      with upgrade_status_lock:
        # Update the status to failed
        upgrade_status['status'] = 'failed'
        upgrade_status['message'] = f'Upgrade failed: {e.stderr.decode()}'
        logger.error(f'Upgrade failed: {e.stderr.decode()}')
    except Exception as e:
      with upgrade_status_lock:
        # Update the status to failed
        upgrade_status['status'] = 'failed'
        upgrade_status['message'] = f'Upgrade failed: {str(e)}'
        logger.error(f'Upgrade failed: {str(e)}')


api.add_resource(Configuration, '/configuration')
api.add_resource(GlobalVariable, '/global_variables')
api.add_resource(GeneralSettingsRoute, '/general_settings')
api.add_resource(ResetStatuses, '/reset/statuses')
api.add_resource(UpgradeApplication, '/upgrade')