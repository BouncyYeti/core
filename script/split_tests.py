#!/usr/bin/env python3
"""Helper script to split test into n buckets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from math import ceil
import os
import re


@dataclass
class TestFile:
    """Class to hold test information."""

    path: str
    total_tests: int


@dataclass
class TestFolder:
    """Class to hold test information."""

    path: str
    children: list[TestFolder | TestFile] = field(default_factory=list)

    @property
    def total_tests(self) -> int:
        """Return total tests."""
        return sum([test.total_tests for test in self.children])

    def __repr__(self):
        """Return representation."""
        return f"TestFolder(path='{self.path}', total={self.total_tests}, children={len(self.children)})"


def count_tests(test_folder: TestFolder) -> int:
    """Count tests in folder."""
    max_tests_in_file = 0
    for entry in os.listdir(test_folder.path):
        if entry in ("__pycache__", "__init__.py", "conftest.py"):
            continue

        entry_path = os.path.join(test_folder.path, entry)
        if os.path.isdir(entry_path):
            sub_folder = TestFolder(entry_path)
            test_folder.children.append(sub_folder)
            max_tests_in_file = max(max_tests_in_file, count_tests(sub_folder))
        elif os.path.isfile(entry_path) and entry.startswith("test_"):
            tests = 0
            with open(entry_path) as file:
                for line in file:
                    if re.match(r"^(async\s+)?def\s+test_\w+\(", line):
                        tests += 1
            test_folder.children.append(TestFile(entry_path, tests))
            max_tests_in_file = max(max_tests_in_file, tests)

    return max_tests_in_file


class BucketHolder:
    """Class to hold buckets."""

    def __init__(self, tests_per_bucket: int, bucket_count: int) -> None:
        """Initialize bucket holder."""
        self._tests_per_bucket = tests_per_bucket
        self._bucket_count = bucket_count
        self._current_bucket = []
        self._current_tests = 0
        self._buckets: list[list[str]] = [self._current_bucket]

    def split_tests(self, tests: TestFolder | TestFile) -> None:
        """Split tests into buckets."""
        if self._current_tests + tests.total_tests < self._tests_per_bucket:
            self._current_bucket.append(tests.path)
            self._current_tests += tests.total_tests
            return

        if isinstance(tests, TestFolder):
            for test in tests.children:
                self.split_tests(test)
            return

        # Create new bucket
        self._current_tests = 0

        # The last bucket is lightly bigger (max the maximum number of tests in a single file)
        if len(self._buckets) != self._bucket_count:
            self._current_bucket = []
            self._buckets.append(self._current_bucket)

        # Add test to new bucket
        self.split_tests(tests)

    def create_ouput_files(self) -> None:
        """Create output files."""
        with open("pytest_buckets.txt", "w") as file:
            for bucket in self._buckets:
                file.write(" ".join(bucket) + "\n")


def main() -> None:
    """Execute script."""
    parser = argparse.ArgumentParser(description="Bump version of Home Assistant")

    def check_greater_0(value: str) -> int:
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                f"{value} is an invalid. Must be greater than 0"
            )
        return ivalue

    parser.add_argument(
        "bucket_count",
        help="Number of buckets to split tests into",
        type=check_greater_0,
    )

    arguments = parser.parse_args()

    tests = TestFolder("tests")
    max_tests_in_file = count_tests(tests)
    print(f"Max tests in a single file: {max_tests_in_file}")

    tests_per_bucket = ceil(tests.total_tests / arguments.bucket_count)

    if max_tests_in_file > tests_per_bucket:
        raise ValueError(
            f"There are more tests in a single file ({max_tests_in_file}) than tests per bucket ({tests_per_bucket})"
        )

    bucket_holder = BucketHolder(tests_per_bucket, arguments.bucket_count)
    bucket_holder.split_tests(tests)
    bucket_holder.create_ouput_files()


if __name__ == "__main__":
    main()
