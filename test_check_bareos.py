#!/usr/bin/env python3

import unittest
import unittest.mock as mock
import os
import sys

sys.path.append('..')


from check_bareos import commandline
from check_bareos import createBackupKindString
from check_bareos import createFactor
from check_bareos import printNagiosOutput
from check_bareos import checkConnection
from check_bareos import connectDB
from check_bareos import Threshold
from check_bareos import check_threshold

from check_bareos import checkBackupSize
from check_bareos import checkEmptyBackups
from check_bareos import checkEmptyTapes
from check_bareos import checkExpiredTapes
from check_bareos import checkFailedBackups
from check_bareos import checkJobs
from check_bareos import checkOversizedBackups
from check_bareos import checkReplaceTapes
from check_bareos import checkRunTimeJobs
from check_bareos import checkSingleJob
from check_bareos import checkTapesInStorage
from check_bareos import checkTotalBackupSize
from check_bareos import checkWillExpiredTapes


class CLITesting(unittest.TestCase):

    def test_commandline(self):
        actual = commandline(['-H', 'localhost', '-U', 'bareos'])
        self.assertEqual(actual.host, 'localhost')
        self.assertEqual(actual.user, 'bareos')


    def test_commandline_fromenv(self):
        os.environ['CHECK_BAREOS_DATABASE_PASSWORD'] = 'secret'

        actual = commandline(['-H', 'localhost', '-U', 'bareos'])
        self.assertEqual(actual.user, 'bareos')
        self.assertEqual(actual.password, 'secret')

        os.unsetenv('CHECK_BAREOS_DATABASE_PASSWORD')

class ThresholdTesting(unittest.TestCase):

    def test_thresholds(self):
        self.assertEqual(check_threshold(0, Threshold("20"), Threshold("25")), 0)
        self.assertEqual(check_threshold(10, Threshold("20"), Threshold("25")), 0)
        self.assertEqual(check_threshold(24, Threshold("20"), Threshold("25")), 1)
        self.assertEqual(check_threshold(26, Threshold("20"), Threshold("25")), 2)

        self.assertEqual(check_threshold(15, Threshold("10:"), Threshold("5:")), 0)
        self.assertEqual(check_threshold(9, Threshold("10:"), Threshold("5:")), 1)
        self.assertEqual(check_threshold(2, Threshold("10:"), Threshold("5:")), 2)

        self.assertEqual(check_threshold(15, Threshold("10:20"), Threshold("50")), 0)
        self.assertEqual(check_threshold(5, Threshold("10:20"), Threshold("50")), 1)
        self.assertEqual(check_threshold(10, Threshold("@10:20"), Threshold("50")), 1)


class UtilTesting(unittest.TestCase):

    # TODO checkConnection(cursor)
    # TODO def checkTape(args)
    # TODO def checkJob(args)

    @mock.patch('check_bareos.psycopg2')
    def test_connectDB(self, mock_sql):
        con = mock.MagicMock()
        con.cursor.return_value = "cursor"
        mock_sql.connect.return_value = con
        actual = connectDB("user", "password", "localhost", "bareos", 5432)

        expected = "cursor"
        self.assertEqual(actual, expected)

    def test_createBackupKindString(self):
        actual = createBackupKindString(True, True, True)
        expected = "'F','I','D'"
        self.assertEqual(actual, expected)

    def test_createFactor(self):
        actual = createFactor('PB')
        expected = 1125899906842624
        self.assertEqual(actual, expected)

    @mock.patch('builtins.print')
    def test_printNagiosOutput(self, mock_print):
        with self.assertRaises(SystemExit) as sysexit:
            printNagiosOutput(None)
        self.assertEqual(sysexit.exception.code, 3)

        with self.assertRaises(SystemExit) as sysexit:
            actual = printNagiosOutput({'returnCode': 1, 'returnMessage': "bar", 'performanceData': 'foo'})
        self.assertEqual(sysexit.exception.code, 1)


