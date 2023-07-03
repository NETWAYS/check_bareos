#!/usr/bin/env python3

import unittest
import unittest.mock as mock
import sys

sys.path.append('..')


from check_bareos import commandline
from check_bareos import createBackupKindString
from check_bareos import createFactor
from check_bareos import getState

from check_bareos import checkFailedBackups
from check_bareos import checkBackupSize
from check_bareos import checkTotalBackupSize
from check_bareos import checkOversizedBackups
from check_bareos import checkSingleJob


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

    def test_getState(self):
        actual = getState('T')
        expected = "Completed successfully"
        self.assertEqual(actual, expected)

class SQLTesting(unittest.TestCase):

    def test_checkFailedBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkFailedBackups(c, 1, 1, 2)
        expected = {'returnCode': 0, 'returnMessage': 'OK - Only 0 Backups failed in the last 1 days', 'performanceData': 'Failed=0;1;2;;'}
        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime, JobStatus\n    FROM Job\n    WHERE JobStatus in ('E','f') AND starttime > (now()::date-1 * '1 day'::INTERVAL);\n    ")

        c.fetchall.return_value = [1,2,3]
        actual = checkFailedBackups(c, 1, 1, 2)
        expected = {'performanceData': 'Failed=3;1;2;;', 'returnCode': 2, 'returnMessage': 'CRITICAL - 3 Backups failed/canceled last 1 days'}
        self.assertEqual(actual, expected)

    def test_checkBackupSize(self):

        c = mock.MagicMock()
        c.fetchone.return_value = [1337]

        actual = checkBackupSize(c, 1, "'F','I','D'", 1234)
        expected = 1337

        self.assertEqual(actual, expected)

    @mock.patch('check_bareos.checkBackupSize')
    def test_checkTotalBackupSize(self, mock_size):

        mock_size.return_value = 1337
        c = mock.MagicMock()

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", 1, 2)
        expected = 1337


    def test_checkOversizedBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkOversizedBackups(c, 1, 100, "'F','I','D'", "PB", 1, 2)
        expected = {'returnCode': 0, 'returnMessage': "OK - No 'F','I','D' Backup larger than 100 PB in the last 1 days", 'performanceData': 'OverSized=0;1;2;;'}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime, JobBytes/1125899906842624.0\n    FROM Job\n    WHERE Level in ('F','I','D') AND starttime > (now()::date-1 * '1 day'::INTERVAL) AND JobBytes/1125899906842624.0>100;\n    ")

        c.fetchall.return_value = [1,2,3]
        actual = checkOversizedBackups(c, 1, 100, "'F','I','D'", "PB", 1, 2)
        expected = {'performanceData': 'OverSized=3;1;2;;', 'returnCode': 2, 'returnMessage': "CRITICAL - 3 'F','I','D' Backups larger than 100 PB in the last 1 days"}
        self.assertEqual(actual, expected)


    def test_checkSingleJob(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkSingleJob(c, "Jobby", "T", "'F','I','D'", 1, 1, 2)

        expected = {'performanceData': 'Completed successfully=0;1;2;;', 'returnCode': 0, 'returnMessage': 'OK - 0 Jobs are in the state: Completed successfully'}


        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Job.JobStatus, Job.Starttime\n    FROM Job\n    WHERE Job.Name like '%Jobby%' AND Job.JobStatus like 'T' AND (starttime > (now()::date-1 * '1 day'::INTERVAL) OR starttime IS NULL) AND Job.Level in ('F','I','D');\n    ")

        actual = checkSingleJob(c, None, "T", "'F','I','D'", 1, 1, 2)
        expected = {'returnCode': 3, 'returnMessage': 'UNKNOWN - Job Name missing'}
        self.assertEqual(actual, expected)
