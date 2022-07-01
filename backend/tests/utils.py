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

"""Testing utils."""

import os
from unittest import mock

from absl.testing import parameterized
import flask
import requests

from common import crmint_logging
from common import insight
from common import task
from controller import app
from controller import database
from controller import extensions


class ModelTestCase(parameterized.TestCase):
  """Base class for model testing."""

  def setUp(self):
    super().setUp()
    # Pushes an application context manually.
    test_app = flask.Flask(__name__)
    extensions.db.init_app(test_app)
    self.ctx = test_app.app_context()
    self.ctx.push()
    # Creates tables & loads seed data
    extensions.db.create_all()

  def tearDown(self):
    super().tearDown()
    # Drops the app context
    self.ctx.pop()


class AppTestCase(parameterized.TestCase):
  """Base class for app testing."""

  ctx = None
  client = None

  def create_app(self):
    raise NotImplementedError

  @mock.patch.dict(os.environ, {'DATABASE_URI': 'sqlite:///:memory:'})
  def setUp(self):
    super().setUp()
    test_app = self.create_app()
    # Pushes an application context manually.
    self.ctx = test_app.app_context()
    self.ctx.push()
    self.client = test_app.test_client()
    self.patched_task_enqueue = self.enter_context(
        mock.patch.object(task.Task, 'enqueue', autospec=True))
    self.patched_log_message = self.enter_context(
        mock.patch.object(crmint_logging, 'log_message', autospec=True))
    self.patched_task_enqueue = self.enter_context(
        mock.patch.object(insight.GAProvider, 'track_event', autospec=True))
    # Mocks the auth request to the favicon.
    mock_auth_response = mock.create_autospec(requests.Response)
    mock_auth_response.status_code = 200
    self.patched_requests_head = self.enter_context(
        mock.patch.object(
            requests, 'head', autospec=True, return_value=mock_auth_response))

  def tearDown(self):
    super().tearDown()
    # Drops the app context
    self.ctx.pop()


class ControllerAppTest(AppTestCase):
  """Controller app test class."""

  def create_app(self):
    test_app = app.create_app()
    test_app.config['TESTING'] = True
    test_app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    return test_app

  @mock.patch.dict(os.environ, {'DATABASE_URI': 'sqlite:///:memory:'})
  def setUp(self):
    super().setUp()
    # Creates tables & loads seed data
    extensions.db.create_all()
    database.load_fixtures()

  def tearDown(self):
    # Ensures next test is in a clean state
    extensions.db.drop_all()
    super().tearDown()
