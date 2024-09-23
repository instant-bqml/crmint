# Copyright 2020 Google Inc. All rights reserved.
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

"""CRMint's abstract worker dealing with BigQuery."""

import json
import os
import time

from google.api_core.client_info import ClientInfo
from google.cloud import bigquery
from jobs.workers import worker

PROJECT_DIR = os.path.join(os.path.dirname(__file__), '../../../')
CONFIG_PATH = os.path.join(PROJECT_DIR, 'consent', 'bigquery_opt_in.json')


class BQWorker(worker.Worker):
  """Abstract BigQuery worker."""

  _SCOPES = [
      'https://www.googleapis.com/auth/bigquery',
      'https://www.googleapis.com/auth/cloud-platform',
      'https://www.googleapis.com/auth/drive',
  ]

  def _get_client(self):
    try:
      with open(CONFIG_PATH, 'r') as fp:
        config = json.load(fp)
      bigquery_opt_in = config.get('bigquery_opt_in', False)
    except FileNotFoundError:
      bigquery_opt_in = False
    if bigquery_opt_in:
      client_info = ClientInfo(
        user_agent='cloud-solutions/crmint-ibqml-usage-v2')
    else:
      client_info = None
    return bigquery.Client(
      client_options={'scopes': self._SCOPES},
      client_info=client_info,
    )

  def _get_prefix(self):
    return f'{self._pipeline_id}_{self._job_id}_{self.__class__.__name__}'

  def _get_dry_run_job_config(self):
    return bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

  def _wait(self, job):
    """Waits for job completion and handles transient errors with retries."""
    delay = 5
    waiting_time = 0
    retries = 5
    attempt = 0
    while not job.done():
      if waiting_time > 300:  # Once 5 minutes have passed, spawn BQWaiter.
        self._enqueue('BQWaiter', {
          'job_id': job.job_id,
          'location': job.location
        }, 60)
        return
      try:
        time.sleep(delay)
        waiting_time += delay
        if job.done():
          break
      except worker.WorkerException as e:
        if attempt < retries:
          delay = min(30, delay * 2)  # Exponential backoff
          self.log_info(f'Transient error encountered: {e}. Retrying in {delay} seconds...')
          time.sleep(delay)
          attempt += 1
        else:
          self.log_error(f'Failed after {retries} attempts: {e}')
          raise worker.WorkerException(f'Failed after {retries} attempts: {e}')
    # Handle job error results with retries
    while job.error_result is not None and attempt < retries:
      delay = min(30, delay * 2)  # Exponential backoff
      self.log_info(f'Error encountered: {job.error_result["message"]}. Retrying in {delay} seconds...')
      time.sleep(delay)
      attempt += 1
      job.reload()  # Reload the job to check its status again
      if job.done() and job.error_result is None:
        return  # Exit if the job completes successfully

    if job.error_result is not None:
      self.log_error(f'Failed after {retries} attempts: {job.error_result["message"]}')
      raise worker.WorkerException(job.error_result['message'])
