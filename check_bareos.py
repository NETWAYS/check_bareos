#!/usr/bin/python3

# ---------------------------------------------------- #
# File : check_bareos
# Author : Philipp Posovszky, DLR
# E-Mail: Philipp.Posovszky@dlr.de
# Date : 22/04/2015
#
# Modifications : Thomas Widhalm, NETways GmbH
# E-Mail: widhalmt@widhalm.or.at
#
# Version: 1.0.3
#
# This program is free software; you can redistribute it or modify
# it under the terms of the GNU General Public License version 3.0
#
# Changelog:
# 	- 1.0.1 remove 'error' tapes from expire check and correct the help description
#	- 1.0.2 start to rework for chosing correct query for the database type (MySQL -vs - PostgreSQL)
#	- 1.0.3 add port parameter for MySQL and PostgreSQL databases
#
#
# Plugin check for icinga
# ---------------------------------------------------- #
import argparse
import psycopg2
import psycopg2.extras
import sys
import subprocess
import MySQLdb

# Variables
databaseName = 'bareos'
# Used to differentiate between database specific queries
databaseType = 'mysql'

def createBackupKindString(full, inc, diff):
    if full == False and inc == False and diff == False:
        return "'F','D','I'"
    kind = []
    if full:
        kind.append("'F'")
    if inc:
        kind.append("'I'")
    if diff:
        kind.append("'D'")

    return ",".join(kind)

def createFactor(unit):
    options = {'EB' : 2 ** 60,
               'PB' : 2 ** 50,
               'TB': 2 ** 40,
               'GB': 2 ** 30,
               'MB': 10 ** 20}
    return options[unit]

def getState(state):
    options = {'T' : "Completed successfully",
               'C' : "Created,not yet running",
               'R': "Running",
               'E': "Terminated with Errors",
               'f': "Fatal error",
               'A': "Canceled by user"}
    return options[state]

def checkFailedBackups(courser, time, warning, critical):
    checkState = {}
    if time == None:
        time = 7
    # MySQL needs other Queries than PostgreSQL
    if(databaseType == "psql"):
        query = """
        SELECT Job.Name,Level,starttime, JobStatus
        FROM Job
        Where JobStatus in ('E','f') and starttime > (now()::date-""" + str(time) + """ * '1 day'::INTERVAL);
        """
    # According to --help output, MySQL is the default
    else:
        query = """
        SELECT Job.Name,Level,starttime, JobStatus
        FROM Job
        Where JobStatus in ('E','f') and starttime > DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY);
        """
    courser.execute(query)
    results = courser.fetchall()  # Returns a value
    result = len(results)

    if result >= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - " + str(result) + " Backups failed/canceled last " + str(time) + " days"
    elif result >= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - " + str(result) + " Backups failed/canceled last " + str(time) + " days"
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - Only " + str(result) + " Backups failed in the last " + str(time) + " days"
    checkState["performanceData"] = "Failed=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState


    return checkState

def checkBackupSize(courser, time, kind, factor):
            if time != None:
                # MySQL needs other Queries than PostgreSQL
                if(databaseType == "psql"):
                    query = """
                    SELECT ROUND(SUM(JobBytes/""" + str(float(factor)) + """),3)
                    FROM Job
                    Where Level in (""" + kind + """) and starttime > (now()-""" + str(time) + """ * '1 day'::INTERVAL) ;
                    """
                # According to --help output MySQL is the default
                else:
                    query = """
                    SELECT ROUND(SUM(JobBytes/""" + str(float(factor)) + """),3)
                    FROM Job
                    Where Level in (""" + kind + """) and starttime > DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY);
                    """
                courser.execute(query)
                results = courser.fetchone()  # Returns a value
                return results[0]
            else:
                query = """
                SELECT ROUND(SUM(JobBytes/""" + str(float(factor)) + """),3)
                FROM Job
                Where Level in (""" + kind + """);
                """
                courser.execute(query)
                results = courser.fetchone()  # Returns a value
                return results[0]

