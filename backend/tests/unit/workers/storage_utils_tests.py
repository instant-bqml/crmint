"""Tests for storage_utils."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.cloud import storage

from jobs.workers.storage import storage_utils


class StorageUtilsTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    mock_client = mock.create_autospec(
        storage.Client, instance=True, spec_set=True)

    def _list_blobs(bucket):
      if bucket.name == 'bucket1':
        return [
            storage.Blob('foo/file1.csv', 'bucket1'),
            storage.Blob('foo/file2.csv', 'bucket1'),
            storage.Blob('bar/file3.csv', 'bucket1'),
        ]
      elif bucket.name == 'bucket2':
        return [
            storage.Blob('foo/file1.csv', 'bucket2'),
        ]
      else:
        raise ValueError(f'Unknown bucket: {bucket.name}')

    mock_client.list_blobs.side_effect = _list_blobs
    self.client = mock_client

  @parameterized.named_parameters(
      {'testcase_name': 'No match',
       'uri_patterns': ['gs://bucket1/nomatch/file*.csv'],
       'expected_matched_uris': []},
      {'testcase_name': 'Matching uris with wildcards',
       'uri_patterns': ['gs://bucket1/foo/file*.csv'],
       'expected_matched_uris':
           ['gs://bucket1/foo/file1.csv', 'gs://bucket1/foo/file2.csv']},
      {'testcase_name': 'Matching uris without wildcards',
       'uri_patterns':
           ['gs://bucket1/bar/file3.csv', 'gs://bucket1/foo/file1.csv'],
       'expected_matched_uris':
           ['gs://bucket1/foo/file1.csv', 'gs://bucket1/bar/file3.csv']},
      {'testcase_name': 'Matching same uris in multiple buckets',
       'uri_patterns':
           ['gs://bucket1/foo/file1.csv', 'gs://bucket2/foo/file1.csv'],
       'expected_matched_uris':
           ['gs://bucket1/foo/file1.csv', 'gs://bucket2/foo/file1.csv']},
      {'testcase_name': 'One match only with overlapping patterns',
       'uri_patterns':
           ['gs://bucket2/foo/file1.csv', 'gs://bucket2/foo/file*.csv'],
       'expected_matched_uris': ['gs://bucket2/foo/file1.csv']},
  )
  def test_matching_uris(self, uri_patterns, expected_matched_uris):
    matched_uris = storage_utils.get_matched_uris(self.client, uri_patterns)
    self.assertCountEqual(matched_uris, expected_matched_uris)


if __name__ == '__main__':
  absltest.main()