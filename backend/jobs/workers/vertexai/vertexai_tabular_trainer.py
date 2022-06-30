# Copyright 2022 Google Inc. All rights reserved.
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

"""CRMint's worker executing Vertex AI tabular training."""

from google.cloud import aiplatform

from jobs.workers.worker import Worker, WorkerException
from jobs.workers.vertexai.vertexai_worker import VertexAIWorker


class VertexAITabularTrainer(VertexAIWorker):
  """Worker to train a Vertex AI AutoML model using a Vertex dataset."""

  PARAMS = [
      ('project_id', 'string', True, '', 'Project ID'),
      ('region', 'string', True, '', 'Region'),
      ('vertexai_dataset_name', 'string', True, '', 'Vertex AI Dataset Name'),
      ('prediction_type', 'string', True, '', 'Prediction Type '
       '(regression or classification)'),
      ('target_column', 'string', True, '', 'Target Column'),
      ('budget_hours', 'number', True, 1, 'Training Budget Hours (1 thru 72)'),
      ('vertexai_model_name', 'string', True, '', 'Vertex AI Model Name'),
      ('clean_up', 'boolean', True, True, 'Clean Up'),
  ]

  def _get_vertexai_tabular_dataset(self):
    display_name = self._params['vertexai_dataset_name']
    dataset = aiplatform.TabularDataset.list(
      filter=f'display_name="{display_name}"')
    if len(dataset) > 1:
      dataset = aiplatform.TabularDataset.list(
        filter=f'display_name="{display_name}"', order_by='create_time desc')
    for ds in dataset:
      return ds
    return None

  def _create_automl_tabular_training_job(self):
    vertexai_model_name = self._params['vertexai_model_name']
    prediction_type = self._params['prediction_type']
    return aiplatform.AutoMLTabularTrainingJob(
      display_name=f'{vertexai_model_name}',
      optimization_prediction_type=f'{prediction_type}')

  def _clean_up_models(self):
    if self._params['clean_up']:
      vertexai_model_name = self._params['vertexai_model_name']
      try:
        models = aiplatform.Model.list(
          filter=f"display_name={vertexai_model_name}", order_by="create_time")
        if models:
          for i, model in enumerate(models[:-1]):
            m = models[i]
            aiplatform.Model.delete(m)
            self.log_info(f'Deleted model: {m.resource_name}.')
      except Exception as e:
        self.log_info(f'Exception: {e}')

  def _execute_training(self):
    aiplatform.init()
    project_id = self._params['project_id']
    budget_hours = self._params['budget_hours']
    target_column = self._params['target_column']
    vertexai_model_name = self._params['vertexai_model_name']
    region = self._params['region']
    vertexai_region = region if region[-1].isdigit() else f'{region}1'
    pipeline_client = self._get_vertexai_pipeline_client(vertexai_region)
    dataset = self._get_vertexai_tabular_dataset()
    if not dataset:
      self.log_info('No Vertex AI dataset found. Try again.')
      return
    if self._params['clean_up']:
      self._clean_up_training_pipelines(pipeline_client, project_id, vertexai_region)
      self._clean_up_models()
    job = self._create_automl_tabular_training_job()
    job.run(
      dataset=dataset,
      target_column=f'{target_column}',
      budget_milli_node_hours=f'{budget_hours * 1000}',
      model_display_name=f'{vertexai_model_name}',
      disable_early_stopping=False,
      sync=False,
    )
    job.wait_for_resource_creation()
    self.log_info(f'{job}')
    self.log_info(f'{job.resource_name}')
    pipeline_name = job.resource_name
    pipeline = self._get_training_pipeline(pipeline_client, pipeline_name)
    self._wait_for_pipeline(pipeline)

  def _execute(self):
    self._execute_training()