def checkTotalBackupSize(cursor, time, kind, unit, warning, critical):
            checkState = {}
            result = checkBackupSize(cursor, time, kind, createFactor(unit))
            if result >= int(critical):
                    checkState["returnCode"] = 2
                    if args.time:
                        checkState["returnMessage"] = "CRITICAL - " + str(result) + " " + unit + " Kind:" + kind + " Days: " + str(time)
                    else:
                        checkState["returnMessage"] = "CRITICAL - " + str(result) + " " + unit + " Kind:" + kind
            elif result >= int(warning):
                    checkState["returnCode"] = 1
                    if args.time:
                        checkState["returnMessage"] = "WARNING - " + str(result) + " " + unit + " Kind:" + kind + " Days: " + str(time)
                    else:
                        checkState["returnMessage"] = "WARNING - " + str(result) + " " + unit + " Kind:" + kind
            else:
                    checkState["returnCode"] = 0
                    if args.time:
                        checkState["returnMessage"] = "OK - " + str(result) + " " + unit + " Kind:" + kind + " Days: " + str(time)
                    else:
                        checkState["returnMessage"] = "OK - " + str(result) + " " + unit + " Kind:" + kind
            checkState["performanceData"] = "Size=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"
            return checkState

def checkOversizedBackups(courser, time, size, kind, unit, warning, critical):
            checkState = {}
            if time == None:
                time = 7
            factor = createFactor(unit)
            # MySQL needs other Queries than PostgreSQL
            if(databaseType == "psql"):
                query = """
                SELECT Job.Name,Level,starttime, JobBytes/""" + str(float(factor)) + """
                FROM Job
                Where Level in (""" + kind + """) and starttime > (now()::date-""" + str(time) + """ * '1 day'::INTERVAL) and JobBytes/""" + str(float(factor)) + """>""" + str(size) + """;
                """
            # MySQL is the default
            else:
                query = """
                SELECT Job.Name,Level,starttime, JobBytes/""" + str(float(factor)) + """
                FROM Job
                Where Level in (""" + kind + """) and starttime > DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY) and JobBytes/""" + str(float(factor)) + """>""" + str(size) + """;
                """
            courser.execute(query)
            results = courser.fetchall()  # Returns a value
            result = len(results)

            if result >= int(critical):
                    checkState["returnCode"] = 2
                    checkState["returnMessage"] = "CRITICAL - " + str(result) + " " + kind + " Backups larger than " + str(size) + " " + unit + " in the last " + str(time) + " days"
            elif result >= int(warning):
                    checkState["returnCode"] = 1
                    checkState["returnMessage"] = "WARNING - " + str(result) + " " + kind + " Backups larger than " + str(size) + " " + unit + " in the last " + str(time) + " days"
            else:
                    checkState["returnCode"] = 0
                    checkState["returnMessage"] = "OK - No " + kind + " Backup larger than " + str(size) + " " + unit + " in the last " + str(time) + " days"
            checkState["performanceData"] = "OverSized=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"
            return checkState

def checkEmptyBackups(cursor, time, kind, warning, critical):
            checkState = {}
            if time == None:
                time = 7
            # MySQL needs other Queries than PostgreSQL
            if(databaseType == "psql"):
                query = """
                SELECT Job.Name,Level,starttime
                FROM Job
                Where Level in (""" + str(kind) + """) and JobBytes=0 and starttime > (now()::date-""" + str(time) + """ * '1 day'::INTERVAL) and JobStatus in ('T');
                """
            # MySQL is the default
            else:
                query = """
                SELECT Job.Name,Level,starttime
                FROM Job
                Where Level in (""" + str(kind) + """) and JobBytes=0 and starttime > DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY) and JobStatus in ('T');
                """
            cursor.execute(query)
            results = cursor.fetchall()  # Returns a value
            result = len(results)

            if result >= int(critical):
                    checkState["returnCode"] = 2
                    checkState["returnMessage"] = "CRITICAL - " + str(result) + " successful " + str(kind) + " backups are empty"
            elif result >= int(warning):
                    checkState["returnCode"] = 1
                    checkState["returnMessage"] = "WARNING - " + str(result) + " successful " + str(kind) + " backups are empty!"
            else:
                    checkState["returnCode"] = 0
                    checkState["returnMessage"] = "OK - All " + str(kind) + " backups are fine"
            checkState["performanceData"] = "EmptyBackups=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"
            return checkState


