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

"""Database helper methods."""

from typing import Callable, Optional

import flask
from sqlalchemy import orm

from common import crmint_logging
from controller import extensions
from controller import models


def load_fixtures(logger_func: Optional[Callable[[str], None]] = None) -> None:
  """Loads initial data into the database.

  Args:
    logger_func: Logger function to display the loading state.
  """
  general_settings = [
      'client_id', 'client_secret', 'emails_for_notifications',
      'google_ads_authentication_code', 'google_ads_refresh_token',
      'developer_token', 'app_conversion_api_developer_token']
  for setting in general_settings:
    general_setting = models.GeneralSetting.where(name=setting).first()
    if not general_setting:
      general_setting = models.GeneralSetting()
      general_setting.name = setting
      general_setting.save()
      if logger_func:
        logger_func('Added setting %s' % setting)


def reset_jobs_and_pipelines_statuses_to_idle() -> None:
  """Resets the statuses of all jobs and pipelines to 'idle'."""
  session = extensions.db.session
  batch_size = 1000
  offset = 0

  # Reset job statuses in batches
  while True:
    jobs = session.query(models.Job).offset(offset).limit(batch_size).all()
    if not jobs:
      break
    for job in jobs:
      job.status = 'idle'
    session.commit()
    offset += batch_size

  # Reset pipeline statuses in batches
  offset = 0
  while True:
    pipelines = session.query(models.Pipeline).offset(offset).limit(batch_size).all()
    if not pipelines:
      break
    for pipeline in pipelines:
      pipeline.status = 'idle'
    session.commit()
    offset += batch_size


def truncate_enqueued_tasks():
  """Truncates the enqueued_tasks table."""
  session = extensions.db.session
  session.execute('TRUNCATE TABLE enqueued_tasks')
  session.commit()


def get_tasks_info():
  """Retrieves information about the oldest task and count of running tasks."""
  oldest_task = models.TaskEnqueued.query.order_by(models.TaskEnqueued.id).first()
  running_tasks_count = models.TaskEnqueued.query.count()
  return {
    'oldest_task_time': oldest_task.created_at if oldest_task else None,
    'running_tasks_count': running_tasks_count
  }


def shutdown(app: flask.Flask) -> None:
  """Cleans database state."""
  # Find all Sessions in memory and close them.
  orm.close_all_sessions()
  crmint_logging.log_global_message(
      'All sessions closed.', log_level='WARNING')
  # Each connection was released on execution, so just formally
  # dispose of the db connection if it's been instantiated
  extensions.db.get_engine(app).dispose()
  crmint_logging.log_global_message(
      'Database connection disposed.', log_level='WARNING')