class SQLTesting(unittest.TestCase):

    def test_checkEmptyTapes(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [2]
        actual = checkEmptyTapes(c, Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 2.0 Tapes are empty', 'performanceData': 'bareos.tape.empty=2.0;3;5;;'}
        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]
        actual = checkEmptyTapes(c, Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 10.0 Tapes are empty', 'performanceData': 'bareos.tape.empty=10.0;3;5;;'}
        self.assertEqual(actual, expected)

    def test_checkReplaceTapes(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [2]
        actual = checkReplaceTapes(c, "foo", Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 2.0 Tapes might need replacement', 'performanceData': 'bareos.tape.replace=2.0;3;5;;'}
        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]
        actual = checkReplaceTapes(c, "foo", Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 10.0 Tapes might need replacement', 'performanceData': 'bareos.tape.replace=10.0;3;5;;'}
        self.assertEqual(actual, expected)


    def test_checkWillExpiredTapes(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [2]
        actual = checkWillExpiredTapes(c, 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 2.0 Tapes will expire in 1 days', 'performanceData': 'bareos.tape.willexpire=2.0;3;5;;'}
        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]
        actual = checkWillExpiredTapes(c, 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 10.0 Tapes will expire in 1 days', 'performanceData': 'bareos.tape.willexpire=10.0;3;5;;'}
        self.assertEqual(actual, expected)

    def test_checkExpiredTapes(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [2]
        actual = checkExpiredTapes(c, Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 2.0 Tapes are expired', 'performanceData': 'bareos.tape.expired=2.0;3;5;;'}
        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]
        actual = checkExpiredTapes(c, Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 10.0 Tapes are expired', 'performanceData': 'bareos.tape.expired=10.0;3;5;;'}
        self.assertEqual(actual, expected)

    def test_checkTapesInStorage(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [2]
        actual = checkTapesInStorage(c, Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 2.0 Tapes are in the Storage', 'performanceData': 'bareos.tape.instorage=2.0;3;5;;'}
        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]
        actual = checkTapesInStorage(c, Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 10.0 Tapes are in the Storage', 'performanceData': 'bareos.tape.instorage=10.0;3;5;;'}
        self.assertEqual(actual, expected)


    def test_checkRunTimeJobs(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [2]
        actual = checkRunTimeJobs(c, "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 2.0 Jobs are running longer than 1 days', 'performanceData': 'bareos.job.count=2.0;3;5;;'}
        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]
        actual = checkRunTimeJobs(c, "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 10.0 Jobs are running longer than 1 days', 'performanceData': 'bareos.job.count=10.0;3;5;;'}
        self.assertEqual(actual, expected)


    def test_checkEmptyBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkEmptyBackups(c, 1, "'F','I','D'", Threshold(1), Threshold(2))
        expected = {'returnCode': 0, 'returnMessage': "[OK] - All 'F','I','D' Backups are fine", 'performanceData': 'bareos.backup.empty=0;1;2;;'}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime\n    FROM Job\n    WHERE Level in ('F','I','D') AND JobBytes=0 AND starttime > (now()::date-1 * '1 day'::INTERVAL) AND JobStatus in ('T');\n    ")

    def test_checkJobs(self):

        c = mock.MagicMock()

        c.fetchone.return_value = [0]

        actual = checkJobs(c, 'E', "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 0, 'returnMessage': "[OK] - 0.0 Jobs are in the state: Job terminated in error", 'performanceData': "'bareos.Job terminated in error'=0.0;3;5;;"}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT count(Job.Name)\n    FROM Job\n    WHERE Job.JobStatus like 'E' AND (starttime > (now()::date-1 * '1 day'::INTERVAL) OR starttime IS NULL) AND Job.Level in ('F','I','D');\n    ")

        c.fetchone.return_value = [4]

        actual = checkJobs(c, 'E', "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 1, 'returnMessage': "[WARNING] - 4.0 Jobs are in the state: Job terminated in error", 'performanceData': "'bareos.Job terminated in error'=4.0;3;5;;"}

        self.assertEqual(actual, expected)

        c.fetchone.return_value = [10]

        actual = checkJobs(c, 'E', "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'returnCode': 2, 'returnMessage': "[CRITICAL] - 10.0 Jobs are in the state: Job terminated in error", 'performanceData': "'bareos.Job terminated in error'=10.0;3;5;;"}

        self.assertEqual(actual, expected)

    def test_checkFailedBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkFailedBackups(c, 1, Threshold("1"), Threshold("2"))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 0 Backups failed/canceled in the last 1 days', 'performanceData': 'bareos.backup.failed=0;1;2;;'}
        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime, JobStatus\n    FROM Job\n    WHERE JobStatus in ('E','f') AND starttime > (now()::date-1 * '1 day'::INTERVAL);\n    ")

        c.fetchall.return_value = [1,2,3]

        actual = checkFailedBackups(c, 1, Threshold("1"), Threshold("2"))
        expected = {'performanceData': 'bareos.backup.failed=3;1;2;;', 'returnCode': 2, 'returnMessage': '[CRITICAL] - 3 Backups failed/canceled in the last 1 days'}
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

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", Threshold(100), Threshold(200))
        expected = {'performanceData': 'bareos.backup.size=300;100;200;;', 'returnCode': 2, 'returnMessage': "[CRITICAL] - 300 PB Kind:'F','I','D' Days: 1"}

        self.assertEqual(actual, expected)

        mock_size.return_value = 199

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", Threshold(100), Threshold(200))
        expected = {'performanceData': 'bareos.backup.size=199;100;200;;', 'returnCode': 1, 'returnMessage': "[WARNING] - 199 PB Kind:'F','I','D' Days: 1"}

        self.assertEqual(actual, expected)

        mock_size.return_value = 99

        actual = checkTotalBackupSize(c, 1, "'F','I','D'", "PB", Threshold(100), Threshold(200))
        expected = {'performanceData': 'bareos.backup.size=99;100;200;;', 'returnCode': 0, 'returnMessage': "[OK] - 99 PB Kind:'F','I','D' Days: 1"}

        self.assertEqual(actual, expected)


    def test_checkOversizedBackups(self):

        c = mock.MagicMock()
        c.fetchall.return_value = []

        actual = checkOversizedBackups(c, 1, 100, "'F','I','D'", "PB", Threshold(1), Threshold(2))
        expected = {'returnCode': 0, 'returnMessage': "[OK] - 0 'F','I','D' Backups larger than 100 PB in the last 1 days", 'performanceData': 'bareos.backup.oversized=0;1;2;;'}

        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Level,starttime, JobBytes/1125899906842624.0\n    FROM Job\n    WHERE Level in ('F','I','D') AND starttime > (now()::date-1 * '1 day'::INTERVAL) AND JobBytes/1125899906842624.0>100;\n    ")

        c.fetchall.return_value = [1,2,3]
        actual = checkOversizedBackups(c, 1, 100, "'F','I','D'", "PB", Threshold(1), Threshold(2))
        expected = {'performanceData': 'bareos.backup.oversized=3;1;2;;', 'returnCode': 2, 'returnMessage': "[CRITICAL] - 3 'F','I','D' Backups larger than 100 PB in the last 1 days"}
        self.assertEqual(actual, expected)


    def test_checkSingleJob(self):

        c = mock.MagicMock()

        # Nothing returned from DB
        c.fetchall.return_value = []
        actual = checkSingleJob(c, "Jobby", "E", "'F','I','D'", 1, Threshold(1), Threshold(2))
        expected = {'performanceData': "'bareos.Job terminated in error'=0;1;2;;", 'returnCode': 0, 'returnMessage': '[OK] - 0 Jobs are in the state: Job terminated in error'}
        self.assertEqual(actual, expected)

        c.execute.assert_called_with("\n    SELECT Job.Name,Job.JobStatus, Job.Starttime\n    FROM Job\n    WHERE Job.Name like '%Jobby%' AND Job.JobStatus like 'E' AND (starttime > (now()::date-1 * '1 day'::INTERVAL) OR starttime IS NULL) AND Job.Level in ('F','I','D');\n    ")

        # Missing Name
        actual = checkSingleJob(c, None, "T", "'F','I','D'", 1, Threshold(1), Threshold(2))
        expected = {'returnCode': 3, 'returnMessage': '[UNKNOWN] - Job Name missing'}
        self.assertEqual(actual, expected)

        # Returns Warning
        c.fetchall.return_value = [1,2,3,4]
        actual = checkSingleJob(c, "Jobby", "E", "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'performanceData': "'bareos.Job terminated in error'=4;3;5;;", 'returnCode': 1, 'returnMessage': '[WARNING] - 4 Jobs are in the state: Job terminated in error'}
        self.assertEqual(actual, expected)

        # Returns Critical
        c.fetchall.return_value = [1,2,3,4,5,6]
        actual = checkSingleJob(c, "Jobby", "E", "'F','I','D'", 1, Threshold(3), Threshold(5))
        expected = {'performanceData': "'bareos.Job terminated in error'=6;3;5;;", 'returnCode': 2, 'returnMessage': '[CRITICAL] - 6 Jobs are in the state: Job terminated in error'}
        self.assertEqual(actual, expected)

    def test_checkSingleJob_WithThreshold(self):

        c = mock.MagicMock()

        # With Threshold, more than 5 T jobs are OK
        c.fetchall.return_value = [1,2,3,4,5,6]
        actual = checkSingleJob(c, "Jobby", "T", "'F','I','D'", 1, Threshold("5:"), Threshold("3:"))
        expected = {'returnCode': 0, 'returnMessage': '[OK] - 6 Jobs are in the state: Job terminated normally', 'performanceData': "'bareos.Job terminated normally'=6;5:;3:;;"}
        self.assertEqual(actual, expected)

        # With Threshold, less than 5 T jobs are warning
        c.fetchall.return_value = [1,2,3]
        actual = checkSingleJob(c, "Jobby", "T", "'F','I','D'", 1, Threshold("5:"), Threshold("3:"))
        expected = {'returnCode': 1, 'returnMessage': '[WARNING] - 3 Jobs are in the state: Job terminated normally', 'performanceData': "'bareos.Job terminated normally'=3;5:;3:;;"}
        self.assertEqual(actual, expected)

        # With Threshold, less than 3 T jobs are critical
        c.fetchall.return_value = [1,2]
        actual = checkSingleJob(c, "Jobby", "T", "'F','I','D'", 1, Threshold("5:"), Threshold("3:"))
        expected = {'returnCode': 2, 'returnMessage': '[CRITICAL] - 2 Jobs are in the state: Job terminated normally', 'performanceData': "'bareos.Job terminated normally'=2;5:;3:;;"}
        self.assertEqual(actual, expected)