# Checks on Jobs
def checkJobs(cursor, state, kind, time, warning, critical):
    checkState = {}
    if time == None:
        time = 7
    # MySQL needs other Queries than PostgreSQL
    if(databaseType == "psql"):
        query = """
        Select count(Job.Name)
        From Job
        Where Job.JobStatus like '"""+str(state)+"""' and (starttime > (now()::date-"""+str(time)+""" * '1 day'::INTERVAL) or starttime IS NULL) and Job.Level in ("""+kind+""");
        """
    # MySQL is the default
    else:
        query = """
        Select count(Job.Name)
        From Job
        Where Job.JobStatus like '"""+str(state)+"""' and (starttime > DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY) or starttime IS NULL) and Job.Level in ("""+kind+""");
        """
    cursor.execute(query)
    results = cursor.fetchone()  # Returns a value
    result = float(results[0])

    if result >= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - " + str(result) + " Jobs are in the state: "+str(getState(state))
    elif result >= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - " + str(result) + " Jobs are in the state: "+str(getState(state))
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - " + str(result) + " Jobs are in the state: "+str(getState(state))
    checkState["performanceData"] = str(getState(state))+"=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState

def checkSingleJob(cursor, name, state, kind, time, warning, critical):
    checkState = {}
    if time == None:
        time = 7
    # MySQL needs other Queries than PostgreSQL
    if(databaseType == "psql"):
        query = """
        Select Job.Name,Job.JobStatus, Job.Starttime
        FROm Job
        Where Job.Name like '%"""+name+"""%' and Job.JobStatus like '"""+state+"""' and (starttime > (now()::date-"""+str(time)+""" * '1 day'::INTERVAL) or starttime IS NULL) and Job.Level in ("""+kind+""");
        """
    # MySQL is the default
    else:
        query = """
        Select Job.Name,Job.JobStatus, Job.Starttime
        FROm Job
        Where Job.Name like '%"""+name+"""%' and Job.JobStatus like '"""+state+"""' and (starttime > DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY) or starttime IS NULL) and Job.Level in ("""+kind+""");
        """
    cursor.execute(query)
    results = cursor.fetchall()  # Returns a value
    result = len(results)

    if result >= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - " + str(result) + " Jobs are in the state: "+str(getState(state))
    elif result >= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - " + str(result) + " Jobs are in the state: "+str(getState(state))
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - " + str(result) + " Jobs are in the state: "+str(getState(state))
    checkState["performanceData"] = str(getState(state))+"=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState

def checkRunTimeJobs(cursor,name,state,time,warning,critical):
    checkState = {}
    if time == None:
        time = 7
    # MySQL needs other Queries than PostgreSQL
    if(databaseType == "psql"):
        query = """
        Select Count(Job.Name)
        FROm Job
        Where starttime < (now()::date-"""+str(time)+""" * '1 day'::INTERVAL) and Job.JobStatus like '"""+state+"""';
        """
    # MySQL is the default
    else:
        query = """
        Select Count(Job.Name)
        FROm Job
        Where starttime < DATE_SUB(now(), INTERVAL """ + str(time) + """ DAY) and Job.JobStatus like '"""+state+"""';
        """
    cursor.execute(query)
    results = cursor.fetchone()  # Returns a value
    result = float(results[0])

    if result >= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - " + str(result) + " Jobs are running longer than "+str(time)+" days"
    elif result >= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - " + str(result) + " Jobs are running longer than "+str(time)+" days"
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - " + str(result) + " Jobs are running longer than "+str(time)+" days"
    checkState["performanceData"] = "Count=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState


# Checks on Tapes
def checkTapesInStorage(cursor, warning, critical):
    checkState = {}

    query = """
    SELECT count(MediaId)
    FROM Media,Pool,Storage
    WHERE Media.PoolId=Pool.PoolId
    AND Slot>0 AND InChanger=1
    AND Media.StorageId=Storage.StorageId;
    """
    cursor.execute(query)
    results = cursor.fetchone()  # Returns a value
    result = float(results[0])

    if result <= int(critical):
        checkState["returnCode"] = 2
        checkState["returnMessage"] = "CRITICAL - Only " + str(result) + " Tapes are in the Storage"
    elif result <= int(warning):
        checkState["returnCode"] = 1
        checkState["returnMessage"] = "WARNING - Only" + str(result) + " Tapes are in the Storage"
    else:
        checkState["returnCode"] = 0
        checkState["returnMessage"] = "OK - " + str(result) + " Tapes are in the Storage"
    checkState["performanceData"] = "Tapes=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"
    return checkState

def checkExpiredTapes(cursor, warning, critical):
    checkState = {}
    query = """
    SELECT Count(MediaId)
    FROM Media
    WHERE lastwritten+(media.volretention * '1 second'::INTERVAL)<now() and volstatus not like 'Error';
    """
    cursor.execute(query)
    results = cursor.fetchone()  # Returns a value
    result = float(results[0])

    if result <= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - Only " + str(result) + " expired"
    elif result <= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - Only " + str(result) + " expired"
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - Tapes " + str(result) + " expired"
    checkState["performanceData"] = "Expired=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState


