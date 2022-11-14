# Copyright 2022 The EasyDL Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from dlrover.python.master.shard_manager.dataset_splitter import (
    TableDatasetSplitter,
)
from dlrover.python.master.shard_manager.dataset_task_manager import (
    DatasetTaskManager
)
from dlrover.python.common.constants import TaskType


class DatasetTaskMangerTest(unittest.TestCase):
    def test_create_shards(self):
        splitter = TableDatasetSplitter(
            dataset_name="test",
            dataset_size=10000,
            shard_size=100,
            num_epochs=1,
        )
        task_manager = DatasetTaskManager(TaskType.TRAINING, splitter)
        worker_id = 0
        task = task_manager.get_task(worker_id)
        self.assertEqual(task.task_id, 0)
        self.assertEqual(len(task_manager._todo), 99)
        self.assertEqual(len(task_manager._doing), 1)
        self.assertFalse(task_manager.completed())

        task_manager.report_task_status(task.task_id, True)
        self.assertEqual(len(task_manager._doing), 0)

        for i in range(101):
            task = task_manager.get_task(worker_id)
            if not task:
                break
            task_manager.report_task_status(task.task_id, True)
        self.assertTrue(task_manager.completed())
