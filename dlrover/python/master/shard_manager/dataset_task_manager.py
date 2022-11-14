import time
from typing import List, Dict
from dlrover.python.master.shard_manager.base_task_manager import (
    TaskManger,
    Task,
)
from dlrover.python.master.shard_manager.dataset_splitter import (
    DatasetSplitter,
)
from dlrover.python.common.log_utils import default_logger as logger

_MAX_TASK_RETRIES = 3


class DoingTask(object):
    """DoingTask records which worker fetches a task and when.
    Attributes:
        task: a task with a data shard.
        worker_id: the id of a worker.
        start_time: the timestamp of a worker to fetch the task.
    """
    def __init__(self, task: Task, worker_id: int, start_time: int):
        self.task = task
        self.worker_id = worker_id
        self.start_time = start_time


class DatasetTaskManager(TaskManger):
    def __init__(
        self,
        task_type,
        dataset_splitter: DatasetSplitter,
    ):
        self._task_type = task_type
        self._dataset_splitter = dataset_splitter
        self._todo: List[Task] = []
        self._doing: Dict[int, DoingTask] = {}
        self._max_task_completed_time = 0
        self._task_id = 0
        self._workers = set()

    def reset(self):
        self._todo = []
        self._doing = {}
        self._task_id = 0
        self._max_task_completed_time = 0

    def get_task(self, worker_id) -> Task:
        """Return next Task"""

        if not self._todo and not self._dataset_splitter.epoch_finished():
            # Start a new epoch
            # num_epochs <= 0 indicates that the master will create data
            # shards infinitely. So, the worker can use the dataset like
            # `dataset.repeat()`.
            self._dataset_splitter.create_shards()
            shards = self._dataset_splitter.get_shards()
            self._create_todo_tasks(shards)
        if not self._todo:
            # No more tasks
            return None

        task: Task = self._todo.pop(0)
        self._doing[task.task_id] = DoingTask(
            task, worker_id, int(time.time())
        )

        self._workers.add(worker_id)
        logger.info(
            "Assign task %s of dataset %s to worker %s",
            task.task_id,
            self._dataset_splitter.dataset_name,
            worker_id,
        )
        return task

    def completed(self):
        return (
            self._dataset_splitter.epoch_finished()
            and not self._todo
            and not self._doing
        )

    def _create_todo_tasks(self, shards):
        tasks = []
        for shard in shards:
            task = Task(self._task_id, self._task_type, shard)
            tasks.append(task)
            self._task_id += 1

        logger.info(
            "todo.extend: %d tasks created for "
            "dataset = %s with total of %s records."
            % (len(tasks), self._dataset_splitter.dataset_name, self._dataset_splitter.dataset_size)
        )
        self._todo.extend(tasks)

    def report_task_status(self, task_id, success) -> [bool, DoingTask]:
        doing_task = self._doing.pop(task_id)
        if not doing_task:
            logger.warning(
                "Unknown task_id: %d of dataset %s"
                % (task_id, self._dataset_splitter.dataset_name)
            )
            success = False
        elif not success:
            logger.warning(
                "Task %d of %s failed " % (task_id, self._dataset_splitter.dataset_name)
            )
            self.recover_task(doing_task.task)
        else:
            logger.info(
                "Task:%d completed, %d remaining tasks for Dataset %s",
                task_id,
                len(self._todo) + len(self._doing),
                self._dataset_splitter.dataset_name,
            )
        return success, doing_task

    def recover_task(self, task):
        if not self._check_exceed_max_task_retries(task):
            self.todo.append(task)

    def _check_exceed_max_task_retries(self, task: Task):
        task.retry_count += 1
        if task.retry_count > _MAX_TASK_RETRIES:
            logger.error(
                "A task %s of failed with %d retries "
                % (task.shard.name, _MAX_TASK_RETRIES)
            )
            return True
        return False

    # TODO:implement the function
    def checkpoint(self):
        """Checkpoint todo and doing to a file."""
        pass

    # TODO:implement the function
    def restore_checkpoint(self, checkpoint):
        """Restore the task manager from a checkpoint"""
        pass