def checkWillExpiredTapes(cursor, time, warning, critical):
    checkState = {}
    query = """
    SELECT Count(MediaId)
    FROM Media
    WHERE lastwritten+(media.volretention * '1 second'::INTERVAL)<now()+(""" + str(time) + """ * '1 day'::INTERVAL) and lastwritten+(media.volretention * '1 second'::INTERVAL)>now() and volstatus not like 'Error';;
    """
    cursor.execute(query)
    results = cursor.fetchone()  # Returns a value
    result = float(results[0])

    if result <= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - Only " + str(result) + " will expire in next " + str(time) + " days"
    elif result <= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - Only " + str(result) + " will expire in next " + str(time) + " days"
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - Tapes " + str(result) + " will expire in next " + str(time) + " days"
    checkState["performanceData"] = "Expire=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState

def checkReplaceTapes(cursor, mounts, warning, critical):
    checkState = {}
    query = """
    SELECT COUNT(VolumeName)
    FROM Media
    WHERE (VolErrors>0) OR (VolStatus='Error') OR (VolMounts>""" + str(mounts) + """) OR
    (VolStatus='Disabled');
    """
    cursor.execute(query)
    results = cursor.fetchone()  # Returns a value
    result = float(results[0])

    if result >= int(critical):
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - " + str(result) + " Tapes have to be replaced in the near future"
    elif result >= int(warning):
            checkState["returnCode"] = 1
            checkState["returnMessage"] = "WARNING - Only " + str(result) + " Tapes have to be replaced in the near future"
    else:
            checkState["returnCode"] = 0
            checkState["returnMessage"] = "OK - Tapes " + str(result) + " have to be replaced in the near future"
    checkState["performanceData"] = "Replace=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

    return checkState




def checkEmptyTapes(courser, warning, critical):
        checkState = {}
        query = """
         SELECT Count(MediaId)
          FROM Media,Pool,Storage
          WHERE Media.PoolId=Pool.PoolId
          AND Slot>0 AND InChanger=1
          AND Media.StorageId=Storage.StorageId
          AND (VolStatus like 'Purged' or VolStatus like 'Recycle' or lastwritten+(media.volretention * '1 second'::INTERVAL)<now() and VolStatus not like 'Error');
        """
        courser.execute(query)
        results = courser.fetchone()  # Returns a value
        result = float(results[0])

        if result <= int(critical):
                checkState["returnCode"] = 2
                checkState["returnMessage"] = "CRITICAL - Only " + str(result) + " Tapes are empty in the Storage"
        elif result <= int(warning):
                checkState["returnCode"] = 1
                checkState["returnMessage"] = "WARNING - Only " + str(result) + " Tapes are empty in the Storage"
        else:
                checkState["returnCode"] = 0
                checkState["returnMessage"] = "OK - " + str(result) + " Tapes are empty in the Storage"
        checkState["performanceData"] = "Empty=" + str(result) + ";" + str(warning) + ";" + str(critical) + ";;"

        return checkState



def connectDB(userName, pw, hostName, database, port):
    if(database == "postgresql" or database == "p" or database == "psql"):
        global databaseType
        databaseType = 'psql'
        try:
            # Define our connection string
            connString = "host='" + hostName + "' port=" + str(port) + " dbname='" + databaseName + "' user='" + userName + "' password='" + pw + "'"
            # get a connection, if a connect cannot be made an exception will be raised here
            conn = psycopg2.connect(connString)
            # conn.cursor will return a cursor object, you can use this cursor to perform queries
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            return cursor
        except psycopg2.DatabaseError as e:
            checkState = {}
            checkState["returnCode"] = 2
            checkState["returnMessage"] = "CRITICAL - " + str(e)[:-1]
            checkState["performanceData"] = ";;;;"
            printNagiosOutput(checkState)

    if(database == "mysql" or database == "m"):
        try:
            conn = MySQLdb.connect(host=hostName, user=userName, passwd=pw, db=databaseName, port=port)
        except MySQLdb.Error as e:
                        checkState = {}
                        checkState["returnCode"] = 2
                        checkState["returnMessage"] = "CRITICAL - " + str(e)[:-1]
                        checkState["performanceData"] = ";;;;"
                        printNagiosOutput(checkState)

def printNagiosOutput(checkResult):
    if checkResult != None:
        print((checkResult["returnMessage"] + "|" + checkResult["performanceData"]))
        sys.exit(checkResult["returnCode"])
    else:
        print("Critical - Error in Script")
        sys.exit(2)

