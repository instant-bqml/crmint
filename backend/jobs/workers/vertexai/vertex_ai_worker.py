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

"""CRMint's worker that waits for a Vertex AI job completion."""

import time
from google.cloud import aiplatform
from jobs.workers.worker import Worker, WorkerException


class VertexAIWorker(Worker):
  """Worker that polls job status and respawns itself if the job is not done."""

  def _wait(self, job):
    """Waits for job completion and relays to VertexAIWaiter if it takes too long."""
    delay = 5
    waiting_time = 5
    time.sleep(delay)
    while job.wait_for_resource_creation() is None:
      if waiting_time > 300:  # Once 5 minutes have passed, spawn VertexAIWaiter.
        self._enqueue('VertexAIWaiter', {'pipeline_id': job.resource_name}, 300)
        return
      if delay < 30:
        delay = [5, 10, 15, 20, 30][int(waiting_time / 60)]
      time.sleep(delay)
      waiting_time += delay