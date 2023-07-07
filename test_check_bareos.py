#!/usr/bin/env python3

import unittest
import unittest.mock as mock
import sys

sys.path.append('..')


from check_bareos import commandline
from check_bareos import createBackupKindString
from check_bareos import createFactor

from check_bareos import checkFailedBackups
from check_bareos import checkBackupSize
from check_bareos import checkTotalBackupSize
from check_bareos import checkOversizedBackups
from check_bareos import checkSingleJob
from check_bareos import checkJobs
from check_bareos import checkEmptyBackups


class CLITesting(unittest.TestCase):

    def test_commandline(self):
        actual = commandline(['-H', 'localhost', '-U', 'bareos'])
        self.assertEqual(actual.host, 'localhost')
        self.assertEqual(actual.user, 'bareos')


class UtilTesting(unittest.TestCase):

    def test_createBackupKindString(self):
        actual = createBackupKindString(True, True, True)
        expected = "'F','I','D'"
        self.assertEqual(actual, expected)

    def test_createFactor(self):
        actual = createFactor('PB')
        expected = 1125899906842624
        self.assertEqual(actual, expected)


class SQLTesting(unittest.TestCase):

    def test_checkEmptyBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkEmptyBackups(c, 1, "'F','I','D'", 1, 2)
        expected = {'returnCode': 0, 'returnMessage': "[OK] - All 'F','I','D' Backups are fine", 'performanceData': 'EmptyBackups=0;1;2;;'}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime\n    FROM Job\n    WHERE Level in ('F','I','D') AND JobBytes=0 AND starttime > (now()::date-1 * '1 day'::INTERVAL) AND JobStatus in ('T');\n    ")

    def test_checkJobs(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [0]

        actual = checkJobs(c, 'E', "'F','I','D'", 1, 3, 5)
        expected = {'returnCode': 0, 'returnMessage': "[OK] - 0.0 Jobs are in the state: Job terminated in error", 'performanceData': 'Job terminated in error=0.0;3;5;;'}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT count(Job.Name)\n    FROM Job\n    WHERE Job.JobStatus like 'E' AND (starttime > (now()::date-1 * '1 day'::INTERVAL) OR starttime IS NULL) AND Job.Level in ('F','I','D');\n    ")

        c.fetchone.return_value = [3]

        actual = checkJobs(c, 'E', "'F','I','D'", 1, 3, 5)
        expected = {'returnCode': 1, 'returnMessage': "[WARNING] - 3.0 Jobs are in the state: Job terminated in error", 'performanceData': 'Job terminated in error=3.0;3;5;;'}

        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]

        actual = checkJobs(c, 'E', "'F','I','D'", 1, 3, 5)
        expected = {'returnCode': 2, 'returnMessage': "[CRITICAL] - 10.0 Jobs are in the state: Job terminated in error", 'performanceData': 'Job terminated in error=10.0;3;5;;'}

        self.assertEqual(actual, expected)

    def test_checkFailedBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkFailedBackups(c, 1, 1, 2)
        expected = {'returnCode': 0, 'returnMessage': '[OK] - Only 0 Backups failed in the last 1 days', 'performanceData': 'Failed=0;1;2;;'}
        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime, JobStatus\n    FROM Job\n    WHERE JobStatus in ('E','f') AND starttime > (now()::date-1 * '1 day'::INTERVAL);\n    ")

        c.fetchall.return_value = [1,2,3]
        actual = checkFailedBackups(c, 1, 1, 2)
        expected = {'performanceData': 'Failed=3;1;2;;', 'returnCode': 2, 'returnMessage': '[CRITICAL] - 3 Backups failed/canceled last 1 days'}
        self.assertEqual(actual, expected)

    def test_checkBackupSize(self):

        c = mock.MagicMock()
        c.fetchone.return_value = [1337]

        actual = checkBackupSize(c, 1, "'F','I','D'", 1234)
        expected = 1337

        self.assertEqual(actual, expected)

    @mock.patch('check_bareos.checkBackupSize')
    def test_checkTotalBackupSize(self, mock_size):

        c = mock.MagicMock()

        mock_size.return_value = 300

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", 100, 200)
        expected = {'performanceData': 'Size=300;100;200;;', 'returnCode': 2, 'returnMessage': "[CRITICAL] - 300 PB Kind:'F','I','D' Days: 1"}

        self.assertEqual(actual, expected)

        mock_size.return_value = 199

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", 100, 200)
        expected = {'performanceData': 'Size=199;100;200;;', 'returnCode': 1, 'returnMessage': "[WARNING] - 199 PB Kind:'F','I','D' Days: 1"}

        self.assertEqual(actual, expected)

        mock_size.return_value = 99

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", 100, 200)
        expected = {'performanceData': 'Size=99;100;200;;', 'returnCode': 0, 'returnMessage': "[OK] - 99 PB Kind:'F','I','D' Days: 1"}

        self.assertEqual(actual, expected)


    def test_checkOversizedBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkOversizedBackups(c, 1, 100, "'F','I','D'", "PB", 1, 2)
        expected = {'returnCode': 0, 'returnMessage': "[OK] - No 'F','I','D' Backup larger than 100 PB in the last 1 days", 'performanceData': 'OverSized=0;1;2;;'}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime, JobBytes/1125899906842624.0\n    FROM Job\n    WHERE Level in ('F','I','D') AND starttime > (now()::date-1 * '1 day'::INTERVAL) AND JobBytes/1125899906842624.0>100;\n    ")

        c.fetchall.return_value = [1,2,3]
        actual = checkOversizedBackups(c, 1, 100, "'F','I','D'", "PB", 1, 2)
        expected = {'performanceData': 'OverSized=3;1;2;;', 'returnCode': 2, 'returnMessage': "[CRITICAL] - 3 'F','I','D' Backups larger than 100 PB in the last 1 days"}
        self.assertEqual(actual, expected)


    def test_checkSingleJob(self):

        c = mock.MagicMock()

        # Nothing returned from DB
        c.fetchall.return_value = []
        actual = checkSingleJob(c, "Jobby", "E", "'F','I','D'", 1, 1, 2)
        expected = {'performanceData': 'Job terminated in error=0;1;2;;', 'returnCode': 0, 'returnMessage': '[OK] - 0 Jobs are in the state: Job terminated in error'}
        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Job.JobStatus, Job.Starttime\n    FROM Job\n    WHERE Job.Name like '%Jobby%' AND Job.JobStatus like 'E' AND (starttime > (now()::date-1 * '1 day'::INTERVAL) OR starttime IS NULL) AND Job.Level in ('F','I','D');\n    ")

        # Missing Name
        actual = checkSingleJob(c, None, "T", "'F','I','D'", 1, 1, 2)
        expected = {'returnCode': 3, 'returnMessage': 'UNKNOWN - Job Name missing'}
        self.assertEqual(actual, expected)

        # Returns Warning
        c.fetchall.return_value = [1,2,3]
        actual = checkSingleJob(c, "Jobby", "E", "'F','I','D'", 1, 3, 5)
        expected = {'performanceData': 'Job terminated in error=3;3;5;;', 'returnCode': 1, 'returnMessage': '[WARNING] - 3 Jobs are in the state: Job terminated in error'}
        self.assertEqual(actual, expected)

        # Returns Critical
        c.fetchall.return_value = [1,2,3,4,5]
        actual = checkSingleJob(c, "Jobby", "E", "'F','I','D'", 1, 3, 5)
        expected = {'performanceData': 'Job terminated in error=5;3;5;;', 'returnCode': 2, 'returnMessage': '[CRITICAL] - 5 Jobs are in the state: Job terminated in error'}
        self.assertEqual(actual, expected)