def argumentParser():
    parser = argparse.ArgumentParser(description='Check status of the bareos backups')
    group = parser.add_argument_group();
    group.add_argument('-u', '--user', dest='user', action='store', required=True, help='user name for the database connections')
    group.add_argument('-p', '--password', dest='password', action='store', help='password for the database connections', default="")
    group.add_argument('-H', '--Host', dest='host', action='store', help='database host', default="127.0.0.1")
    group.add_argument('-P', '--port', dest='port', action='store', help='database port', default=3306, type=int)
    group.add_argument('-v', '--version', action='version', version='%(prog)s 1.0.0')
    parser.add_argument('-d', '--database', dest='database', choices=['mysql', 'm', 'postgresql', 'p', 'psql'], default='mysql', help='the database kind for the database connection (m=mysql, p=psql) (Default=Mysql)')

    subParser = parser.add_subparsers()

    jobParser = subParser.add_parser('job', help='Specific checks on a job');
    jobGroup = jobParser.add_mutually_exclusive_group(required=True)
    jobParser.set_defaults(func=checkJob)
    jobGroup.add_argument('-js', '--checkJobs', dest='checkJobs', action='store_true', help='Check how many jobs are in a specific state [default=queued]')
    jobGroup.add_argument('-j', '--checkJob', dest='checkJob', action='store_true', help='Check the state of a specific job [default=queued]')
    jobGroup.add_argument('-rt', '--runTimeJobs', dest='runTimeJobs', action='store_true', help='Check if a backup runs longer then n day')
    jobParser.add_argument('-n', '--name', dest='name', action='store', help='Name of the job')
    jobParser.add_argument('-t', '--time', dest='time', action='store', help='Time in days (default=7 days)')
    jobParser.add_argument('-u', '--unit', dest='unit', choices=['GB', 'TB', 'PB'], default='TB', help='display unit')
    jobParser.add_argument('-w', '--warning', dest='warning', action='store', help='Warning value', default=5)
    jobParser.add_argument('-c', '--critical', dest='critical', action='store', help='Critical value', default=10)
    jobParser.add_argument('-st', '--state', dest='state', choices=['T', 'C', 'R', 'E', 'f','A'], default='C', help='T=Completed, C=Queued, R=Running, E=Terminated with Errors, f=Fatal error, A=Canceld by user [default=C]')
    jobParser.add_argument('-f', '--full', dest='full', action='store_true', help='Backup kind full')
    jobParser.add_argument('-i', '--inc', dest='inc', action='store_true', help='Backup kind inc')
    jobParser.add_argument('-d', '--diff', dest='diff', action='store_true', help='Backup kind diff')

    tapeParser = subParser.add_parser('tape', help='Specific checks on a tapes');
    tapeGroup = tapeParser.add_mutually_exclusive_group(required=True);
    tapeParser.set_defaults(func=checkTape)
    tapeGroup.add_argument('-e', '--emptyTapes', dest='emptyTapes', action='store_true', help='Count empty tapes in the storage (Status Purged/Expired)')
    tapeGroup.add_argument('-ts', '--tapesInStorage', dest='tapesInStorage', action='store_true', help='Count how much tapes are in the storage')
    tapeGroup.add_argument('-ex', '--expiredTapes', dest='expiredTapes', action='store_true', help='Count how much tapes are expired')
    tapeGroup.add_argument('-wex', '--willExpire', dest='willExpire', action='store_true', help='Count how much tapes are will expire in n day')
    tapeGroup.add_argument('-r', '--replaceTapes', dest='replaceTapes', action='store_true', help='Count how much tapes should by replaced')
    tapeParser.add_argument('-w', '--warning', dest='warning', action='store', help='Warning value', default=5)
    tapeParser.add_argument('-c', '--critical', dest='critical', action='store', help='Critical value', default=10)
    tapeParser.add_argument('-m', '--mounts', dest='mounts', action='store', help='Amout of allowed mounts for a tape [used for replace tapes]', default=200)
    tapeParser.add_argument('-t', '--time', dest='time', action='store', help='Time in days (default=7 days)', default=7)


    statusParser = subParser.add_parser('status', help='Specific status informations');
    statusGroup = statusParser.add_mutually_exclusive_group(required=True);
    statusParser.set_defaults(func=checkStatus)
    statusGroup.add_argument('-b', '--totalBackupsSize', dest='totalBackupsSize', action='store_true', help='the size of all backups in the database [use time and kind for mor restrictions]')
    statusGroup.add_argument('-e', '--emptyBackups', dest='emptyBackups', action='store_true', help='Check if a successful backup have 0 bytes [only wise for full backups]')
    statusGroup.add_argument('-o', '--oversizedBackup', dest='oversizedBackups', action='store_true', help='Check if a backup have more than n TB')
    statusGroup.add_argument('-fb', '--failedBackups', dest='failedBackups', action='store_true', help='Check if a backup failed in the last n day')
    statusParser.add_argument('-f', '--full', dest='full', action='store_true', help='Backup kind full')
    statusParser.add_argument('-i', '--inc', dest='inc', action='store_true', help='Backup kind inc')
    statusParser.add_argument('-d', '--diff', dest='diff', action='store_true', help='Backup kind diff')
    statusParser.add_argument('-t', '--time', dest='time', action='store', help='Time in days')
    statusParser.add_argument('-w', '--warning', dest='warning', action='store', help='Warning value [default=5]', default=5)
    statusParser.add_argument('-c', '--critical', dest='critical', action='store', help='Critical value [default=10]', default=10)
    statusParser.add_argument('-s', '--size', dest='size', action='store', help='Border value for oversized backups [default=2]', default=2)
    statusParser.add_argument('-u', '--unit', dest='unit', choices=['MB', 'GB', 'TB', 'PB', 'EB'], default='TB', help='display unit [default=TB]')


    return parser

def checkConnection(cursor):
    checkResult = {}
    if cursor == None:
        checkResult["returnCode"] = 2
        checkResult["returnMessage"] = "CRITICAL - No DB connection"
        printNagiosOutput(checkResult)
        return False
    else:
        return True

def checkTape(args):
    cursor = connectDB(args.user, args.password, args.host, args.database, args.port);
    checkResult = {}
    if checkConnection(cursor):
        if args.emptyTapes:
            checkResult = checkEmptyTapes(cursor, args.warning, args.critical)
        if args.replaceTapes:
            checkResult = checkReplaceTapes(cursor, args.mounts, args.warning, args.critical)
        elif args.tapesInStorage:
            checkResult = checkTapesInStorage(cursor, args.warning, args.critical)
        elif args.expiredTapes:
            checkResult = checkExpiredTapes(cursor, args.warning, args.critical)
        elif args.willExpire:
            checkResult = checkWillExpiredTapes(cursor, args.time, args.warning, args.critical)
        printNagiosOutput(checkResult);
        cursor.close();


def checkJob(args):
    cursor = connectDB(args.user, args.password, args.host, args.database, args.port);
    checkResult = {}
    if checkConnection(cursor):
        if args.checkJob:
            kind = createBackupKindString(args.full, args.inc, args.diff)
            checkResult = checkSingleJob(cursor, args.name, args.state,kind, args.time, args.warning, args.critical)
        elif args.checkJobs:
            kind = createBackupKindString(args.full, args.inc, args.diff)
            checkResult = checkJobs(cursor, args.state, kind, args.time, args.warning, args.critical)
        elif args.runTimeJobs:
            checkResult = checkRunTimeJobs(cursor, args.name,args.state, args.time, args.warning, args.critical)
        printNagiosOutput(checkResult);
        cursor.close();


def checkStatus(args):
    cursor = connectDB(args.user, args.password, args.host, args.database, args.port);
    checkResult = {}
    if checkConnection(cursor):
        if args.emptyBackups:
            kind = createBackupKindString(args.full, args.inc, args.diff)
            checkResult = checkEmptyBackups(cursor, args.time, kind, args.warning, args.critical)
        elif args.totalBackupsSize:
            kind = createBackupKindString(args.full, args.inc, args.diff)
            checkResult = checkTotalBackupSize(cursor, args.time, kind, args.unit, args.warning, args.critical)
        elif args.oversizedBackups:
            kind = createBackupKindString(args.full, args.inc, args.diff)
            checkResult = checkOversizedBackups(cursor, args.time, args.size, kind, args.unit, args.warning, args.critical)
        elif args.failedBackups:
            kind = createBackupKindString(args.full, args.inc, args.diff)
            checkResult = checkFailedBackups(cursor, args.time, args.warning, args.critical)
        printNagiosOutput(checkResult);
        cursor.close();


if __name__ == '__main__':
    parser = argumentParser()
    args = parser.parse_args()
    args.func(args)
    # Get a cursor for the specific database connection
